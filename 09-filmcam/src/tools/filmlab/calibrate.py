"""The calibration harness: compare a rendered image against a reference photo.

CLAUDE.md section 7 is the reason this module exists before any profile does:
"the engine is worthless with invented parameters... build the calibration
framework before authoring profiles." This is that framework. It does not pick
parameters for you — it produces the numbers a human uses to pick one stage to
retune next, per the same section's "tune one stage at a time."

**On registration — read this before trusting any metric here.** A rendered
image and a reference photograph of nominally "the same scene" are two
different photographs: different camera position, framing, focal length,
moment, sometimes different scenes entirely (the reference is real, the
render's source is whatever phone shot you fed in). They will never line up
pixel-for-pixel, and forcing them to with a homography or optical-flow warp
would introduce its own interpolation blur and edge artefacts — exactly the
kind of softness this module is trying to measure, now contaminated by the
registration step itself. So this module never diffs pixels. Every metric
below is a *distributional* comparison — histograms, percentiles, per-channel
moments, and spatially-binned statistics (luminance bands for noise, radial
rings for sharpness) computed independently on each image and then compared as
summary numbers. That is weaker evidence than a registered pixel diff would
be, but it is honest about what it is: a `Param` backed by numbers from this
module should carry `Confidence.REFERENCE_CALIBRATED`, never `MEASURED`.

Both images are resampled to the same analysis width before anything is
computed. Without that, a higher-resolution source trivially reports sharper
edges and finer-grained noise than a lower-resolution one, which has nothing
to do with either camera's actual optics or sensor and everything to do with
how many pixels a Laplacian gets to work with.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from scipy.ndimage import gaussian_filter, laplace

from . import ops
from .optics import _radial_grid

_EPS = 1e-6

# Luminance bands used for both the noise estimate and (implicitly) the
# black-point/highlight-clip framing. Shared here so every metric group draws
# the same shadow/midtone/highlight line.
SHADOW_MAX = 0.33
HIGHLIGHT_MIN = 0.66

# What counts as "clipped" on a float32-normalised [0, 1] image decoded from an
# 8-bit source. 0.995 rather than exactly 1.0 because JPEG/PNG decode and the
# sRGB round-trip can leave a fully clipped channel a fraction under 255/255.
CLIP_THRESHOLD = 0.995

RADIAL_BINS = 4  # ring 0 = centre, ring -1 = corners


def load_rgb(path: Path, width: int | None = None) -> np.ndarray:
    """Load a photograph as float32 sRGB in [0, 1], optionally resized to `width`.

    Resizing is Lanczos, matching `__main__._load_image`, so a look rendered
    for review and a photo loaded for calibration go through the same filter.
    """
    from PIL import Image

    img = Image.open(path).convert("RGB")
    if width and img.width != width:
        h = max(int(round(img.height * width / img.width)), 1)
        img = img.resize((width, h), Image.LANCZOS)
    return (np.asarray(img, dtype=np.float32) / 255.0).astype(np.float32)


# ---------------------------------------------------------------------------
# Per-image metric groups. Each takes one image and returns plain floats;
# `compare()` runs each group on both images and pairs the results up.
# ---------------------------------------------------------------------------


def exposure_stats(rgb: np.ndarray) -> dict[str, float]:
    """Mean and median luminance. The first two numbers to check, because
    every other comparison is easier to read once you know whether the render
    is simply brighter or darker than the reference."""
    lum = ops.luma(rgb)
    return {"mean_luma": float(lum.mean()), "median_luma": float(np.median(lum))}


def white_balance_stats(rgb: np.ndarray) -> dict[str, float]:
    """Per-channel ratios against green, measured over the image's own
    midtones (gray-world assumption restricted to [0.2, 0.8] luma).

    This is not a registered gray-card read — there is no guarantee either
    photo contains a neutral patch — so treat the ratio as "this image's
    average colour cast relative to a scene-average grey", comparable between
    two images of *similar* content even though it is not a measurement of
    either camera's absolute white balance.
    """
    lum = ops.luma(rgb)
    mask = (lum > 0.2) & (lum < 0.8)
    if not mask.any():
        mask = np.ones_like(lum, dtype=bool)
    r = float(rgb[..., 0][mask].mean())
    g = float(rgb[..., 1][mask].mean())
    b = float(rgb[..., 2][mask].mean())
    return {
        "r_mean": r,
        "g_mean": g,
        "b_mean": b,
        "r_over_g": r / max(g, _EPS),
        "b_over_g": b / max(g, _EPS),
    }


def tone_stats(rgb: np.ndarray) -> dict[str, float]:
    """Black point and highlight-clipping behaviour.

    `black_point_p1` is the 1st percentile of luminance, a registration-free
    stand-in for "how far off true black do the darkest tones sit" (section 4:
    historical cameras lose shadow detail rather than rendering a clean 0).
    Highlight clipping is reported two ways because they diverge in practice:
    `highlight_clip_luma_pct` (luma itself pinned) undercounts colour-channel
    clipping, so `highlight_clip_any_channel_pct` (at least one channel
    pinned) is usually the more honest "this looks blown out" number,
    especially for saturated highlights like a red jacket in direct sun.
    """
    lum = ops.luma(rgb)
    max_channel = rgb.max(axis=-1)
    return {
        "black_point_p1": float(np.percentile(lum, 1.0)),
        "black_point_p5": float(np.percentile(lum, 5.0)),
        "white_point_p99": float(np.percentile(lum, 99.0)),
        "highlight_clip_luma_pct": float((lum >= CLIP_THRESHOLD).mean() * 100.0),
        "highlight_clip_any_channel_pct": float((max_channel >= CLIP_THRESHOLD).mean() * 100.0),
    }


def contrast_stats(rgb: np.ndarray) -> dict[str, float]:
    """Midtone contrast: spread of luminance within the midtone band, plus the
    overall inter-quartile range as a whole-image contrast proxy. Section 4
    tone modelling (shoulder, shadow lift) shows up here as a *compressed*
    midtone std relative to the reference, not as a hue shift."""
    lum = ops.luma(rgb)
    mid_mask = (lum > SHADOW_MAX) & (lum < HIGHLIGHT_MIN)
    mid_std = float(lum[mid_mask].std()) if mid_mask.any() else 0.0
    p25, p75 = np.percentile(lum, [25.0, 75.0])
    return {"midtone_std": mid_std, "iqr": float(p75 - p25)}


def saturation_stats(rgb: np.ndarray) -> dict[str, float]:
    """Mean/median HSV-style saturation `(max-min)/max`, excluding near-black
    pixels where saturation is numerically unstable and semantically
    meaningless (a JPEG-noise-dark pixel is not "highly saturated black")."""
    mx = rgb.max(axis=-1)
    mn = rgb.min(axis=-1)
    valid = mx > 0.05
    sat = np.zeros_like(mx)
    sat[valid] = (mx[valid] - mn[valid]) / mx[valid]
    vals = sat[valid] if valid.any() else sat
    return {"mean_saturation": float(vals.mean()), "median_saturation": float(np.median(vals))}


def noise_stats(rgb: np.ndarray) -> dict[str, float]:
    """Per-region noise estimate: shadows vs midtones vs highlights.

    No registration is needed here at all, which is the one metric group
    where that is true by construction: "noise" is estimated as the
    high-frequency residual against a locally blurred copy of the *same*
    image (`rgb - gaussian_filter(rgb, sigma=1)`), then that residual's
    standard deviation is binned by the image's own luminance. Two images
    never need to line up because each is only ever compared against a
    blurred version of itself. Binning by region matters because sensor and
    film noise are genuinely more visible in shadows than in highlights
    (section 4) — a single whole-image noise number would hide exactly the
    thing a NoiseProfile's `shadow_visibility_boost` is meant to capture.
    """
    lum = ops.luma(rgb)
    residual = rgb - gaussian_filter(rgb, sigma=(1.0, 1.0, 0.0))
    residual_mag = np.sqrt((residual**2).mean(axis=-1))  # per-pixel, channel-averaged

    bands = {
        "shadow": lum < SHADOW_MAX,
        "midtone": (lum >= SHADOW_MAX) & (lum < HIGHLIGHT_MIN),
        "highlight": lum >= HIGHLIGHT_MIN,
    }
    out: dict[str, float] = {}
    for name, mask in bands.items():
        out[f"{name}_noise_std"] = float(residual_mag[mask].std()) if mask.any() else float("nan")
    return out


def sharpness_profile(rgb: np.ndarray, bins: int = RADIAL_BINS) -> np.ndarray:
    """Edge sharpness in `bins` concentric rings from image centre (ring 0) to
    corners (ring `bins - 1`), via variance-of-Laplacian — the standard
    registration-free sharpness proxy, computed per ring rather than per pixel
    so it stays a distributional (not positional) comparison.

    Reuses `optics._radial_grid`'s exact radius convention (0 at centre, 1.0
    at the corners, aspect-corrected) so a falloff measured here lines up
    directly with `LensProfile.edge_softness` and `LensProfile.vignette_*`,
    which are defined against the same grid.
    """
    lum = ops.luma(rgb).astype(np.float64)
    lap = laplace(lum)
    _, _, r = _radial_grid(*lum.shape[:2])
    edges = np.linspace(0.0, 1.0, bins + 1)
    profile = np.zeros(bins, dtype=np.float64)
    for i in range(bins):
        mask = (r >= edges[i]) & (r < edges[i + 1] if i < bins - 1 else r <= edges[i + 1])
        profile[i] = lap[mask].var() if mask.any() else float("nan")
    return profile


def sharpness_stats(rgb: np.ndarray) -> dict[str, float]:
    profile = sharpness_profile(rgb)
    out = {f"ring{i}_variance": float(v) for i, v in enumerate(profile)}
    out["center_variance"] = float(profile[0])
    out["corner_variance"] = float(profile[-1])
    # >1 means the centre is sharper than the corners, as a real lens should be.
    out["center_over_corner"] = float(profile[0] / profile[-1]) if profile[-1] > _EPS else float("nan")
    return out


METRIC_GROUPS: dict[str, Any] = {
    "exposure": exposure_stats,
    "white_balance": white_balance_stats,
    "tone (black point / highlight clip)": tone_stats,
    "midtone_contrast": contrast_stats,
    "saturation": saturation_stats,
    "noise_by_region": noise_stats,
    "edge_sharpness": sharpness_stats,
}


def compare(rendered: np.ndarray, reference: np.ndarray) -> dict[str, dict[str, tuple[float, float]]]:
    """Run every metric group on both images and pair the results up.

    Returns `{stage_name: {metric_name: (rendered_value, reference_value)}}`,
    grouped by the pipeline stage each metric traces back to in CLAUDE.md
    section 4, so the report can be read and acted on one stage at a time
    (section 7, rule 3).
    """
    result: dict[str, dict[str, tuple[float, float]]] = {}
    for stage, fn in METRIC_GROUPS.items():
        r_vals = fn(rendered)
        f_vals = fn(reference)
        result[stage] = {k: (r_vals[k], f_vals[k]) for k in r_vals}
    return result


def format_report(comparison: dict[str, dict[str, tuple[float, float]]], name_a: str = "rendered", name_b: str = "reference") -> str:
    """Render `compare()`'s output as an aligned, per-stage text report."""
    lines = [
        "Distributional comparison only — see module docstring: no pixel registration is",
        "attempted, every number below is a histogram/percentile/moment summary.",
        "",
        f"{'metric':<32} {name_a:>14} {name_b:>14} {'delta':>14}",
    ]
    for stage, metrics in comparison.items():
        lines.append("")
        lines.append(f"-- {stage} " + "-" * max(1, 60 - len(stage)))
        for metric, (r_val, f_val) in metrics.items():
            delta = r_val - f_val if np.isfinite(r_val) and np.isfinite(f_val) else float("nan")
            lines.append(f"{metric:<32} {r_val:>14.4f} {f_val:>14.4f} {delta:>+14.4f}")
    return "\n".join(lines)


def run(rendered_path: Path, reference_path: Path, width: int = 1024) -> str:
    """Load both images at a shared analysis width and return the text report.

    This is what `__main__.cmd_calibrate` calls; it is also the entry point
    for using this module directly (e.g. from a notebook) without going
    through argparse.
    """
    rendered = load_rgb(rendered_path, width)
    reference = load_rgb(reference_path, width)
    return format_report(compare(rendered, reference))
