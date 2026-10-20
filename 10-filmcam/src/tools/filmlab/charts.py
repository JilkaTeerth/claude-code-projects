"""Synthetic test images.

Judging a look on a photograph is misleading: a warm cast looks great on one
sunset and awful on the next. These charts isolate the things that actually
distinguish a good look from a bad one.

  * `color_chart`   — does the grade hold colour relationships, or collapse them?
  * `grey_ramp`     — does the tone curve invert, band, or crush anywhere?
  * `skin_strip`    — the single most unforgiving test. A look that ruins skin
                      across the tonal range is not usable regardless of how
                      good it looks on a landscape.
  * `highlight_scene` — a deliberately blown highlight next to a dark edge, which
                      is the only way to see whether halation reads as film or
                      as cheap bloom.
"""

from __future__ import annotations

import numpy as np

# Standard 24-patch reference chart values in 8-bit sRGB. These are published
# colorimetric measurement data, used here as a calibration target.
CHART_PATCHES = [
    (115, 82, 68),   (194, 150, 130), (98, 122, 157),  (87, 108, 67),
    (133, 128, 177), (103, 189, 170), (214, 126, 44),  (80, 91, 166),
    (193, 90, 99),   (94, 60, 108),   (157, 188, 64),  (224, 163, 46),
    (56, 61, 150),   (70, 148, 73),   (175, 54, 60),   (231, 199, 31),
    (187, 86, 149),  (8, 133, 161),   (243, 243, 242), (200, 200, 200),
    (160, 160, 160), (122, 122, 121), (85, 85, 85),    (52, 52, 52),
]

# A range of real-world skin tones, light through deep. Chosen to span the range
# rather than to represent any individual.
SKIN_TONES = [
    (255, 224, 196), (241, 194, 165), (224, 172, 144), (198, 145, 116),
    (172, 120, 92),  (141, 96, 71),   (110, 74, 54),   (79, 52, 38),
]


def _to_float(rgb8: tuple[int, int, int]) -> np.ndarray:
    return np.array(rgb8, dtype=np.float32) / 255.0


def color_chart(patch: int = 96, cols: int = 6, gutter: int = 8) -> np.ndarray:
    """The 24-patch chart, laid out 6 x 4."""
    rows = (len(CHART_PATCHES) + cols - 1) // cols
    h = rows * patch + (rows + 1) * gutter
    w = cols * patch + (cols + 1) * gutter
    img = np.full((h, w, 3), 0.18, dtype=np.float32)
    for i, colour in enumerate(CHART_PATCHES):
        r, c = divmod(i, cols)
        y = gutter + r * (patch + gutter)
        x = gutter + c * (patch + gutter)
        img[y : y + patch, x : x + patch] = _to_float(colour)
    return img


def grey_ramp(width: int = 640, height: int = 96, steps: int = 0) -> np.ndarray:
    """A horizontal ramp. `steps > 0` gives discrete patches instead of a gradient."""
    if steps > 0:
        vals = np.repeat(np.linspace(0.0, 1.0, steps, dtype=np.float32), width // steps + 1)[:width]
    else:
        vals = np.linspace(0.0, 1.0, width, dtype=np.float32)
    return np.tile(vals[None, :, None], (height, 1, 3)).astype(np.float32)


def skin_strip(patch: int = 80, gutter: int = 8) -> np.ndarray:
    """Skin tones across the range, each shown at three exposures.

    The three exposures matter: a look can flatter skin at correct exposure and
    turn it green a stop down, which you would never catch on a single patch.
    """
    rows = 3
    cols = len(SKIN_TONES)
    h = rows * patch + (rows + 1) * gutter
    w = cols * patch + (cols + 1) * gutter
    img = np.full((h, w, 3), 0.18, dtype=np.float32)
    for r, ev in enumerate((-1.0, 0.0, 0.75)):
        for c, tone in enumerate(SKIN_TONES):
            colour = np.clip(_to_float(tone) * (2.0**ev), 0.0, 1.0)
            y = gutter + r * (patch + gutter)
            x = gutter + c * (patch + gutter)
            img[y : y + patch, x : x + patch] = colour
    return img


def highlight_scene(size: int = 320) -> np.ndarray:
    """A blown highlight against a dark field, plus a hard edge.

    Halation only announces itself where very bright meets very dark, so this is
    the image that tells you whether the halation parameters are doing anything
    real or just fogging the frame.
    """
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    img = np.full((size, size, 3), 0.04, dtype=np.float32)

    # A hot, slightly clipped disc.
    cy, cx, r = size * 0.38, size * 0.38, size * 0.14
    disc = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    img[disc < r] = 1.0
    halo = np.clip(1.0 - (disc - r) / (r * 0.35), 0.0, 1.0)
    img = np.maximum(img, halo[..., None] * 0.95)

    # A hard bright/dark edge in the lower half.
    img[int(size * 0.68) : int(size * 0.80), : int(size * 0.55)] = 0.98
    # A midtone patch so the grain weighting has somewhere to show up.
    img[int(size * 0.85) : , :] = 0.45
    return np.clip(img, 0.0, 1.0).astype(np.float32)


def test_sheet() -> np.ndarray:
    """All four charts stacked into one image, for per-look review."""
    chart = color_chart()
    width = chart.shape[1]

    def fit(img: np.ndarray) -> np.ndarray:
        if img.shape[1] == width:
            return img
        scale = width / img.shape[1]
        h = max(int(round(img.shape[0] * scale)), 1)
        ys = np.clip((np.arange(h) / scale).astype(np.int32), 0, img.shape[0] - 1)
        xs = np.clip((np.arange(width) / scale).astype(np.int32), 0, img.shape[1] - 1)
        return img[ys][:, xs]

    parts = [chart, fit(skin_strip()), fit(grey_ramp(steps=16)), fit(highlight_scene())]
    return np.concatenate(parts, axis=0).astype(np.float32)
