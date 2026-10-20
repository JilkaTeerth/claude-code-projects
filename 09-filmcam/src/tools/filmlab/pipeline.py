"""The full render pipeline, in numpy.

This mirrors the stage order the Swift `buildGraph()` implements, and exists for
two reasons:

  1. **Design surface.** Look authoring happens here, on the Mac, in seconds.
     Ninety percent of the question "does this colour relationship work" is
     answerable without a phone, which matters a lot when the device loop costs
     a rebuild on a 7-day certificate.
  2. **Oracle.** Render the same source through this and through the Swift graph
     and compare stage by stage. Exact numeric agreement with a GPU will never
     happen and should not be chased, but an order-of-magnitude divergence
     points straight at the broken stage.

Stage order, matching the plan:

    0  input normalize      → linear
    1  exposure / balance   (folded into the grade/LUT)
    2  halation             linear light, multi-scale, downsampled
    3  tone response        (folded into the grade/LUT)
    4  colour LUT
    5  grain                density weighted
    6  optics               vignette
    7  light leak           (not yet implemented here)
    8  date stamp           (not yet implemented here)

Halation runs *before* the LUT because scatter physically happens at exposure
time, so the look's grade pushes the halation too and it reads integrated
rather than pasted on. Grain runs *after* the LUT so it stays independently
tunable instead of being crushed by whatever range the look compresses.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter, zoom

from . import lut as lut_mod
from . import ops
from . import optics
from .looks import Look

NOISE_TILE = 512


def _smoothstep(edge0: float, edge1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - edge0) / max(edge1 - edge0, 1e-6), 0.0, 1.0)
    return (t * t * (3.0 - 2.0 * t)).astype(np.float32)


def make_noise_tile(
    size: int = NOISE_TILE,
    seed: int = 20260918,
    beta: float = 1.0,
    cross_correlation: float = 0.45,
) -> np.ndarray:
    """A tileable, zero-mean RGB noise tile with a *pink* power spectrum.

    Three properties separate real film grain from the Gaussian noise that most
    "film filter" apps ship, and a plain `rng.normal` gets all three wrong:

    **Pink spectrum, not white.** Measured film grain has a power spectral
    density close to 1/f. White noise (or white noise blurred by a Gaussian,
    which is what the first version of this function did) has the wrong falloff:
    too little low-frequency energy, so it reads as fine electronic hash rather
    than as clumped silver. Shaping in the frequency domain fixes this directly,
    and an FFT-built tile is exactly periodic, so it tiles for free.

    **Cross-channel correlation.** The intuition that colour film has three
    independently developing dye layers, so grain should be fully decorrelated
    per channel, is wrong in practice. Measured film grain shows *strong* cross
    colour correlation, because a clump occupies overlapping volume across the
    layers and scanning integrates through all of them. Fully decorrelated noise
    reads as chroma speckle, which is a digital artefact. `cross_correlation`
    mixes a shared component into all three channels.

    **Zero mean.** Non-zero-mean grain shifts average exposure, so every look
    would mysteriously brighten as grain increases.
    """
    rng = np.random.default_rng(seed)

    # Frequency-domain shaping. Build the radial frequency magnitude once.
    fy = np.fft.fftfreq(size)[:, None]
    fx = np.fft.fftfreq(size)[None, :]
    radius = np.sqrt(fy**2 + fx**2)
    radius[0, 0] = 1.0 / size  # avoid a divide-by-zero at DC
    shaping = radius ** (-beta / 2.0)
    shaping[0, 0] = 0.0  # kill DC so the tile is exactly zero-mean

    def pink_plane() -> np.ndarray:
        spectrum = np.fft.fft2(rng.normal(0.0, 1.0, (size, size)))
        return np.real(np.fft.ifft2(spectrum * shaping)).astype(np.float32)

    shared = pink_plane()
    planes = [pink_plane() for _ in range(3)]

    c = float(np.clip(cross_correlation, 0.0, 1.0))
    tile = np.stack([shared * c + p * (1.0 - c) for p in planes], axis=-1)

    tile -= tile.mean(axis=(0, 1), keepdims=True)
    tile /= tile.std(axis=(0, 1), keepdims=True) + 1e-6
    return tile.astype(np.float32)


def halation(rgb_linear: np.ndarray, params, width: int) -> np.ndarray:
    """Multi-scale red-orange bleed off blown highlights, in linear light.

    Multi-scale, not a single Gaussian: real halation is a tight hot core with a
    long low-amplitude tail. One Gaussian gives a soft donut that reads as cheap
    bloom. Each scale is blurred on a progressively smaller downsample, which is
    both faster and visually indistinguishable at these radii, and on device it
    is the single biggest thermal lever in the pipeline.
    """
    if params.strength <= 0.0:
        return rgb_linear

    lum = ops.luma(rgb_linear)
    mask = _smoothstep(params.threshold, params.threshold + params.softness, lum)
    tint = np.asarray(params.tint, dtype=np.float32)
    seed = rgb_linear * mask[..., None] * tint

    base_radius = params.radius_pct * width
    glow = np.zeros_like(seed)
    for scale, weight in zip(params.scales, params.weights):
        sigma = max(base_radius * scale / 3.0, 0.5)
        # Downsample proportionally to the blur width; a wide blur on a small
        # image is nearly free and upsamples back indistinguishably.
        factor = float(np.clip(1.0 / max(scale, 1.0), 0.12, 1.0))
        if factor < 0.99:
            small = zoom(seed, (factor, factor, 1.0), order=1)
            blurred = gaussian_filter(small, sigma=(sigma * factor, sigma * factor, 0.0))
            up = zoom(blurred, (seed.shape[0] / small.shape[0], seed.shape[1] / small.shape[1], 1.0), order=1)
            up = up[: seed.shape[0], : seed.shape[1]]
            if up.shape[:2] != seed.shape[:2]:
                pad = [(0, seed.shape[0] - up.shape[0]), (0, seed.shape[1] - up.shape[1]), (0, 0)]
                up = np.pad(up, pad, mode="edge")
            blurred = up
        else:
            blurred = gaussian_filter(seed, sigma=(sigma, sigma, 0.0))
        glow += blurred * weight

    # Additive in linear is the physically sensible composite, and is close to a
    # screen blend once it is back in display-referred space.
    return (rgb_linear + glow * params.strength).astype(np.float32)


def grain(rgb: np.ndarray, params, width: int, tile: np.ndarray | None = None, seed: int = 0) -> np.ndarray:
    """Density-weighted grain, applied after the LUT in display-referred space.

    The Gaussian weight in luminance is the point: grain peaks in the midtones
    and falls off toward both the toe and the shoulder. `shadow_floor` keeps
    blacks from going suspiciously clean, which is a giveaway that a "film"
    filter is fake.
    """
    if params.amount <= 0.0:
        return rgb

    if tile is None:
        tile = make_noise_tile(seed=20260918 + seed)

    h, w = rgb.shape[:2]
    # Grain cell size is stored at a 1000px reference width and scaled, so the
    # apparent grain is identical at preview and capture resolution. This is the
    # numpy equivalent of the parity invariant the Swift kernel enforces.
    base_cell = max(params.size_px1000 * width / 1000.0, 1.0)

    # Multi-scale. A real emulsion is a distribution of particle sizes, not one
    # uniform cell, so a single sampling scale reads as a regular texture. Two
    # octaves an octave apart, weighted toward the finer one, is enough to break
    # up the regularity without costing much.
    octaves = int(getattr(params, "octaves", 2))
    weights = [1.0, 0.55, 0.30][:octaves]
    total = sum(weights)

    n = np.zeros((h, w, 3), dtype=np.float32)
    for k, ow in enumerate(weights):
        cell = max(base_cell * (2.0**k), 1.0)
        ys = ((np.arange(h, dtype=np.float32) + k * 137.0) / cell) % tile.shape[0]
        xs = ((np.arange(w, dtype=np.float32) + k * 71.0) / cell) % tile.shape[1]
        n += tile[ys.astype(np.int32)[:, None], xs.astype(np.int32)[None, :]] * ow
    n /= total

    lum = ops.luma(rgb)
    weight = np.exp(-((lum - params.mu) ** 2) / (2.0 * params.sigma**2))
    weight = np.maximum(weight, params.shadow_floor)[..., None].astype(np.float32)

    mono = n.mean(axis=-1, keepdims=True)
    mixed = mono * (1.0 - params.chroma) + n * params.chroma
    return (rgb + mixed * weight * params.amount).astype(np.float32)


def vignette(rgb: np.ndarray, params) -> np.ndarray:
    """Radial falloff. Darkens corners, which reads as a lens rather than a filter."""
    if params.amount <= 0.0:
        return rgb
    h, w = rgb.shape[:2]
    yy = (np.linspace(-1.0, 1.0, h, dtype=np.float32))[:, None]
    xx = (np.linspace(-1.0, 1.0, w, dtype=np.float32))[None, :]
    # roundness 1.0 tracks the frame aspect; higher pushes toward a circle
    aspect = w / max(h, 1)
    d = np.sqrt((xx * aspect * params.roundness) ** 2 + yy**2) / max(aspect, 1e-6)
    falloff = 1.0 - _smoothstep(params.radius, params.radius + params.softness, d) * params.amount
    return (rgb * falloff[..., None]).astype(np.float32)


def render(
    rgb: np.ndarray,
    look: Look,
    cube: np.ndarray | None = None,
    tile: np.ndarray | None = None,
    grain_on: bool = True,
    stamp_text: str = "'26 9 18",
) -> np.ndarray:
    """Run a display-referred sRGB image through the full pipeline for one look.

    `grain_on=False` is what the parity test uses, since grain is stochastic and
    will never match pixel-for-pixel between two implementations.
    """
    x = np.clip(np.asarray(rgb, dtype=np.float32), 0.0, 1.0)
    width = x.shape[1]

    # Stage 2: halation, in linear light, before the grade.
    lin = ops.srgb_to_linear(x)
    lin = halation(lin, look.halation, width)
    x = np.clip(ops.linear_to_srgb(lin), 0.0, 1.0)

    # Stages 1/3/4: exposure, balance, curve and colour, all carried by the LUT.
    if cube is None:
        cube = lut_mod.build(look)
    x = lut_mod.apply_lut(x, cube)

    # Stage 5: grain.
    if grain_on:
        x = grain(x, look.grain, width, tile=tile)

    # Stage 6: optics. Aberration and softness are lens properties so they run
    # before the vignette, which is also the lens but is the last thing the
    # light passes through.
    opt = getattr(look, "optics", None)
    if opt is not None:
        x = optics.chromatic_aberration(x, opt.aberration)
        x = optics.lens_softness(x, opt.softness)
    x = vignette(x, look.vignette)

    # Stage 7: light leak, seeded so a re-render reproduces it exactly.
    lk = getattr(look, "leak", None)
    if lk is not None and lk.strength > 0.0:
        x = optics.light_leak(x, seed=lk.seed, strength=lk.strength, tint=lk.tint)

    # Stage 8: date stamp, additive with a glow because it is light exposing
    # the negative, not text drawn on top of a photo.
    st = getattr(look, "stamp", None)
    if st is not None and st.enabled and stamp_text:
        x = optics.date_stamp(
            x, text=stamp_text, corner=st.corner, size_pct=st.size_pct,
            tint=st.tint, glow=st.glow,
        )

    # Stage 9: the physical frame. Occludes rather than tints, so it goes last.
    frame = getattr(look, "frame", "none")
    if frame != "none":
        x = optics.film_border(x, frame)

    return np.clip(x, 0.0, 1.0).astype(np.float32)
