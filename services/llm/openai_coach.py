from __future__ import annotations

from typing import Any

from core.config import settings


PERSONA_SYSTEM_PROMPT = (
    "Ты — дружелюбный русскоязычный AI‑диетолог. Помогаешь достигать целей (снижение/набор/поддержание),"
    " учитывая профиль, цели и историю дня. Отвечай кратко и по делу, с конкретными шагами."
    " Не давай медицинских диагнозов и не замещай врача. При запросах вне твоей компетенции — вежливо откажись"
    " и предложи альтернативу."
)


def build_context_messages(context: dict[str, Any], user_text: str) -> list[dict[str, str]]:
    msgs: list[dict[str, str]] = [{"role": "system", "content": PERSONA_SYSTEM_PROMPT}]
    # Сжато предоставим контекст
    prof = context.get("profile") or {}
    goal = context.get("goal") or {}
    last_summaries = context.get("last_summaries") or []
    ctx_text = (
        f"Профиль: sex={prof.get('sex')}, height_cm={prof.get('height_cm')}, weight_kg={prof.get('weight_kg')}, "
        f"activity={prof.get('activity_level')}, goal={prof.get('goal')}.\n"
        f"Цель: {goal.get('target_type')}={goal.get('target_value')} pace={goal.get('pace')} active={goal.get('active')}.\n"
        f"Последние сводки (дата kcal БЖУ): "
        + ", ".join(
            f"{s['date']} {int(s['kcal'])}ккал Б{int(s['protein_g'])} Ж{int(s['fat_g'])} У{int(s['carb_g'])}"
            for s in last_summaries
        )
    )
    msgs.append({"role": "system", "content": ctx_text})
    msgs.append({"role": "user", "content": user_text})
    return msgs


def chat_coach(context: dict[str, Any], user_text: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    msgs = build_context_messages(context, user_text)
    resp = client.chat.completions.create(
        model=settings.openai_model_normalize or "gpt-4o-mini",
        messages=msgs,
        temperature=0.3,
    )
    return resp.choices[0].message.content or ""


