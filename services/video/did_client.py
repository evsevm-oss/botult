from __future__ import annotations

from pathlib import Path
from typing import Optional

import httpx

from core.config import settings


BASE_URL = "https://api.d-id.com"  # v1, v2 endpoints vary by account; adjust if needed


class DIDClient:
    def __init__(self, api_key: Optional[str] = None, *, base_url: str = BASE_URL) -> None:
        self.api_key = api_key or settings.did_api_key
        self.base_url = base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise ValueError("D-ID API key is not configured")
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def create_talk(
        self,
        *,
        image_url: str,
        audio_url: str | None = None,
        text: str | None = None,
        driver_url: str | None = None,
        webhook_url: str | None = None,
    ) -> dict:
        if not (audio_url or text):
            raise ValueError("Either audio_url or text must be provided")

        payload: dict = {
            "source_url": image_url,
        }
        if audio_url:
            payload["audio_url"] = audio_url
        if text:
            payload["script"] = {"type": "text", "input": text}
        if driver_url:
            payload["driver_url"] = driver_url
        if webhook_url:
            payload["webhook"] = {"url": webhook_url}

        with httpx.Client(base_url=self.base_url, headers=self._headers(), timeout=60) as client:
            resp = client.post("/talks", json=payload)
            resp.raise_for_status()
            return resp.json()

    def get_talk(self, talk_id: str) -> dict:
        with httpx.Client(base_url=self.base_url, headers=self._headers(), timeout=60) as client:
            resp = client.get(f"/talks/{talk_id}")
            resp.raise_for_status()
            return resp.json()

    def download_result(self, result_url: str, target_path: str | Path) -> Path:
        path = Path(target_path)
        with httpx.Client(timeout=None) as client:
            with client.stream("GET", result_url) as resp:
                resp.raise_for_status()
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("wb") as f:
                    for chunk in resp.iter_bytes():
                        f.write(chunk)
        return path


