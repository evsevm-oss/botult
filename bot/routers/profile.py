from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from datetime import date

from infra.db.session import get_session
from infra.db.repositories.user_repo import UserRepo
from infra.db.repositories.profile_repo import ProfileRepo
from infra.api.schemas import ProfileDTO
from domain.use_cases import CalculateBudgetsInput, calculate_budgets
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards import main_menu_kb


profile_router = Router()


class OnboardStates(StatesGroup):
    sex = State()
    age = State()
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
    await state.set_state(OnboardStates.age)
    await message.answer("Возраст (лет):")


@profile_router.message(OnboardStates.age, F.text.regexp(r"^\d{1,3}$"))
async def st_age(message: Message, state: FSMContext) -> None:
    age = int(message.text)
    if age < 10 or age > 100:
        await message.answer("Введите возраст от 10 до 100")
        return
    await state.update_data(age=age)
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
async def st_goal(message: Message, state: FSMContext, session: AsyncSession = get_session.__wrapped__()):
    # Сбор данных
    await state.update_data(goal=message.text.lower())
    data = await state.get_data()

    # Создание/получение пользователя и сохранение профиля
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
    budgets = calculate_budgets(
        CalculateBudgetsInput(
            sex=dto.sex,
            age=data["age"],
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


