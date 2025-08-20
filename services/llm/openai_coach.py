from __future__ import annotations

from typing import Any
import json
from pathlib import Path

from core.config import settings
from infra.cache.redis import redis_client


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
    out = resp.choices[0].message.content or ""
    # crude token accounting if available
    try:
        usage = getattr(resp, "usage", None)
        if usage:
            in_t = getattr(usage, "prompt_tokens", 0) or 0
            out_t = getattr(usage, "completion_tokens", 0) or 0
            cost = (in_t / 1000.0) * settings.openai_cost_input_per_1k + (out_t / 1000.0) * settings.openai_cost_output_per_1k
            # per-user daily cost
            # context may hold user_id
            uid = context.get("user_id")
            if uid:
                from datetime import date as D
                key = f"cost:coach:{uid}:{D.today().isoformat()}"
                awaitable = redis_client.incrbyfloat(key, float(cost))  # type: ignore
                try:
                    # for sync func, fire and forget; most redis clients return awaitable when async
                    pass
                except Exception:
                    pass
    except Exception:
        pass
    return out


def _load_dietology_snippets(max_chars: int = 1800) -> str:
    try:
        p = Path("docs/dietology-recommendations.mdc")
        if p.exists():
            txt = p.read_text(encoding="utf-8")
            return txt[:max_chars]
    except Exception:
        pass
    return ""


def chat_coach_structured(context: dict[str, Any], user_text: str) -> dict[str, Any]:
    """Return { message: str, actions: [{type, payload}...] }"""
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    diet = _load_dietology_snippets()
    tools_spec = (
        "Верни JSON с полями: message (string), actions (array). Каждое действие имеет type из"
        " [propose_meal_plan, suggest_swaps, evaluate_meal, shopping_list] и payload (object)."
        " propose_meal_plan.payload = { date: 'YYYY-MM-DD', meals: [{at: iso, type: breakfast|lunch|dinner|snack, items:[{name, amount, unit, kcal, protein_g, fat_g, carb_g}]}] }"
        " suggest_swaps.payload = { items:[{from, to, rationale}] }"
        " evaluate_meal.payload = { score: 0..100, notes: string }"
        " shopping_list.payload = { items:[{name, qty, unit}] }"
        " Строго валидный JSON."
    )
    msgs = build_context_messages(context, user_text)
    if diet:
        msgs.insert(1, {"role": "system", "content": f"Краткие выдержки из методологии:\n{diet}"})
    msgs.insert(1, {"role": "system", "content": tools_spec})
    resp = client.chat.completions.create(
        model=settings.openai_model_normalize or "gpt-4o-mini",
        messages=msgs,
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    txt = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(txt)
    except Exception:
        data = {"message": txt, "actions": []}
    if "message" not in data:
        data["message"] = ""
    if "actions" not in data or not isinstance(data["actions"], list):
        data["actions"] = []
    return data


