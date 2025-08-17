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


