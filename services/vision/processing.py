from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PIL import Image as PILImage, ImageOps
import io


@dataclass
class ProcessedImage:
    bytes: bytes
    width: int
    height: int
    content_type: str


def preprocess_photo(raw_bytes: bytes, content_type: str) -> ProcessedImage:
    # Basic orientation/resize and compression
    with PILImage.open(io.BytesIO(raw_bytes)) as im:
        im = ImageOps.exif_transpose(im)
        max_side = 1600
        w, h = im.size
        scale = min(1.0, max_side / max(w, h))
        if scale < 1.0:
            im = im.resize((int(w * scale), int(h * scale)))
        buf = io.BytesIO()
        if content_type == "image/png":
            im.save(buf, format="PNG", optimize=True)
            ct = "image/png"
        else:
            im = im.convert("RGB")
            im.save(buf, format="JPEG", quality=85, optimize=True)
            ct = "image/jpeg"
        data = buf.getvalue()
        return ProcessedImage(bytes=data, width=im.width, height=im.height, content_type=ct)


