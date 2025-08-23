from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import time

from core.config import settings


def main_menu_kb() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="Профиль", callback_data="profile:open")],
        [InlineKeyboardButton(text="Добавить приём", callback_data="meal:add")],
        [InlineKeyboardButton(text="Статистика", callback_data="stats:open")],
        [InlineKeyboardButton(text="Настройки", callback_data="settings:open")],
    ]
    if settings.webapp_url and str(settings.webapp_url).startswith("https://"):
        v = int(time.time())
        url = f"{settings.webapp_url}?v={v}"
        buttons.append([
            InlineKeyboardButton(text="Открыть Ultima App", web_app={"url": url})
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def webapp_cta_kb(screen: str | None = None, date_iso: str | None = None) -> InlineKeyboardMarkup | None:
    base = (settings.webapp_url or "").strip()
    # Требуем HTTPS для Telegram WebApp, иначе не возвращаем клавиатуру вовсе
    if not base or (not base.startswith("https://")):
        return None
    url = base
    params = []
    if screen:
        params.append(f"screen={screen}")
    if date_iso:
        params.append(f"date={date_iso}")
    # bust cache param to force fresh WebApp load in Telegram mobile WebView
    params.append(f"v={int(time.time())}")
    if screen == 'debug':
        params.append('debug=1')
    if params:
        sep = '&' if ('?' in url) else '?'
        url = f"{url}{sep}{'&'.join(params)}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Открыть Ultima App", web_app={"url": url})]])
    return kb

