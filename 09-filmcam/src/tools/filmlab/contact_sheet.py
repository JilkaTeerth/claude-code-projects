"""Contact sheets — the review surface.

Everything here exists so look design happens on the Mac rather than through a
rebuild-and-squint loop on a phone that needs re-signing every seven days.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def to_pil(rgb: np.ndarray) -> Image.Image:
    arr = (np.clip(rgb, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    return Image.fromarray(arr, mode="RGB")


def _font(size: int = 16) -> ImageFont.ImageFont:
    for path in (
        "/System/Library/Fonts/SFNSMono.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Supplemental/Courier New.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def grid(
    tiles: list[tuple[str, np.ndarray]],
    cols: int = 5,
    pad: int = 12,
    label_h: int = 26,
    bg: tuple[int, int, int] = (20, 20, 22),
) -> Image.Image:
    """Lay out labelled tiles in a grid. Tiles may differ in size; the cell is
    sized to the largest and everything is top-left anchored."""
    if not tiles:
        raise ValueError("no tiles to lay out")

    cell_w = max(t[1].shape[1] for t in tiles)
    cell_h = max(t[1].shape[0] for t in tiles)
    rows = (len(tiles) + cols - 1) // cols

    W = cols * cell_w + (cols + 1) * pad
    H = rows * (cell_h + label_h) + (rows + 1) * pad
    sheet = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(sheet)
    font = _font(15)

    for i, (label, img) in enumerate(tiles):
        r, c = divmod(i, cols)
        x = pad + c * (cell_w + pad)
        y = pad + r * (cell_h + label_h + pad)
        sheet.paste(to_pil(img), (x, y))
        draw.text((x + 2, y + cell_h + 5), label, fill=(225, 225, 228), font=font)

    return sheet


def save(sheet: Image.Image, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path, quality=92)
    return path
