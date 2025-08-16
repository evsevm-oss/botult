from __future__ import annotations

from pathlib import Path

from openai import OpenAI

from core.config import settings


def synthesize_speech(
    text: str,
    *,
    voice: str | None = None,
    model: str = "gpt-4o-mini-tts",
    api_key: str | None = None,
) -> bytes:
    """Return synthesized speech bytes using the most compatible API path.

    Newer OpenAI SDKs expose streaming helpers; older ones return a buffer-like
    object with ``content`` or a ``read()`` method. We avoid passing a
    non-portable ``format`` argument to keep compatibility across SDK versions.
    """
    client = OpenAI(api_key=api_key or settings.openai_api_key)

    # Try the non-streaming variant first
    try:
        result = client.audio.speech.create(
            model=model,
            voice=voice or settings.openai_tts_voice,
            input=text,
        )
        if hasattr(result, "content") and result.content is not None:
            return result.content  # type: ignore[attr-defined]
        if hasattr(result, "read"):
            return result.read()  # type: ignore[no-any-return]
    except TypeError:
        # Fall back to streaming helper when signature differs
        pass

    # Fallback: use streaming response and capture bytes
    with client.audio.speech.with_streaming_response.create(
        model=model,
        voice=voice or settings.openai_tts_voice,
        input=text,
    ) as response:
        return response.read()  # type: ignore[no-any-return]


def synthesize_to_file(
    text: str,
    target_path: str | Path,
    *,
    voice: str | None = None,
    model: str = "gpt-4o-mini-tts",
    api_key: str | None = None,
) -> Path:
    """Synthesize speech and write to ``target_path``.

    Prefer the streaming helper to avoid memory overhead and to work across SDK
    versions; gracefully fall back to a non-streaming call if needed.
    """
    client = OpenAI(api_key=api_key or settings.openai_api_key)
    path = Path(target_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with client.audio.speech.with_streaming_response.create(
            model=model,
            voice=voice or settings.openai_tts_voice,
            input=text,
        ) as response:
            response.stream_to_file(path)
            return path
    except Exception:
        # Fallback to non-streaming
        audio = synthesize_speech(
            text,
            voice=voice,
            model=model,
            api_key=api_key,
        )
        path.write_bytes(audio)
        return path


