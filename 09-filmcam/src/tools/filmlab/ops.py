"""Parametric colour operations.

Every op takes and returns a float32 array shaped (..., 3) holding
display-referred sRGB in roughly [0, 1]. Ops may push values slightly outside
that range; clip once at the end of a chain rather than after every step, so
intermediate headroom is not thrown away.

These are the building blocks a look is made of. A look is a named sequence of
these calls with its own parameters, which means the parameters *are* the
artwork and they live in git history.
"""

from __future__ import annotations

import numpy as np
from scipy.interpolate import PchipInterpolator

# Rec. 709 luma weights. Used everywhere we need "how bright is this pixel".
LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)

_EPS = 1e-6


def luma(rgb: np.ndarray) -> np.ndarray:
    """Per-pixel luminance, shape (...,) with the trailing channel axis dropped."""
    return rgb @ LUMA


def srgb_to_linear(rgb: np.ndarray) -> np.ndarray:
    """Inverse sRGB transfer function.

    Note the honest caveat: phone output is already ISP tone-mapped and clipped,
    so this recovers a *relative* linear signal, not scene-referred light. There
    is no real highlight headroom to recover.
    """
    rgb = np.asarray(rgb, dtype=np.float32)
    return np.where(
        rgb <= 0.04045,
        rgb / 12.92,
        np.power(np.clip(rgb + 0.055, _EPS, None) / 1.055, 2.4),
    ).astype(np.float32)


def linear_to_srgb(rgb: np.ndarray) -> np.ndarray:
    """Forward sRGB transfer function."""
    rgb = np.asarray(rgb, dtype=np.float32)
    return np.where(
        rgb <= 0.0031308,
        rgb * 12.92,
        1.055 * np.power(np.clip(rgb, _EPS, None), 1.0 / 2.4) - 0.055,
    ).astype(np.float32)


def exposure(rgb: np.ndarray, ev: float) -> np.ndarray:
    """Exposure in stops, applied in linear light so it behaves like real exposure."""
    if ev == 0.0:
        return rgb
    lin = srgb_to_linear(rgb) * (2.0**ev)
    return linear_to_srgb(lin)


def temperature_tint(rgb: np.ndarray, temp: float = 0.0, tint: float = 0.0) -> np.ndarray:
    """Cheap white-balance trim.

    `temp` positive is warmer (red up, blue down). `tint` positive pushes magenta,
    negative pushes green. Both are roughly [-0.3, 0.3] before it gets silly.
    """
    if temp == 0.0 and tint == 0.0:
        return rgb
    gain = np.array(
        [1.0 + temp, 1.0 - 0.5 * tint, 1.0 - temp],
        dtype=np.float32,
    )
    return rgb * gain


def asc_cdl(
    rgb: np.ndarray,
    slope: tuple[float, float, float] = (1.0, 1.0, 1.0),
    offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
    power: tuple[float, float, float] = (1.0, 1.0, 1.0),
) -> np.ndarray:
    """ASC CDL: out = (in * slope + offset) ^ power, per channel.

    The industry-standard primary grade. Slope is gain, offset is lift, power is
    gamma. Doing all three per-channel is most of what separates one film look
    from another.
    """
    s = np.asarray(slope, dtype=np.float32)
    o = np.asarray(offset, dtype=np.float32)
    p = np.asarray(power, dtype=np.float32)
    out = rgb * s + o
    return np.power(np.clip(out, _EPS, None), p).astype(np.float32)


def crosstalk(rgb: np.ndarray, amount: float, bias: tuple[float, float, float] | None = None) -> np.ndarray:
    """Channel contamination between emulsion layers.

    This is the op that makes a LUT feel photochemical rather than like a slider
    preset. On real colour film the three dye layers are not cleanly separated:
    each records a little of what its neighbours record. Digital never does this,
    which is part of why untreated digital reads as "clean" and film does not.

    `amount` is how much each channel bleeds into the others, roughly [0, 0.15].
    `bias` optionally weights which channel donates most; defaults to even.
    """
    if amount <= 0.0:
        return rgb
    b = np.ones(3, dtype=np.float32) if bias is None else np.asarray(bias, dtype=np.float32)
    b = b / max(float(b.sum()), _EPS) * 3.0

    m = np.eye(3, dtype=np.float32)
    for i in range(3):
        for j in range(3):
            if i != j:
                m[i, j] = amount * b[j]
    # Renormalise rows so a neutral stays neutral instead of drifting brighter.
    m = m / m.sum(axis=1, keepdims=True)
    return (rgb @ m.T).astype(np.float32)


def saturation(rgb: np.ndarray, amount: float) -> np.ndarray:
    """Global saturation about the luma axis. 1.0 is a no-op."""
    if amount == 1.0:
        return rgb
    l = luma(rgb)[..., None]
    return (l + (rgb - l) * amount).astype(np.float32)


def split_tone(
    rgb: np.ndarray,
    shadow_tint: tuple[float, float, float] = (0.0, 0.0, 0.0),
    highlight_tint: tuple[float, float, float] = (0.0, 0.0, 0.0),
    balance: float = 0.5,
    strength: float = 1.0,
) -> np.ndarray:
    """Push one colour into the shadows and a different one into the highlights.

    This is where a lot of a look's identity comes from: cool shadows with warm
    highlights reads as one era, warm shadows with cyan highlights as another.
    `balance` moves the crossover point between the two.
    """
    if strength <= 0.0:
        return rgb
    l = luma(rgb)[..., None]
    # smoothstep around the balance point so the handover is not a hard line
    t = np.clip((l - balance + 0.5), 0.0, 1.0)
    t = (t * t * (3.0 - 2.0 * t)).astype(np.float32)

    sh = np.asarray(shadow_tint, dtype=np.float32)
    hi = np.asarray(highlight_tint, dtype=np.float32)
    return (rgb + (sh * (1.0 - t) + hi * t) * strength).astype(np.float32)


def highlight_rolloff(rgb: np.ndarray, strength: float = 0.0, knee: float = 0.7) -> np.ndarray:
    """Desaturate toward white as values approach clipping.

    Real film does not hit a hard saturated clip; bright saturated areas bleach
    toward white. Without this, blown highlights keep their colour and read as
    digital.
    """
    if strength <= 0.0:
        return rgb
    l = luma(rgb)[..., None]
    t = np.clip((l - knee) / max(1.0 - knee, _EPS), 0.0, 1.0)
    t = (t * t).astype(np.float32) * strength
    return (rgb * (1.0 - t) + np.ones_like(rgb) * l * t).astype(np.float32)


def _curve_table(points: list[tuple[float, float]], size: int = 1024) -> np.ndarray:
    """Build a monotonic 1D lookup from control points.

    PCHIP is the right interpolator here: it is monotonic by construction, so a
    tone curve can never invert and produce a solarised region, which a plain
    cubic spline happily will.
    """
    pts = sorted(points)
    xs = np.array([p[0] for p in pts], dtype=np.float64)
    ys = np.array([p[1] for p in pts], dtype=np.float64)
    interp = PchipInterpolator(xs, ys, extrapolate=True)
    grid = np.linspace(0.0, 1.0, size, dtype=np.float64)
    return np.clip(interp(grid), 0.0, 1.0).astype(np.float32)


def apply_curve(rgb: np.ndarray, table: np.ndarray) -> np.ndarray:
    """Apply a 1D table (from `_curve_table`) to every channel."""
    size = table.shape[0]
    idx = np.clip(rgb, 0.0, 1.0) * (size - 1)
    lo = np.floor(idx).astype(np.int32)
    hi = np.minimum(lo + 1, size - 1)
    frac = (idx - lo).astype(np.float32)
    return (table[lo] * (1.0 - frac) + table[hi] * frac).astype(np.float32)


def tone_curve(
    rgb: np.ndarray,
    black_point: float = 0.0,
    white_point: float = 1.0,
    toe_lift: float = 0.0,
    shoulder: float = 0.0,
    contrast: float = 1.0,
) -> np.ndarray:
    """The film-ish S-curve, expressed as parameters rather than raw points.

    `toe_lift` raises the blacks (the single most recognisable "faded film" move).
    `shoulder` compresses the highlights so they roll off instead of clipping.
    `contrast` steepens the midtones around 0.5.
    """
    mid = 0.5
    # contrast is a DEVIATION from neutral, not a multiplier on the curve's
    # steepness. With `0.25 * contrast`, contrast=1.0 still bent the curve by
    # up to 0.085 from identity, so every look carried an unintended baseline
    # S-curve and the parameter did not mean what its name said. That makes a
    # profile impossible to calibrate, because you cannot reason about what
    # you are tuning. At contrast=1.0 this now returns identity exactly.
    steep = 0.25 * (contrast - 1.0)

    points = [
        (0.0, float(np.clip(black_point + toe_lift, 0.0, 1.0))),
        (0.25, float(np.clip(black_point + toe_lift + (0.25 - steep * 0.35), 0.0, 1.0))),
        (mid, mid),
        (0.75, float(np.clip(0.75 + steep * 0.35 - shoulder * 0.35, 0.0, 1.0))),
        (1.0, float(np.clip(white_point - shoulder * 0.12, 0.0, 1.0))),
    ]
    # PCHIP needs strictly increasing y to stay sane; nudge any flat/inverted run.
    for i in range(1, len(points)):
        if points[i][1] <= points[i - 1][1]:
            points[i] = (points[i][0], points[i - 1][1] + 1e-4)

    return apply_curve(rgb, _curve_table(points))


def channel_curves(
    rgb: np.ndarray,
    red: list[tuple[float, float]] | None = None,
    green: list[tuple[float, float]] | None = None,
    blue: list[tuple[float, float]] | None = None,
) -> np.ndarray:
    """Independent per-channel curves, for crossed-over looks.

    Shifting the red curve up in the shadows and the blue curve down in the
    highlights is how you get the classic warm-shadow / cool-highlight cross
    process feel that no single global curve can produce.
    """
    out = rgb.copy()
    for ch, pts in enumerate((red, green, blue)):
        if pts:
            out[..., ch] = apply_curve(rgb[..., ch : ch + 1], _curve_table(pts))[..., 0]
    return out


def monochrome(
    rgb: np.ndarray,
    weights: tuple[float, float, float] = (0.2126, 0.7152, 0.0722),
    tone: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> np.ndarray:
    """Collapse to greyscale with custom channel weights, then optionally tone it.

    Channel weights matter: a red-heavy mix darkens skies and lightens skin,
    which is the difference between a flat desaturation and a black-and-white
    that looks deliberate. `tone` adds a selenium or sepia cast.
    """
    w = np.asarray(weights, dtype=np.float32)
    w = w / max(float(w.sum()), _EPS)
    grey = (rgb @ w)[..., None]
    return (grey + np.asarray(tone, dtype=np.float32) * grey * (1.0 - grey) * 4.0).astype(np.float32)
