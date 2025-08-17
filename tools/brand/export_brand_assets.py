from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from PIL import Image


SIZES = (640, 512, 200)


def export_pngs(src_svg: Path, out_dir: Path, prefix: str) -> None:
    # Простая конвертация: SVG → PNG через Pillow не поддерживается напрямую.
    # В минимальном варианте рендерим фон и букву сами (логотип примитивный).
    # Для реального SVG‑рендера подключите cairosvg (добавьте зависимость при необходимости).
    import re

    svg = src_svg.read_text(encoding="utf-8")
    bg = re.search(r"fill: (#[0-9A-Fa-f]{6})", svg).group(1)  # первый fill в стилях — фон
    # fg сейчас не используем, букву рисуем как часть простого рендера

    for size in SIZES:
        img = Image.new("RGB", (size, size), color=bg)
        # Букву не рисуем, чтобы не тянуть зависимость на векторный рендер в этапе 0.
        # В ассетах фокус на цвете/фоне и краевом округлении в Telegram.
        out_dir.mkdir(parents=True, exist_ok=True)
        img.save(out_dir / f"{prefix}-{size}.png", format="PNG")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export brand assets (PNG) from SVG sources")
    parser.add_argument("--src-dir", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    light_svg = args.src_dir / "logo-light.svg"
    dark_svg = args.src_dir / "logo-dark.svg"

    export_pngs(light_svg, args.out_dir / "light", "logo")
    export_pngs(dark_svg, args.out_dir / "dark", "logo")


if __name__ == "__main__":
    main()


