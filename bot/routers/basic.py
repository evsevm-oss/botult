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
import asyncio


basic_router = Router()


@basic_router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    from bot.keyboards import webapp_cta_kb
    kb = webapp_cta_kb(screen="dashboard")
    await message.answer(
        "Привет! Я бот‑коуч по питанию (MVP). Доступно: /help, /budget.",
        reply_markup=kb if kb is not None else None
    )


@basic_router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    from bot.keyboards import webapp_cta_kb
    kb = webapp_cta_kb()
    await message.answer("Доступно: /start, /help, /budget — пример расчёта бюджета.", reply_markup=kb if kb is not None else None)


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
        last_image_id: int | None = None
        for p in photos:
            file = await bot.get_file(p.file_id)
            url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url)
                data = resp.content
                r = await client.post(
                    "/api/photos",
                    params={"telegram_id": message.from_user.id, "content_type": "image/jpeg"},
                    content=data,
                )
                if r.status_code == 200:
                    last_image_id = (r.json().get("data") or {}).get("image_id")
    except Exception:
        pass
    if message.media_group_id:
        # агрегируем группу, попробуем автоматически закоммитить через 2 сек
        gid = message.media_group_id
        uid = message.from_user.id
        if last_image_id:
            await redis_client.rpush(f"mediagroup:{uid}:{gid}", last_image_id)
            await redis_client.expire(f"mediagroup:{uid}:{gid}", 120)
        # один шедулер на группу
        if await redis_client.set(f"mediagroup:{uid}:{gid}:lock", "1", ex=5, nx=True):
            async def _finalize():
                await asyncio.sleep(2.0)
                async with httpx.AsyncClient(base_url=settings.api_base_url, timeout=20.0) as client:
                    cr = await client.post("/api/photo-groups/commit", params={"telegram_id": uid, "group_id": gid})
                    data = cr.json().get("data") if cr.status_code == 200 else None
                    if not data:
                        await message.answer("Не удалось собрать альбом. Попробуйте ещё раз.")
                        return
                    items = data.get("items", [])
                    img_id = data.get("handle_image_id")
                    preview = "\n".join(
                        f"• {i['name']} — {int(i.get('amount',0))}{i.get('unit','g')} ≈ {int(i.get('kcal',0))} ккал" for i in items
                    )
                    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Сохранить", callback_data=f"photo_save:{img_id}"), InlineKeyboardButton(text="Отменить", callback_data=f"photo_cancel:{img_id}")]])
                    await message.answer(f"Распознано по альбому:\n{preview}", reply_markup=kb)
            asyncio.create_task(_finalize())
        else:
            # просто уведомим о получении
            await message.answer("Фото получены. Объединяю изображения…")
    else:
        await message.answer("Фото получено. Поставлено в очередь на распознавание. Сообщу, когда будет готово.")


@basic_router.callback_query(F.data.startswith("photo_save:"))
async def cb_photo_save(call, state):
    image_id = int(call.data.split(":",1)[1])
    async with httpx.AsyncClient(base_url=settings.api_base_url, timeout=20.0) as client:
        r = await client.post(f"/api/photos/{image_id}/save", params={"telegram_id": call.from_user.id})
        if r.status_code == 200:
            await call.message.edit_text("Сохранено ✅")
        else:
            await call.message.edit_text("Не удалось сохранить")

@basic_router.callback_query(F.data.startswith("photo_cancel:"))
async def cb_photo_cancel(call, state):
    await call.message.edit_text("Отменено.")


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


