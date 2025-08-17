from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont
import re


SIZES = (640, 512, 200)


def _extract_colors_from_svg(svg_path: Path) -> tuple[str, str]:
    svg = svg_path.read_text(encoding="utf-8")
    # Expect styles like: .bg { fill: #RRGGBB; } .fg { fill: #RRGGBB; }
    bg_match = re.search(r"\.bg\s*\{\s*fill:\s*(#[0-9A-Fa-f]{6})", svg)
    fg_match = re.search(r"\.fg\s*\{\s*fill:\s*(#[0-9A-Fa-f]{6})", svg)
    bg = bg_match.group(1) if bg_match else "#2E7D32"
    fg = fg_match.group(1) if fg_match else "#FFFFFF"
    return bg, fg


def _load_font(preferred_size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    # Try common fonts; fallback to PIL default
    candidate_paths = [
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/SFNS.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/Library/Fonts/Arial.ttf",
        "/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for path in candidate_paths:
        p = Path(path)
        if p.exists():
            try:
                return ImageFont.truetype(str(p), preferred_size)
            except Exception:
                continue
    return ImageFont.load_default()


def _draw_logo_png(bg_hex: str, fg_hex: str, size: int, letter: str = "К") -> Image.Image:
    img = Image.new("RGB", (size, size), color=bg_hex)
    draw = ImageDraw.Draw(img)
    # Circle background with margins
    margin = int(size * 0.03125)  # ~ 20px on 640
    draw.ellipse((margin, margin, size - margin, size - margin), fill=bg_hex)

    # Draw letter
    font_size = int(size * 0.56)
    font = _load_font(font_size)
    # Measure text bounding box
    bbox = draw.textbbox((0, 0), letter, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = (size - w) // 2
    y = (size - h) // 2 - int(size * 0.04)
    draw.text((x, y), letter, fill=fg_hex, font=font)
    return img


def export_pngs(src_svg: Path, out_dir: Path, prefix: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    bg_hex, fg_hex = _extract_colors_from_svg(src_svg)
    for size in SIZES:
        img = _draw_logo_png(bg_hex, fg_hex, size)
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


