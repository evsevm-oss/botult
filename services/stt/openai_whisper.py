from __future__ import annotations

from typing import Optional

from core.config import settings


def _get_openai_client():
    try:
        from openai import OpenAI
    except Exception as e:  # pragma: no cover
        raise RuntimeError("openai package is required for STT") from e
    return OpenAI(api_key=settings.openai_api_key)


def transcribe_audio_bytes(audio_bytes: bytes, filename: str = "audio.ogg", language: Optional[str] = "ru") -> str:
    """Transcribe audio bytes using OpenAI Whisper (or 4o-mini-transcribe if configured)."""
    client = _get_openai_client()
    # The SDK requires a file-like object
    import io

    with io.BytesIO(audio_bytes) as f:
        f.name = filename
        try:
            # Prefer whisper-1; fallback to gpt-4o-mini-transcribe for new API
            resp = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language=language or "ru",
            )
        except Exception:
            f.seek(0)
            resp = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=f,
                language=language or "ru",
            )
    text = getattr(resp, "text", None) or (resp.get("text") if isinstance(resp, dict) else None)
    return text or ""


