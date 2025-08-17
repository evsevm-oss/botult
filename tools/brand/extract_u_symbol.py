from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageOps


def frac_box(img_w: int, img_h: int, x: float, y: float, w: float, h: float) -> tuple[int, int, int, int]:
    left = int(x * img_w)
    top = int(y * img_h)
    right = int((x + w) * img_w)
    bottom = int((y + h) * img_h)
    return max(0, left), max(0, top), min(img_w, right), min(img_h, bottom)


def extract_symbol(image_path: Path, out_path: Path, bbox: tuple[float, float, float, float], threshold: int = 200) -> None:
    img = Image.open(image_path).convert("RGB")
    W, H = img.size
    box = frac_box(W, H, *bbox)
    crop = img.crop(box)

    gray = ImageOps.grayscale(crop)
    gray = ImageOps.autocontrast(gray, cutoff=2)

    # Bright parts considered as symbol (glowing U)
    mask = gray.point(lambda p: 255 if p >= threshold else 0).convert("L")

    # Build RGBA with white symbol on transparent bg
    out = Image.new("RGBA", crop.size, (255, 255, 255, 0))
    white = Image.new("RGBA", crop.size, (255, 255, 255, 255))
    out.paste(white, mask=mask)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.save(out_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract glowing U symbol from character chest (simple threshold)")
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--bbox", type=float, nargs=4, metavar=("X","Y","W","H"), default=(0.38, 0.52, 0.24, 0.22), help="fractional bbox on source image")
    parser.add_argument("--threshold", type=int, default=200)
    args = parser.parse_args()

    extract_symbol(args.image, args.out, tuple(args.bbox), args.threshold)


if __name__ == "__main__":
    main()


