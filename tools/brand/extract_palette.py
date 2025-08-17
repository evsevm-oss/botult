from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Tuple

from PIL import Image


def extract_palette(image_path: Path, num_colors: int = 6) -> List[Tuple[int, int, int]]:
    image = Image.open(image_path).convert("RGB")
    small = image.resize((200, 200))
    pal = small.quantize(colors=num_colors, method=Image.MEDIANCUT)
    palette = pal.getpalette()[: num_colors * 3]
    colors = [tuple(palette[i : i + 3]) for i in range(0, len(palette), 3)]
    return colors


def to_hex(rgb: Tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % rgb


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract color palette from character image")
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--colors", type=int, default=6)
    args = parser.parse_args()

    colors = extract_palette(args.image, args.colors)

    # Heuristic roles: 0-primary, 1-accent, last = neutral_dark
    data = {
        "source": str(args.image),
        "colors": [to_hex(c) for c in colors],
        "roles": {
            "primary": to_hex(colors[0]) if colors else "#2E7D32",
            "accent": to_hex(colors[1]) if len(colors) > 1 else "#FF7043",
            "neutral_dark": to_hex(colors[-1]) if colors else "#263238",
            "white": "#FFFFFF",
            "black": "#000000",
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()


