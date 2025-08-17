from __future__ import annotations

import argparse
import json
from pathlib import Path


LOGO_TEMPLATE = """
<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"640\" height=\"640\" viewBox=\"0 0 640 640\">
  <defs>
    <style>
      .bg {{ fill: {bg}; }}
      .u {{ fill: {fg}; }}
      .glow {{ filter: url(#glow); }}
    </style>
    <filter id=\"glow\" x=\"-50%\" y=\"-50%\" width=\"200%\" height=\"200%\">
      <feGaussianBlur stdDeviation=\"8\" result=\"coloredBlur\"/>
      <feMerge>
        <feMergeNode in=\"coloredBlur\"/>
        <feMergeNode in=\"SourceGraphic\"/>
      </feMerge>
    </filter>
  </defs>
  <circle class=\"bg\" cx=\"320\" cy=\"320\" r=\"310\" />
  <!-- Stylized U with glow -->
  <g class=\"glow\">
    <rect class=\"u\" x=\"190\" y=\"150\" rx=\"26\" width=\"48\" height=\"340\"/>
    <rect class=\"u\" x=\"402\" y=\"150\" rx=\"26\" width=\"48\" height=\"340\"/>
    <rect class=\"u\" x=\"206\" y=\"420\" rx=\"26\" width=\"228\" height=\"48\"/>
  </g>
</svg>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Build SVG logos from palette.json")
    parser.add_argument("--palette", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    data = json.loads(args.palette.read_text(encoding="utf-8"))
    roles = data["roles"]

    light_svg = LOGO_TEMPLATE.format(bg=roles["primary"], fg="#FFFFFF")
    dark_svg = LOGO_TEMPLATE.format(bg=roles["neutral_dark"], fg=roles["primary"])

    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)
    (out / "logo-light.svg").write_text(light_svg, encoding="utf-8")
    (out / "logo-dark.svg").write_text(dark_svg, encoding="utf-8")


if __name__ == "__main__":
    main()


