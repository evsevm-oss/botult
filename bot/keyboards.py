from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from core.config import settings


def main_menu_kb() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="Профиль", callback_data="profile:open")],
        [InlineKeyboardButton(text="Добавить приём", callback_data="meal:add")],
        [InlineKeyboardButton(text="Статистика", callback_data="stats:open")],
        [InlineKeyboardButton(text="Настройки", callback_data="settings:open")],
    ]
    if settings.webapp_url:
        buttons.append([
            InlineKeyboardButton(text="Открыть WebApp", web_app={"url": settings.webapp_url})
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def webapp_cta_kb(screen: str | None = None, date_iso: str | None = None) -> InlineKeyboardMarkup:
    base = (settings.webapp_url or "").strip()
    # Если URL пустой/некорректный — вернуть пустую клавиатуру, чтобы не падать на стороне Telegram
    if not base or ("://" not in base):
        return InlineKeyboardMarkup(inline_keyboard=[])
    url = base
    params = []
    if screen:
        params.append(f"screen={screen}")
    if date_iso:
        params.append(f"date={date_iso}")
    if params:
        sep = '&' if ('?' in url) else '?'
        url = f"{url}{sep}{'&'.join(params)}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Открыть WebApp", web_app={"url": url})]])
    return kb

