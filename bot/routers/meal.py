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
import json
import math


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
                items = _add_emojis(items)
                preview = _build_preview(items)
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Сохранить", callback_data="meal_save")],
                    [InlineKeyboardButton(text="Отменить", callback_data="meal_cancel")],
                    [InlineKeyboardButton(text="Дополнить", callback_data="meal_refine")],
                ])
                # Сохраним черновик в Redis (TTL 10 мин)
                draft = {"items": items, "text": text, "meta": {}}
                await redis_client.setex(_draft_key(message.from_user.id), 600, json.dumps(draft, ensure_ascii=False))
                await state.set_data({"items": items, "text": text})
                await state.set_state(AddMealStates.preview)
                await message.answer(f"Предварительная нормализация:\n{preview}", reply_markup=kb)
        else:
            await message.answer("Сервис нормализации временно недоступен")
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
    # Берём items из Redis‑черновика, если доступен
    data = await state.get_data()
    draft_raw = await redis_client.get(_draft_key(call.from_user.id))
    if draft_raw:
        try:
            d = json.loads(draft_raw)
            items = d.get("items", [])
            data = {**data, **d}
        except Exception:
            items = data.get("items", [])
    else:
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
            payload = r.json().get("data") or {}
            warnings = payload.get("warnings") or []
            # show day totals
            today = DT.utcnow().date().isoformat()
            s = await client.get(f"/api/daily-summary", params={"telegram_id": call.from_user.id, "date": today})
            txt = "Сохранено ✅"
            if s.status_code == 200 and s.json().get("data"):
                ds = s.json()["data"]
                txt += f"\nИтоги дня: {int(ds['kcal'])} ккал, Б:{int(ds['protein_g'])} Ж:{int(ds['fat_g'])} У:{int(ds['carb_g'])}"
            if warnings:
                txt += "\n\nПредупреждения:\n" + "\n".join([f"• {w}" for w in warnings])
            await call.message.edit_text(txt)
        else:
            await call.message.edit_text("Не удалось сохранить приём. Попробуйте позже.")
    await state.clear()
    try:
        await redis_client.delete(_draft_key(call.from_user.id))
    except Exception:
        pass


@meal_router.callback_query(F.data == "meal_cancel")
async def cb_meal_cancel(call: CallbackQuery, state: FSMContext) -> None:
    await call.message.edit_text("Отменено.")
    await state.clear()


@meal_router.callback_query(F.data == "meal_edit")
async def cb_meal_edit(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    await call.message.edit_text("Пришлите исправленный текст приема пищи одним сообщением.")
    await state.set_state(AddMealStates.waiting_text)


# -------- Черновик (draft) и быстрые уточнения --------

def _draft_key(user_id: int) -> str:
    return f"meal:draft:{user_id}"


def _build_preview(items: list[dict]) -> str:
    if not items:
        return "Пусто"
    lines: list[str] = []
    for it in items:
        name = it.get("name", "?")
        amt = int(float(it.get("amount", 0) or 0))
        unit = it.get("unit", "g")
        kcal = int(float(it.get("kcal", 0) or 0))
        p = int(float(it.get("protein_g", 0) or 0))
        f = int(float(it.get("fat_g", 0) or 0))
        c = int(float(it.get("carb_g", 0) or 0))
        lines.append(
            f"• {name} — {amt}{unit} ≈ {kcal} ккал\n"
            f"  Протеин: {p} г. | Жиры: {f} г. | Углеводы: {c} г."
        )
    return "\n".join(lines)


@meal_router.callback_query(F.data == "meal_refine")
async def cb_meal_refine(call: CallbackQuery, state: FSMContext) -> None:
    # Покажем быстрые опции уточнений
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="50 г", callback_data="meal_refine:add:50g"), InlineKeyboardButton(text="100 г", callback_data="meal_refine:add:100g"), InlineKeyboardButton(text="300 г", callback_data="meal_refine:add:300g")],
        [InlineKeyboardButton(text="500 г", callback_data="meal_refine:add:500g"), InlineKeyboardButton(text="1 кг", callback_data="meal_refine:add:1kg"), InlineKeyboardButton(text="100 ml", callback_data="meal_refine:add:100ml")],
        [InlineKeyboardButton(text="330 ml", callback_data="meal_refine:add:330ml"), InlineKeyboardButton(text="500 ml", callback_data="meal_refine:add:500ml"), InlineKeyboardButton(text="1 литр", callback_data="meal_refine:add:1l")],
        [InlineKeyboardButton(text="1 ч.л.", callback_data="meal_refine:add:1tsp"), InlineKeyboardButton(text="1 ст.л.", callback_data="meal_refine:add:1tbsp"), InlineKeyboardButton(text="1 тарелка", callback_data="meal_refine:add:1plate")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="meal_refine:back")],
    ])
    await call.message.edit_reply_markup(reply_markup=kb)


@meal_router.callback_query(F.data.startswith("meal_refine:"))
async def cb_meal_refine_select(call: CallbackQuery, state: FSMContext) -> None:
    parts = (call.data or "").split(":")
    if len(parts) < 3:
        return
    action = parts[1]
    if action == "back":
        # восстановим прежнюю клавиатуру предпросмотра
        draft_raw = await redis_client.get(_draft_key(call.from_user.id))
        items = []
        if draft_raw:
            try:
                items = (json.loads(draft_raw) or {}).get("items", [])
            except Exception:
                items = []
        preview = _build_preview(items)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Сохранить", callback_data="meal_save")],
            [InlineKeyboardButton(text="Отменить", callback_data="meal_cancel")],
            [InlineKeyboardButton(text="Дополнить", callback_data="meal_refine")],
        ])
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Сохранить", callback_data="meal_save")],
            [InlineKeyboardButton(text="Отменить", callback_data="meal_cancel")],
            [InlineKeyboardButton(text="Дополнить", callback_data="meal_refine")],
        ])
        await call.message.edit_text(f"Предварительная нормализация:\n{preview}", reply_markup=kb)
        return

    if action == "add" and len(parts) >= 3:
        option = parts[2]
        # восстановим предыдущий текст запроса
        draft_raw = await redis_client.get(_draft_key(call.from_user.id))
        base_text = (await state.get_data()).get("text") or ""
        if draft_raw and not base_text:
            try:
                base_text = (json.loads(draft_raw) or {}).get("text") or base_text
            except Exception:
                pass
        mapping = {
            "50g": "50 г", "100g": "100 г", "300g": "300 г", "500g": "500 г", "1kg": "1 кг",
            "100ml": "100 мл", "330ml": "330 мл", "500ml": "500 мл", "1l": "1 литр",
            "1tsp": "1 ч.л.", "1tbsp": "1 ст.л.", "1plate": "1 тарелка",
        }
        add_text = mapping.get(option, option)
        new_text = (base_text + (" " if base_text and not base_text.endswith(" ") else "") + add_text).strip()
        # вызовим /api/normalize заново и обновим предпросмотр/черновик
        async with httpx.AsyncClient(base_url=settings.api_base_url, timeout=10.0) as client:
            r = await client.post("/api/normalize", json={"text": new_text, "locale": "ru", "telegram_id": call.from_user.id})
        if r.status_code == 200:
            data = r.json()
            items = data.get("items", [])
            items = _add_emojis(items)
            draft = {"items": items, "text": new_text, "meta": {}}
            await state.set_data({"items": items, "text": new_text})
            await redis_client.setex(_draft_key(call.from_user.id), 600, json.dumps(draft, ensure_ascii=False))
            preview = _build_preview(items)
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Сохранить", callback_data="meal_save"), InlineKeyboardButton(text="Отменить", callback_data="meal_cancel")],
                [InlineKeyboardButton(text="Добавить", callback_data="meal_refine"), InlineKeyboardButton(text="Править", callback_data="meal_edit")],
            ])
            await call.message.edit_text(f"Предварительная нормализация:\n{preview}", reply_markup=kb)
        else:
            await call.answer("Сервис недоступен, попробуйте позже", show_alert=True)
        return

        def find_item_by_keywords(keys: list[str]) -> int:
            for idx, it in enumerate(items):
                name = (it.get("name") or "").lower()
                if any(k in name for k in keys):
                    return idx
            return -1

        changed = False
        if kind == "diameter":
            try:
                meta["pizza_diameter_cm"] = int(value)
                changed = True
            except Exception:
                pass
        elif kind == "slices":
            try:
                n = int(value)
                idx = find_item_by_keywords(["пицц", "pizza"])
                if idx >= 0 and n > 0:
                    d = int(meta.get("pizza_diameter_cm") or 30)
                    area_cm2 = math.pi * (d / 2.0) ** 2
                    density = 0.95
                    whole_g = area_cm2 * density
                    grams = whole_g * (n / 8.0)
                    before = float(items[idx].get("amount", 0.0) or 0.0)
                    unit_before = (items[idx].get("unit") or "").lower()
                    kcal_before = float(items[idx].get("kcal", 0.0) or 0.0)
                    items[idx]["unit"] = "g"
                    items[idx]["amount"] = round(grams, 1)
                    # масштабируем ккал при наличии исходных грамм
                    if unit_before == "g" and before > 0:
                        scale = grams / before
                        items[idx]["kcal"] = round(kcal_before * scale, 1)
                    changed = True
            except Exception:
                pass
        elif kind == "volume":
            try:
                vol = int(value)
                idx = find_item_by_keywords(["суп", "soup", "напит", "juice", "смузи", "чай", "кофе"]) or 0
                if idx >= 0:
                    items[idx]["unit"] = "ml"
                    items[idx]["amount"] = vol
                    changed = True
            except Exception:
                pass
        elif kind == "fried":
            # Добавим/удалим масло для жарки как отдельную позицию
            oil_idx = find_item_by_keywords(["масло", "oil"])
            if value == "none":
                if oil_idx >= 0:
                    items.pop(oil_idx)
                    changed = True
            else:
                grams = 5.0 if value == "1tsp" else 15.0
                oil_item = {
                    "name": "растительное масло (жарка)",
                    "unit": "g",
                    "amount": grams,
                    "kcal": round(9.0 * grams, 1),
                    "protein_g": 0.0,
                    "fat_g": round(grams, 1),
                    "carb_g": 0.0,
                }
                if oil_idx >= 0:
                    items[oil_idx] = oil_item
                else:
                    items.append(oil_item)
                changed = True

        if changed:
            draft["items"] = items
            draft["meta"] = meta
            await redis_client.setex(_draft_key(call.from_user.id), 600, json.dumps(draft, ensure_ascii=False))

        # Вернёмся к предпросмотру
        preview = _build_preview(items)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Сохранить", callback_data="meal_save"), InlineKeyboardButton(text="Отменить", callback_data="meal_cancel")],
            [InlineKeyboardButton(text="Добавить", callback_data="meal_refine"), InlineKeyboardButton(text="Править", callback_data="meal_edit")],
        ])
        await call.message.edit_text(f"Предварительная нормализация:\n{preview}", reply_markup=kb)


# Авто‑вопрос при конфликте масс (draft)
def _detect_mass_conflict(items: list[dict]) -> tuple[bool, str | None, float | None, float | None]:
    # простая эвристика: если есть два варианта amount для одной позиции в meta (не реализовано в схеме items), пропускаем
    return False, None, None, None


# ---------- Эмодзи для блюд ----------

def _emoji_for_item(name: str, category: str | None) -> str:
    n = (name or "").lower()
    # По ключевым словам
    kw = {
        "пицц": "🍕",
        "бургер": "🍔",
        "биф" : "🥩",
        "стейк": "🥩",
        "котлет": "🥩",
        "куриц": "🍗",
        "индейк": "🍗",
        "рыб": "🐟",
        "суши": "🍣",
        "ролл": "🍣",
        "суп": "🍲",
        "салат": "🥗",
        "каша": "🥣",
        "хлеб": "🍞",
        "йогурт": "🥛",
        "молок": "🥛",
        "кофе": "☕️",
        "чай": "🍵",
        "яблок": "🍎",
        "банан": "🍌",
        "арбуз": "🍉",
        "апельс": "🍊",
        "виноград": "🍇",
        "картоф": "🥔",
    }
    for k, e in kw.items():
        if k in n:
            return e
    # По категории
    catmap = {
        "protein": "🥩",
        "carbohydrate": "🍚",
        "fat": "🧈",
        "vegetable": "🥦",
        "fruit": "🍎",
        "dairy": "🥛",
        "beverage": "🥤",
        "dessert": "🍰",
        "other": "🍽️",
    }
    return catmap.get((category or "").lower(), "🍽️")


def _add_emojis(items: list[dict]) -> list[dict]:
    out: list[dict] = []
    for it in items:
        name = str(it.get("name") or "?")
        # если уже начинается с эмодзи — не дублируем
        if name and name[0] in "🍕🍔🥩🍗🐟🍣🍲🥗🥣🍞🥛☕️🍵🍎🍌🍉🍊🍇🥔🍚🧈🥦🥤🍰🍽️":
            out.append(it)
            continue
        emoji = _emoji_for_item(name, it.get("category"))
        it2 = {**it, "name": f"{emoji} {name}"}
        out.append(it2)
    return out

