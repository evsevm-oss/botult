from __future__ import annotations

import argparse
import json
from pathlib import Path


LOGO_LIGHT = """
<svg xmlns="http://www.w3.org/2000/svg" width="640" height="640" viewBox="0 0 640 640">
  <defs>
    <style>
      .bg {{ fill: {bg}; }}
      .fg {{ fill: {fg}; font-family: -apple-system,BlinkMacSystemFont,Segoe UI,Roboto,Inter,Arial; font-weight: 700; }}
    </style>
  </defs>
  <circle class="bg" cx="320" cy="320" r="310" />
  <text class="fg" x="50%" y="55%" text-anchor="middle" font-size="360">К</text>
</svg>
"""

LOGO_DARK = LOGO_LIGHT  # тот же шаблон, меняются цвета


def main() -> None:
    parser = argparse.ArgumentParser(description="Build SVG logos from palette.json")
    parser.add_argument("--palette", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    data = json.loads(args.palette.read_text(encoding="utf-8"))
    roles = data["roles"]

    light_svg = LOGO_LIGHT.format(bg=roles["primary"], fg="#FFFFFF")
    dark_svg = LOGO_DARK.format(bg=roles["neutral_dark"], fg=roles["primary"])

    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    (out / "logo-light.svg").write_text(light_svg, encoding="utf-8")
    (out / "logo-dark.svg").write_text(dark_svg, encoding="utf-8")


if __name__ == "__main__":
    main()


