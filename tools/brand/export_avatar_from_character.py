from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageOps, ImageFilter


SIZES = (640, 512, 200)


def biased_center_crop_box(img: Image.Image, bias_y: float, scale: float) -> tuple[int, int, int, int]:
    """
    Return crop box (left, top, right, bottom) for a square window.
    bias_y: positive moves window downward; negative upward.
    scale: fraction of min(w,h) to keep (0..1]
    """
    w, h = img.size
    side = int(min(w, h) * scale)
    cx = w / 2
    cy = h / 2 + h * bias_y

    left = int(cx - side / 2)
    top = int(cy - side / 2)
    right = left + side
    bottom = top + side

    # Clamp to image bounds
    if left < 0:
        right -= left
        left = 0
    if top < 0:
        bottom -= top
        top = 0
    if right > w:
        left -= (right - w)
        right = w
    if bottom > h:
        top -= (bottom - h)
        bottom = h

    return left, top, right, bottom


def ensure_top_safe_margin(
    img: Image.Image,
    box: tuple[int, int, int, int],
    *,
    safe_margin_frac: float = 0.1,
    edge_threshold: int = 18,
) -> tuple[int, int, int, int]:
    """
    Ensure there is at least safe_margin_frac of headroom at the top of the crop.
    Heuristic: detect earliest strong edges row in the center band and shift box UP if needed.
    """
    left, top, right, bottom = box
    crop = img.crop((left, top, right, bottom))
    side = crop.size[0]

    g = ImageOps.grayscale(crop)
    edges = g.filter(ImageFilter.FIND_EDGES)

    # Sum edges over center 50% width
    w, h = edges.size
    x0 = int(w * 0.25)
    x1 = int(w * 0.75)
    pixels = edges.load()
    y_min_edge = None
    for y in range(h):
        s = 0
        for x in range(x0, x1):
            s += pixels[x, y]
        if s / (x1 - x0) > edge_threshold:
            y_min_edge = y
            break

    if y_min_edge is None:
        return box

    safe_px = int(safe_margin_frac * side)
    if y_min_edge < safe_px:
        delta = safe_px - y_min_edge
        # shift UP (reduce top)
        top_new = max(0, top - delta)
        bottom_new = top_new + side
        # if bottom exceeds image (shouldn't when moving up), clamp
        if bottom_new > img.size[1]:
            bottom_new = img.size[1]
            top_new = bottom_new - side
        return left, top_new, right, bottom_new
    return box


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Telegram avatar from character image (face crop)")
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--bias-y", type=float, default=-0.06)
    parser.add_argument("--scale", type=float, default=0.82)
    parser.add_argument("--safe-top", type=float, default=0.15, help="safe headroom fraction at top (0..0.3)")
    parser.add_argument("--formats", type=str, default="png,webp,jpg", help="comma-separated: png,webp,jpg")
    args = parser.parse_args()

    img = Image.open(args.image).convert("RGB")
    box = biased_center_crop_box(img, bias_y=args.bias_y, scale=args.scale)
    box = ensure_top_safe_margin(img, box, safe_margin_frac=args.safe_top)
    crop = img.crop(box)

    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    fmts = [f.strip().lower() for f in args.formats.split(",") if f.strip()]
    for size in SIZES:
        resized = crop.resize((size, size), Image.LANCZOS)
        for ext in fmts:
            sub = out / ext
            sub.mkdir(parents=True, exist_ok=True)
            target = sub / f"avatar-{size}.{ext}"
            if ext in ("jpg", "jpeg"):
                rgb = resized.convert("RGB")
                rgb.save(target, format="JPEG", quality=92, optimize=True)
            elif ext == "webp":
                resized.save(target, format="WEBP", quality=92, method=6)
            else:
                resized.save(target, format="PNG")


if __name__ == "__main__":
    main()


