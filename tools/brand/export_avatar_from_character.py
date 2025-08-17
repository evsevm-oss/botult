from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


SIZES = (640, 512, 200)


def biased_center_crop(img: Image.Image, bias_y: float = -0.08, scale: float = 0.9) -> Image.Image:
    """
    Square crop with vertical bias toward the face (slightly above center).
    bias_y: negative raises crop (faces usually above vertical center)
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

    return img.crop((left, top, right, bottom))


def main() -> None:
    parser = argparse.ArgumentParser(description="Export Telegram avatar from character image (face crop)")
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--bias-y", type=float, default=-0.08)
    parser.add_argument("--scale", type=float, default=0.9)
    args = parser.parse_args()

    img = Image.open(args.image).convert("RGB")
    crop = biased_center_crop(img, bias_y=args.bias_y, scale=args.scale)

    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    for size in SIZES:
        resized = crop.resize((size, size), Image.LANCZOS)
        target = out / f"avatar-{size}.png"
        resized.save(target, format="PNG")


if __name__ == "__main__":
    main()


