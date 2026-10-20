"""Optical and physical-artifact stages.

The teardown's central finding: the category does not sell filters, it sells
*cameras*. A camera is not a colour grade. It is a grade plus a lens plus a
frame plus a date stamp plus whatever light was leaking past its back door.
These are the stages that carry that, and they are what a LUT structurally
cannot express.

All geometry here is expressed as a fraction of image width, never in pixels,
so preview and capture agree. That is the same parity invariant the render
graph enforces.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter, map_coordinates

_EPS = 1e-6


def _radial_grid(h: int, w: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Normalised centred coordinates and radius. Radius is 1.0 at the corners."""
    yy = np.linspace(-1.0, 1.0, h, dtype=np.float32)[:, None]
    xx = np.linspace(-1.0, 1.0, w, dtype=np.float32)[None, :]
    aspect = w / max(h, 1)
    r = np.sqrt((xx * aspect) ** 2 + yy**2) / max(np.sqrt(aspect**2 + 1.0), _EPS)
    return yy, xx, r.astype(np.float32)


def chromatic_aberration(rgb: np.ndarray, amount: float = 0.0) -> np.ndarray:
    """Lateral chromatic aberration: radial per-channel magnification difference.

    A cheap lens does not focus all wavelengths to the same image height, so red
    and blue land at slightly different radii. The tell is colour fringing that
    *grows toward the corners* and is absent at the centre. A uniform RGB offset
    is the wrong model and reads as a glitch effect rather than as a lens.

    `amount` is the fractional radius difference, roughly [0, 0.004].
    """
    if amount <= 0.0:
        return rgb
    h, w = rgb.shape[:2]
    yy, xx, _ = _radial_grid(h, w)

    out = np.empty_like(rgb)
    # Green is the reference; red magnifies slightly more, blue slightly less.
    for ch, scale in ((0, 1.0 + amount), (1, 1.0), (2, 1.0 - amount)):
        if scale == 1.0:
            out[..., ch] = rgb[..., ch]
            continue
        sy = (yy / scale + 1.0) * 0.5 * (h - 1)
        sx = (xx / scale + 1.0) * 0.5 * (w - 1)
        coords = np.broadcast_arrays(sy, sx)
        out[..., ch] = map_coordinates(
            rgb[..., ch], [coords[0], coords[1]], order=1, mode="nearest"
        )
    return out.astype(np.float32)


def lens_softness(rgb: np.ndarray, amount: float = 0.0, centre_hold: float = 0.45) -> np.ndarray:
    """Corner softness. Sharp in the middle, mushy at the edges.

    Every cheap lens does this and no digital filter does, which is part of why
    a plain colour filter still reads as a phone photo. Implemented as a blend
    toward a blurred copy, weighted by radius.
    """
    if amount <= 0.0:
        return rgb
    h, w = rgb.shape[:2]
    _, _, r = _radial_grid(h, w)
    sigma = max(amount * w * 0.01, 0.6)
    blurred = gaussian_filter(rgb, sigma=(sigma, sigma, 0.0))
    t = np.clip((r - centre_hold) / max(1.0 - centre_hold, _EPS), 0.0, 1.0) ** 2
    return (rgb * (1.0 - t[..., None]) + blurred * t[..., None]).astype(np.float32)


def light_leak(
    rgb: np.ndarray,
    seed: int = 0,
    strength: float = 0.0,
    tint: tuple[float, float, float] = (1.0, 0.42, 0.14),
) -> np.ndarray:
    """A seeded, procedural light leak entering from one edge.

    Stores a *seed*, not a baked texture, so re-rendering a shot months later
    reproduces the identical leak. That is what makes the roll genuinely
    re-editable rather than merely re-gradeable.

    Modelled as a soft wedge from a random edge with a couple of hot streaks,
    screen-blended. Real leaks are directional and fall off along the film
    travel direction, so a centred radial glow is the wrong shape.
    """
    if strength <= 0.0:
        return rgb
    h, w = rgb.shape[:2]
    rng = np.random.default_rng(seed)

    yy = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None]
    xx = np.linspace(0.0, 1.0, w, dtype=np.float32)[None, :]

    edge = int(rng.integers(0, 4))
    along = [xx, 1.0 - xx, yy, 1.0 - yy][edge]
    across = [yy, yy, xx, xx][edge]

    # Main wedge: bright at the edge, decaying inward, with a soft vertical bias.
    falloff = float(rng.uniform(2.2, 4.5))
    wedge = np.exp(-along * falloff)
    bias = 0.55 + 0.45 * np.sin(across * np.pi * float(rng.uniform(0.6, 1.4)) + rng.uniform(0, 3.14))
    leak = wedge * bias

    # A couple of hotter streaks riding the wedge.
    for _ in range(int(rng.integers(1, 3))):
        pos = float(rng.uniform(0.05, 0.95))
        width_ = float(rng.uniform(0.04, 0.16))
        leak = leak + np.exp(-((across - pos) ** 2) / (2 * width_**2)) * wedge * rng.uniform(0.4, 0.9)

    leak = gaussian_filter(np.broadcast_to(leak, (h, w)).astype(np.float32), sigma=w * 0.01)
    leak = leak / max(float(leak.max()), _EPS)

    glow = leak[..., None] * np.asarray(tint, dtype=np.float32) * strength
    # Screen blend: keeps highlights from simply clipping to white.
    return (1.0 - (1.0 - np.clip(rgb, 0, 1)) * (1.0 - np.clip(glow, 0, 1))).astype(np.float32)


# --- date stamp -------------------------------------------------------------
# Seven-segment layout:      --a--
#                           f     b
#                            --g--
#                           e     c
#                            --d--
_SEGMENTS = {
    "0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc",
    "5": "afgcd", "6": "afgecd", "7": "abc", "8": "abcdefg", "9": "afgbcd",
    " ": "",
}


def _draw_digit(canvas: np.ndarray, ch: str, x0: int, y0: int, dw: int, dh: int, t: int) -> None:
    """Paint one seven-segment glyph into a single-channel canvas."""
    segs = _SEGMENTS.get(ch, "")
    mid = y0 + dh // 2

    def bar(y, x, hh, ww):
        canvas[max(y, 0) : y + hh, max(x, 0) : x + ww] = 1.0

    if "a" in segs: bar(y0, x0 + t, t, dw - 2 * t)
    if "d" in segs: bar(y0 + dh - t, x0 + t, t, dw - 2 * t)
    if "g" in segs: bar(mid - t // 2, x0 + t, t, dw - 2 * t)
    if "f" in segs: bar(y0 + t, x0, mid - y0 - t, t)
    if "b" in segs: bar(y0 + t, x0 + dw - t, mid - y0 - t, t)
    if "e" in segs: bar(mid, x0, y0 + dh - mid - t, t)
    if "c" in segs: bar(mid, x0 + dw - t, y0 + dh - mid - t, t)


def date_stamp(
    rgb: np.ndarray,
    text: str = "'26 9 18",
    strength: float = 1.0,
    corner: str = "bottomRight",
    size_pct: float = 0.035,
    tint: tuple[float, float, float] = (1.0, 0.36, 0.06),
    glow: float = 1.0,
) -> np.ndarray:
    """The orange seven-segment date burn, composited additively with a glow.

    Additive, not alpha-blended. The real thing is light exposing the negative
    from a small LED behind the film gate, so it *adds* and it blooms into its
    surroundings. Alpha compositing gives flat orange text sitting on top of the
    photo, which is the single most common way this effect is done badly.
    """
    if strength <= 0.0:
        return rgb
    h, w = rgb.shape[:2]

    dh = max(int(size_pct * w), 8)
    dw = max(int(dh * 0.62), 5)
    t = max(int(dh * 0.16), 1)
    gap = max(int(dw * 0.30), 2)
    margin = max(int(w * 0.045), 6)

    total_w = len(text) * (dw + gap)
    canvas = np.zeros((h, w), dtype=np.float32)

    x = w - margin - total_w if "Right" in corner else margin
    y = h - margin - dh if "bottom" in corner else margin
    for ch in text:
        if ch != " ":
            _draw_digit(canvas, ch, x, y, dw, dh, t)
        x += dw + gap

    # The glow is what sells it: a tight core plus a wide halo, same multi-scale
    # logic as halation, because it is the same physical phenomenon.
    if glow > 0.0:
        tight = gaussian_filter(canvas, sigma=dh * 0.06)
        wide = gaussian_filter(canvas, sigma=dh * 0.30)
        canvas = canvas + (tight * 0.6 + wide * 0.9) * glow

    burn = canvas[..., None] * np.asarray(tint, dtype=np.float32) * strength
    return np.clip(rgb + burn, 0.0, 1.0).astype(np.float32)


def film_border(rgb: np.ndarray, style: str = "none", strength: float = 1.0) -> np.ndarray:
    """Composite a physical frame around the image.

    `"sprocket"` reproduces the 35mm perforation strip the reference app uses
    for its film-frame camera. The image is inset and the surrounding base is
    drawn, rather than the border being overlaid, because a real frame occludes
    rather than tints.
    """
    if style == "none" or strength <= 0.0:
        return rgb
    h, w = rgb.shape[:2]

    if style == "sprocket":
        band = max(int(h * 0.11), 6)
        out = np.zeros_like(rgb)
        inner_h = h - 2 * band
        ys = (np.arange(inner_h, dtype=np.float32) / max(inner_h - 1, 1) * (h - 1)).astype(np.int32)
        out[band : band + inner_h] = rgb[ys]

        # Film base is very dark but not pure black, with a slight warm cast.
        base = np.array([0.055, 0.048, 0.042], dtype=np.float32)
        out[:band] = base
        out[band + inner_h :] = base

        # Perforations: rounded-ish rectangles at a regular pitch.
        pitch = max(int(w * 0.075), 10)
        pw = max(int(pitch * 0.46), 4)
        ph = max(int(band * 0.42), 3)
        for x in range(pitch // 2, w - pw, pitch):
            for y0 in (int(band * 0.29), h - band + int(band * 0.29)):
                out[y0 : y0 + ph, x : x + pw] = 0.88
        return out.astype(np.float32)

    if style == "instant":
        # Wide chin at the bottom, like an instant print.
        side = max(int(w * 0.055), 5)
        chin = max(int(h * 0.20), 12)
        out = np.full_like(rgb, 0.93)
        inner_h = h - side - chin
        inner_w = w - 2 * side
        ys = (np.arange(inner_h, dtype=np.float32) / max(inner_h - 1, 1) * (h - 1)).astype(np.int32)
        xs = (np.arange(inner_w, dtype=np.float32) / max(inner_w - 1, 1) * (w - 1)).astype(np.int32)
        out[side : side + inner_h, side : side + inner_w] = rgb[ys][:, xs]
        return out.astype(np.float32)

    return rgb
