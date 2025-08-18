from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
import httpx
from core.config import settings

from domain.use_cases import CalculateBudgetsInput, calculate_budgets
from infra.cache.redis import redis_client
from infra.db.session import get_session
from infra.db.repositories.image_repo import ImageRepo
from infra.db.repositories.vision_inference_repo import VisionInferenceRepo
from infra.db.repositories.meal_repo import MealRepo


basic_router = Router()


@basic_router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Привет! Я бот‑коуч по питанию (MVP). Доступно: /help, /budget."
    )


@basic_router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer("Доступно: /start, /help, /budget — пример расчёта бюджета.")


@basic_router.message(Command("budget"))
async def cmd_budget(message: Message) -> None:
    # Заглушка профиля — позже возьмём из БД/профиля пользователя
    inp = CalculateBudgetsInput(
        sex="male",
        age=30,
        height_cm=180,
        weight_kg=80,
        activity_level="medium",
        goal="maintain",
    )
    out = calculate_budgets(inp)
    await message.answer(
        f"Дневной бюджет (пример):\n"
        f"Калории: {int(out.kcal)} ккал\n"
        f"Б: {int(out.protein_g)} г, Ж: {int(out.fat_g)} г, У: {int(out.carb_g)} г"
    )


@basic_router.message(F.photo | F.media_group_id)
async def on_photo(message: Message) -> None:
    # Принимаем одиночное фото или медиагруппу; на старте сохраняем файл(ы) и ставим в очередь
    try:
        from aiogram import Bot
        bot = message.bot
        photos = []
        if message.photo:
            photos = [message.photo[-1]]  # best quality
        # Для медиагруппы aiogram вызывает обработчик для каждого элемента — складываем по одному
        for p in photos:
            file = await bot.get_file(p.file_id)
            url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url)
                data = resp.content
                await client.post(
                    "/api/photos",
                    params={"telegram_id": message.from_user.id, "content_type": "image/jpeg"},
                    content=data,
                )
    except Exception:
        pass
    await message.answer("Фото получено. Поставлено в очередь на распознавание. Сообщу, когда будет готово.")


@basic_router.message(F.text.startswith("/checkphoto"))
async def cmd_check_photo(message: Message) -> None:
    # Утилита: проверяет последние распознавания и предлагает подтвердить
    args = (message.text or "").split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("Использование: /checkphoto <image_id>")
        return
    image_id = int(args[1])
    async with get_session() as session:  # type: ignore
        vrepo = VisionInferenceRepo(session)
        inf = await vrepo.get_latest_by_image(image_id=image_id)
        if not inf:
            await message.answer("Результат распознавания пока не готов")
            return
        resp = inf["response"]
        items = resp.get("items", [])
        if not items:
            await message.answer("Не удалось распознать блюда. Введите вручную /addmeal")
            return
        preview = "\n".join(
            f"• {i['name']} — {int(i.get('amount',0))}{i.get('unit','g')} ≈ {int(i.get('kcal',0))} ккал" for i in items
        )
        await message.answer(f"Распознано:\n{preview}\nПодтвердить сохранение? Отправьте /savephoto {image_id}")


@basic_router.message(F.text.startswith("/savephoto"))
async def cmd_save_photo(message: Message) -> None:
    args = (message.text or "").split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("Использование: /savephoto <image_id>")
        return
    image_id = int(args[1])
    from datetime import datetime as DT
    async with get_session() as session:  # type: ignore
        vrepo = VisionInferenceRepo(session)
        mrepo = MealRepo(session)
        inf = await vrepo.get_latest_by_image(image_id=image_id)
        if not inf:
            await message.answer("Результат распознавания не найден")
            return
        resp = inf["response"]
        items = resp.get("items", [])
        meal_id = await mrepo.create_meal(
            user_id=message.from_user.id,
            at=DT.utcnow(),
            meal_type=MealRepo.suggest_meal_type(DT.utcnow()),
            items=items,
            notes=f"photo:{image_id}",
            status="confirmed",
            autocommit=True,
        )
        await message.answer(f"Сохранено как приём {meal_id} ✅")


@basic_router.message(Command("photo"))
async def cmd_photo(message: Message) -> None:
    await message.answer("Пришлите фото блюда одним сообщением — я подтвержу получение и позже распознаю.")


# аудио/голос обрабатывается в meal_router с FSM


