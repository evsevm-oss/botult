from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw
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


def _draw_logo_png(bg_hex: str, fg_hex: str, size: int) -> Image.Image:
    img = Image.new("RGB", (size, size), color=bg_hex)
    draw = ImageDraw.Draw(img)
    # Circle background with margins
    margin = int(size * 0.03125)  # ~ 20px on 640
    draw.ellipse((margin, margin, size - margin, size - margin), fill=bg_hex)

    # Draw geometric "U" (rounded thick shape) inspired by the character's chest mark
    cx = cy = size // 2
    u_width = int(size * 0.48)
    u_height = int(size * 0.55)
    thickness = max(8, int(size * 0.14))
    radius = thickness // 2

    top_y = cy - u_height // 2
    bot_y = cy + u_height // 2

    # Left bar
    left_x = cx - (u_width // 2 - thickness // 2)
    left_rect = (left_x - thickness // 2, top_y, left_x + thickness // 2, bot_y - thickness // 2)
    draw.rounded_rectangle(left_rect, radius=radius, fill=fg_hex)

    # Right bar
    right_x = cx + (u_width // 2 - thickness // 2)
    right_rect = (right_x - thickness // 2, top_y, right_x + thickness // 2, bot_y - thickness // 2)
    draw.rounded_rectangle(right_rect, radius=radius, fill=fg_hex)

    # Bottom bridge
    bottom_rect = (cx - u_width // 2, bot_y - thickness, cx + u_width // 2, bot_y)
    draw.rounded_rectangle(bottom_rect, radius=radius, fill=fg_hex)
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


