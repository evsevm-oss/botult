from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message


coach_router = Router()


@coach_router.message(Command("coach"))
async def cmd_coach(message: Message) -> None:
    await message.answer("AI‑коуч активен. Спросите меня о рационе, замене блюд, как уложиться в бюджет и т.п.")


from infra.db.session import get_session
from infra.db.repositories.profile_repo import ProfileRepo
from infra.db.repositories.goal_repo import GoalRepo
from infra.db.repositories.daily_summary_repo import DailySummaryRepo
from services.llm.openai_coach import chat_coach


@coach_router.message(F.text & ~F.text.startswith("/"))
async def on_coach_text(message: Message) -> None:
    async with get_session() as session:  # type: ignore
        prof = await ProfileRepo(session).get_by_user_id(message.from_user.id)
        from datetime import date, timedelta
        today = date.today()
        days = [today - timedelta(days=i) for i in range(3)]
        ds_repo = DailySummaryRepo(session)
        last = []
        for d in days:
            v = await ds_repo.get_by_user_date(user_id=message.from_user.id, on_date=d)
            if v:
                last.append({"date": d.isoformat(), **v})
        goal = None
        goals = await GoalRepo(session).list_by_user(message.from_user.id)
        if goals:
            for g in goals:
                if g.get("active"):
                    goal = g
                    break
            goal = goal or goals[0]
    context = {"profile": prof or {}, "goal": goal or {}, "last_summaries": last}
    reply = chat_coach(context, message.text or "")
    await message.answer(reply or "Готов помочь. Сформулируйте вопрос подробнее.")


