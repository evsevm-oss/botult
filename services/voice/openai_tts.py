from __future__ import annotations

from pathlib import Path
from typing import Literal

from openai import OpenAI

from core.config import settings


TTSFormat = Literal["mp3", "wav", "ogg"]


def synthesize_speech(
    text: str,
    *,
    voice: str | None = None,
    format: TTSFormat = "mp3",
    model: str = "gpt-4o-mini-tts",
    api_key: str | None = None,
) -> bytes:
    client = OpenAI(api_key=api_key or settings.openai_api_key)
    result = client.audio.speech.create(
        model=model,
        voice=voice or settings.openai_tts_voice,
        input=text,
        format=format,
    )
    return result.read()


def synthesize_to_file(
    text: str,
    target_path: str | Path,
    *,
    voice: str | None = None,
    format: TTSFormat = "mp3",
    model: str = "gpt-4o-mini-tts",
    api_key: str | None = None,
) -> Path:
    audio = synthesize_speech(
        text,
        voice=voice,
        format=format,
        model=model,
        api_key=api_key,
    )
    path = Path(target_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(audio)
    return path


