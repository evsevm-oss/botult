from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from datetime import date, datetime

from infra.db.session import SessionLocal
from infra.db.repositories.user_repo import UserRepo
from infra.db.repositories.profile_repo import ProfileRepo
from infra.api.schemas import ProfileDTO
from domain.use_cases import CalculateBudgetsInput, calculate_budgets
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import main_menu_kb


profile_router = Router()


class OnboardStates(StatesGroup):
    sex = State()
    birth = State()
    height = State()
    weight = State()
    activity = State()
    goal = State()


@profile_router.message(Command("profile"))
async def cmd_profile(message: Message, state: FSMContext) -> None:
    await state.set_state(OnboardStates.sex)
    await message.answer("Давайте заполним профиль. Укажите пол (male/female):", reply_markup=main_menu_kb())


@profile_router.message(OnboardStates.sex, F.text.lower().in_({"male", "female"}))
async def st_sex(message: Message, state: FSMContext) -> None:
    await state.update_data(sex=message.text.lower())
    await state.set_state(OnboardStates.birth)
    await message.answer("Дата рождения (в формате YYYY-MM-DD или DD.MM.YYYY):")


@profile_router.message(OnboardStates.birth)
async def st_birth(message: Message, state: FSMContext) -> None:
    txt = (message.text or "").strip()
    birth: date | None = None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            birth = datetime.strptime(txt, fmt).date()
            break
        except ValueError:
            continue
    if birth is None:
        await message.answer("Не получилось распознать дату. Введите в формате YYYY-MM-DD или DD.MM.YYYY")
        return
    today = date.today()
    if birth > today or (today.year - birth.year) < 10 or (today.year - birth.year) > 100:
        await message.answer("Пожалуйста, введите реальную дату рождения (возраст 10–100 лет)")
        return
    await state.update_data(birth_date=birth.isoformat())
    await state.set_state(OnboardStates.height)
    await message.answer("Рост (в сантиметрах):")


@profile_router.message(OnboardStates.height, F.text.regexp(r"^\d{2,3}(\.\d+)?$"))
async def st_height(message: Message, state: FSMContext) -> None:
    await state.update_data(height_cm=float(message.text))
    await state.set_state(OnboardStates.weight)
    await message.answer("Вес (в килограммах):")


@profile_router.message(OnboardStates.weight, F.text.regexp(r"^\d{2,3}(\.\d+)?$"))
async def st_weight(message: Message, state: FSMContext) -> None:
    await state.update_data(weight_kg=float(message.text))
    await state.set_state(OnboardStates.activity)
    await message.answer("Уровень активности (low/medium/high):")


@profile_router.message(OnboardStates.activity, F.text.lower().in_({"low", "medium", "high"}))
async def st_activity(message: Message, state: FSMContext) -> None:
    await state.update_data(activity_level=message.text.lower())
    await state.set_state(OnboardStates.goal)
    await message.answer("Цель (lose/maintain/gain):")


@profile_router.message(OnboardStates.goal, F.text.lower().in_({"lose", "maintain", "gain"}))
async def st_goal(message: Message, state: FSMContext):
    # Сбор данных
    await state.update_data(goal=message.text.lower())
    data = await state.get_data()

    # Создание/получение пользователя и сохранение профиля
    async with SessionLocal() as session:
        users = UserRepo(session)
        profiles = ProfileRepo(session)
        user_id = await users.get_or_create_by_telegram_id(message.from_user.id)
        dto = ProfileDTO(
            sex=data["sex"],
            birth_date=None,
            height_cm=data["height_cm"],
            weight_kg=data["weight_kg"],
            activity_level=data["activity_level"],
            goal=data["goal"],
        )
        await profiles.upsert_profile(
            user_id=user_id,
            sex=dto.sex,
            birth_date=dto.birth_date,
            height_cm=dto.height_cm,
            weight_kg=dto.weight_kg,
            activity_level=dto.activity_level,
            goal=dto.goal,
        )

    # Расчет бюджетов
    # Возраст считаем из даты рождения на текущую дату
    def _age_from_birth(b: str) -> int:
        d = datetime.strptime(b, "%Y-%m-%d").date()
        today = date.today()
        years = today.year - d.year - ((today.month, today.day) < (d.month, d.day))
        return max(0, years)

    age_years = _age_from_birth(data["birth_date"]) if data.get("birth_date") else 30
    budgets = calculate_budgets(
        CalculateBudgetsInput(
            sex=dto.sex,
            age=age_years,
            height_cm=dto.height_cm,
            weight_kg=dto.weight_kg,
            activity_level=dto.activity_level,
            goal=dto.goal,
        )
    )

    await message.answer(
        f"Профиль сохранен. Ваши дневные бюджеты:\n"
        f"Калории: {int(budgets.kcal)} ккал\n"
        f"Белки: {int(budgets.protein_g)} г\n"
        f"Жиры: {int(budgets.fat_g)} г\n"
        f"Углеводы: {int(budgets.carb_g)} г"
    )
    await state.clear()


