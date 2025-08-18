from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import httpx
from core.config import settings
from infra.cache.redis import redis_client
from services.stt.openai_whisper import transcribe_audio_bytes


meal_router = Router()


class AddMealStates(StatesGroup):
    waiting_text = State()
    preview = State()
    waiting_voice = State()


@meal_router.message(Command("addmeal"))
async def cmd_addmeal(message: Message, state: FSMContext) -> None:
    await state.set_state(AddMealStates.waiting_text)
    await message.answer("Введите прием пищи в формате: 'куриная грудка 150 г, рис 120 г, масло 5 г'")


@meal_router.message(AddMealStates.waiting_text, F.text)
async def on_meal_text(message: Message, state: FSMContext) -> None:
    text = message.text or ""
    headers = {}
    if (trace_id := (await state.get_data()).get("trace_id")):
        headers["X-Trace-Id"] = str(trace_id)
    async with httpx.AsyncClient(base_url=settings.api_base_url, timeout=10.0, headers=headers) as client:
        r = await client.post("/api/normalize", json={"text": text, "locale": "ru", "telegram_id": message.from_user.id})
        if r.status_code == 200:
            data = r.json()
            items = data.get("items", [])
            if not items:
                await message.answer("Не удалось распознать позиции. Попробуйте уточнить формулировки.")
            else:
                preview = "\n".join(
                    f"• {i['name']} — {int(i['amount'])}{i['unit']} ≈ {int(i['kcal'])} ккал"
                    for i in items
                )
                kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Сохранить", callback_data="meal_save"), InlineKeyboardButton(text="Отменить", callback_data="meal_cancel")], [InlineKeyboardButton(text="Править", callback_data="meal_edit")]])
                # идемпотентность: запомним update_id входящего текста
                if message.update_id:
                    await redis_client.setex(f"seen:update:{message.from_user.id}:{message.update_id}", 86400, "1")
                await state.set_data({"items": items, "text": text, "source_update_id": message.update_id})
                await state.set_state(AddMealStates.preview)
                await message.answer(f"Предварительная нормализация:\n{preview}", reply_markup=kb)
        else:
            await message.answer("Сервис нормализации временно недоступен")
    await state.clear()
@meal_router.message(F.text)
async def on_free_text(message: Message, state: FSMContext) -> None:
    # Игнорируем команды
    if (message.text or "").startswith("/"):
        return
    # Запуск потока нормализации без команды
    await state.set_state(AddMealStates.waiting_text)
    await on_meal_text(message, state)

@meal_router.message(F.voice)
async def on_voice(message: Message, state: FSMContext) -> None:
    # Download voice file
    try:
        file_id = message.voice.file_id
        from aiogram import Bot
        bot = message.bot if hasattr(message, 'bot') else None
        if bot is None:
            await message.answer("Не удалось получить файл.")
            return
        file = await bot.get_file(file_id)
        url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url)
            audio_bytes = resp.content
        text = transcribe_audio_bytes(audio_bytes, filename="voice.ogg", language="ru")
        if not text:
            await message.answer("Не удалось распознать речь. Попробуйте ещё раз.")
            return
        # Reuse text flow
        await state.set_state(AddMealStates.waiting_text)
        fake_message = message
        fake_message.text = text
        await on_meal_text(fake_message, state)
    except Exception:
        await message.answer("Ошибка распознавания. Попробуйте позже.")


@meal_router.callback_query(F.data == "meal_save")
async def cb_meal_save(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    items = data.get("items", [])
    if not items:
        await call.message.edit_text("Нечего сохранять.")
        return
    from datetime import datetime as DT
    async with httpx.AsyncClient(base_url=settings.api_base_url, timeout=10.0, headers={"X-Trace-Id": (await state.get_data()).get("trace_id", "")}) as client:
        r = await client.post(
            "/api/meals",
            params={"telegram_id": call.from_user.id},
            json={
                "at": DT.utcnow().isoformat(),
                "type": None,
                "status": "confirmed",
                "items": items,
                "notes": data.get("text"),
                "source_chat_id": call.message.chat.id,
                "source_message_id": call.message.message_id,
                "source_update_id": data.get("source_update_id"),
            },
        )
        if r.status_code == 200:
            # show day totals
            today = DT.utcnow().date().isoformat()
            s = await client.get(f"/api/daily-summary", params={"telegram_id": call.from_user.id, "date": today})
            txt = "Сохранено ✅"
            if s.status_code == 200 and s.json().get("data"):
                ds = s.json()["data"]
                txt += f"\nИтоги дня: {int(ds['kcal'])} ккал, Б:{int(ds['protein_g'])} Ж:{int(ds['fat_g'])} У:{int(ds['carb_g'])}"
            await call.message.edit_text(txt)
        else:
            await call.message.edit_text("Не удалось сохранить приём. Попробуйте позже.")
    await state.clear()


@meal_router.callback_query(F.data == "meal_cancel")
async def cb_meal_cancel(call: CallbackQuery, state: FSMContext) -> None:
    await call.message.edit_text("Отменено.")
    await state.clear()


@meal_router.callback_query(F.data == "meal_edit")
async def cb_meal_edit(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await call.message.edit_text("Пришлите исправленный текст приема пищи одним сообщением.")
    await state.set_state(AddMealStates.waiting_text)


