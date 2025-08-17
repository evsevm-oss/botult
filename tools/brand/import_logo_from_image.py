from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageOps


SIZES = (640, 512, 200)


def _tight_crop_nonwhite(img: Image.Image, white_threshold: int = 250) -> Image.Image:
    """Crop away near-white margins (assumes provided logo on white bg)."""
    gray = ImageOps.grayscale(img)
    # Build binary mask for pixels darker than white_threshold
    mask = gray.point(lambda p: 255 if p < white_threshold else 0).convert("L")
    bbox = mask.getbbox()
    if bbox is None:
        return img
    cropped = img.crop(bbox)
    # Make square canvas by padding
    w, h = cropped.size
    side = max(w, h)
    canvas = Image.new("RGBA", (side, side), (255, 255, 255, 0))
    offset = ((side - w) // 2, (side - h) // 2)
    canvas.paste(cropped, offset)
    return canvas


def import_logo(source: Path, out_dir: Path) -> None:
    image = Image.open(source).convert("RGBA")
    square = _tight_crop_nonwhite(image)

    # Export to light/dark folders (same asset, as requested "exactly like provided")
    for theme in ("light", "dark"):
        theme_dir = out_dir / theme
        theme_dir.mkdir(parents=True, exist_ok=True)
        for size in SIZES:
            resized = square.resize((size, size), Image.LANCZOS)
            target = theme_dir / f"logo-{size}.png"
            resized.save(target, format="PNG")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import provided U-logo image and export required sizes")
    parser.add_argument("--image", type=Path, required=True, help="path to provided U logo image")
    parser.add_argument(
        "--out-dir", type=Path, required=True, help="output dir, typically data/brand/exports"
    )
    args = parser.parse_args()

    import_logo(args.image, args.out_dir)


if __name__ == "__main__":
    main()


