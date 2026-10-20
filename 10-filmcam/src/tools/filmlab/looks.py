"""The look library.

A look is a parameter set, not a baked image filter. Two halves:

  * the **grade** (exposure, balance, CDL, crosstalk, curve, split tone, ...)
    which is pure per-pixel colour and therefore bakes cleanly into a 3D LUT;
  * the **spatial** parameters (halation, grain, vignette) which depend on
    neighbouring pixels or on image resolution and so cannot live in a LUT.
    These are carried in `looks.json` and executed by the render graph.

Every value here is ours. Nothing is sampled, traced, or reverse-engineered
from any commercial LUT pack or from any shipping app. Where a look is described
as behaving like a class of film stock, that refers to documented photochemical
behaviour (shadow response, grain structure, highlight rolloff), not to any
stock's trademarked identity.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

import numpy as np

from . import ops


@dataclass
class Halation:
    """Red-orange bleed off blown highlights. Applied in linear light, pre-curve."""

    strength: float = 0.0
    threshold: float = 0.78
    softness: float = 0.12
    tint: tuple[float, float, float] = (1.00, 0.30, 0.12)
    radius_pct: float = 0.012
    scales: tuple[float, float, float] = (1.0, 3.0, 9.0)
    weights: tuple[float, float, float] = (0.50, 0.35, 0.15)


@dataclass
class Grain:
    """Density-weighted grain. Peaks in the midtones, never fully clean in black."""

    amount: float = 0.10
    size_px1000: float = 2.2
    mu: float = 0.45
    sigma: float = 0.28
    # Keep this small. The floor is relative to the *signal*, so on a near-black
    # field a floor of 0.12 makes the grain larger than the thing it sits on and
    # the shadows visibly boil. 0.05 keeps blacks from being suspiciously clean
    # without turning them into noise.
    shadow_floor: float = 0.05
    # How much of the noise is shared across R/G/B vs per-channel. Measured film
    # grain has *strong* cross-channel correlation, so this stays low; fully
    # decorrelated noise reads as digital chroma speckle.
    chroma: float = 0.30
    # Sampling octaves. A real emulsion is a distribution of particle sizes, so
    # one uniform cell reads as a regular texture. 2 breaks it up cheaply.
    octaves: int = 2


@dataclass
class Vignette:
    amount: float = 0.0
    radius: float = 0.78
    softness: float = 0.45
    roundness: float = 1.0


@dataclass
class Optics:
    """The lens. Cheap glass is a huge part of why a toy camera looks like one."""

    aberration: float = 0.0  # lateral CA, fringing that grows toward the corners
    softness: float = 0.0  # corner mush


@dataclass
class Leak:
    """Seeded light leak. Stores a seed, never a baked texture, so a re-render
    months later reproduces the identical leak."""

    strength: float = 0.0
    seed: int = 0
    tint: tuple[float, float, float] = (1.0, 0.42, 0.14)


@dataclass
class Stamp:
    """The orange seven-segment date burn."""

    enabled: bool = False
    size_pct: float = 0.035
    corner: str = "bottomRight"
    tint: tuple[float, float, float] = (1.0, 0.36, 0.06)
    glow: float = 1.0


@dataclass
class Look:
    id: str
    name: str
    family: str
    version: int = 1

    # --- grade: baked into the LUT -----------------------------------------
    exposure_ev: float = 0.0
    temp: float = 0.0
    tint: float = 0.0

    cdl_slope: tuple[float, float, float] = (1.0, 1.0, 1.0)
    cdl_offset: tuple[float, float, float] = (0.0, 0.0, 0.0)
    cdl_power: tuple[float, float, float] = (1.0, 1.0, 1.0)

    crosstalk: float = 0.0
    crosstalk_bias: tuple[float, float, float] | None = None

    black_point: float = 0.0
    white_point: float = 1.0
    toe_lift: float = 0.0
    shoulder: float = 0.0
    contrast: float = 1.0

    curve_r: list[tuple[float, float]] | None = None
    curve_g: list[tuple[float, float]] | None = None
    curve_b: list[tuple[float, float]] | None = None

    saturation: float = 1.0
    split_shadow: tuple[float, float, float] = (0.0, 0.0, 0.0)
    split_highlight: tuple[float, float, float] = (0.0, 0.0, 0.0)
    split_balance: float = 0.5
    split_strength: float = 0.0
    rolloff: float = 0.0

    mono_weights: tuple[float, float, float] | None = None
    mono_tone: tuple[float, float, float] = (0.0, 0.0, 0.0)

    # --- the camera body: optics, frame, artifacts --------------------------
    # A camera is not a colour grade. The teardown's central finding is that
    # this category sells cameras, not filters, and a camera bundles a lens, a
    # frame, a focal length and its own artifacts along with the look.
    focal: int = 26  # shown on the capture UI, and the default crop
    frame: str = "none"  # none | sprocket | instant

    # --- spatial: executed by the render graph, never baked ----------------
    halation: Halation = field(default_factory=Halation)
    grain: Grain = field(default_factory=Grain)
    vignette: Vignette = field(default_factory=Vignette)
    optics: Optics = field(default_factory=Optics)
    leak: Leak = field(default_factory=Leak)
    stamp: Stamp = field(default_factory=Stamp)

    def grade(self, rgb: np.ndarray) -> np.ndarray:
        """Run the colour half of the look. This is what gets baked into the LUT."""
        x = np.asarray(rgb, dtype=np.float32)
        x = ops.exposure(x, self.exposure_ev)
        x = ops.temperature_tint(x, self.temp, self.tint)
        x = ops.asc_cdl(x, self.cdl_slope, self.cdl_offset, self.cdl_power)
        x = ops.crosstalk(x, self.crosstalk, self.crosstalk_bias)
        x = ops.tone_curve(
            x,
            black_point=self.black_point,
            white_point=self.white_point,
            toe_lift=self.toe_lift,
            shoulder=self.shoulder,
            contrast=self.contrast,
        )
        x = ops.channel_curves(x, self.curve_r, self.curve_g, self.curve_b)
        x = ops.saturation(x, self.saturation)
        x = ops.split_tone(
            x,
            self.split_shadow,
            self.split_highlight,
            self.split_balance,
            self.split_strength,
        )
        x = ops.highlight_rolloff(x, self.rolloff)
        if self.mono_weights is not None:
            x = ops.monochrome(x, self.mono_weights, self.mono_tone)
        return np.clip(x, 0.0, 1.0).astype(np.float32)

    def to_json(self) -> dict[str, Any]:
        """Serialise the spatial half plus identity. The grade lives in the LUT."""
        return {
            "id": self.id,
            "name": self.name,
            "family": self.family,
            "version": self.version,
            "focal": self.focal,
            "frame": self.frame,
            "halation": asdict(self.halation),
            "grain": asdict(self.grain),
            "vignette": asdict(self.vignette),
            "optics": asdict(self.optics),
            "leak": asdict(self.leak),
            "stamp": asdict(self.stamp),
        }


# ---------------------------------------------------------------------------
# Family 1 — warm daylight negative
# Warm cast, lifted and slightly muddy shadows, compressed shadow detail,
# forgiving on skin. The "nostalgic snapshot" register.
# ---------------------------------------------------------------------------

SUNDECK = Look(
    id="sundeck", name="Sundeck", family="warm-negative",
    temp=0.045, tint=-0.010,
    cdl_slope=(1.03, 1.00, 0.96), cdl_offset=(0.012, 0.006, 0.000), cdl_power=(0.98, 1.00, 1.03),
    crosstalk=0.055, crosstalk_bias=(1.2, 1.0, 0.8),
    toe_lift=0.035, shoulder=0.18, contrast=1.08,
    saturation=1.06,
    split_shadow=(0.012, 0.004, -0.008), split_highlight=(0.020, 0.010, -0.006),
    split_strength=0.9, rolloff=0.35,
    halation=Halation(strength=0.35, threshold=0.78, radius_pct=0.012),
    grain=Grain(amount=0.036, size_px1000=2.2),
    vignette=Vignette(amount=0.22),
)

TERRACOTTA = Look(
    id="terracotta", name="Terracotta", family="warm-negative",
    temp=0.075, tint=0.015,
    cdl_slope=(1.05, 0.99, 0.92), cdl_offset=(0.018, 0.008, 0.002), cdl_power=(0.96, 1.00, 1.06),
    crosstalk=0.070, crosstalk_bias=(1.4, 1.0, 0.7),
    toe_lift=0.055, shoulder=0.22, contrast=1.02,
    saturation=0.98,
    split_shadow=(0.020, 0.006, -0.012), split_highlight=(0.026, 0.012, -0.010),
    split_strength=1.0, rolloff=0.45,
    halation=Halation(strength=0.45, threshold=0.74, radius_pct=0.014),
    grain=Grain(amount=0.042, size_px1000=2.6),
    vignette=Vignette(amount=0.30),
)

HONEYLINE = Look(
    id="honeyline", name="Honeyline", family="warm-negative",
    temp=0.030,
    cdl_slope=(1.01, 1.00, 0.98), cdl_offset=(0.006, 0.004, 0.002),
    crosstalk=0.035,
    toe_lift=0.018, shoulder=0.26, contrast=0.96,
    saturation=1.00,
    split_highlight=(0.016, 0.010, 0.000), split_strength=0.8, rolloff=0.55,
    halation=Halation(strength=0.22, threshold=0.82, radius_pct=0.010),
    grain=Grain(amount=0.024, size_px1000=1.8, sigma=0.24),
    vignette=Vignette(amount=0.12),
)

# ---------------------------------------------------------------------------
# Family 2 — cool consumer negative
# Cool shadows, green bias through the midtones, coarser grain structure.
# The "cheap 400-speed film in overcast light" register.
# ---------------------------------------------------------------------------

COLDSTORE = Look(
    id="coldstore", name="Coldstore", family="cool-negative",
    temp=-0.045, tint=-0.030,
    cdl_slope=(0.96, 1.02, 1.05), cdl_offset=(0.004, 0.010, 0.014), cdl_power=(1.04, 1.00, 0.97),
    crosstalk=0.060, crosstalk_bias=(0.8, 1.3, 1.0),
    toe_lift=0.030, shoulder=0.14, contrast=1.10,
    saturation=0.94,
    split_shadow=(-0.014, 0.004, 0.020), split_highlight=(0.006, 0.010, 0.004),
    split_strength=1.0, rolloff=0.25,
    halation=Halation(strength=0.18, threshold=0.84, tint=(1.0, 0.45, 0.30)),
    grain=Grain(amount=0.048, size_px1000=2.9, sigma=0.30, chroma=0.36),
    vignette=Vignette(amount=0.26),
)

NIGHTBUS = Look(
    id="nightbus", name="Nightbus", family="cool-negative",
    exposure_ev=-0.15, temp=-0.060, tint=-0.015,
    cdl_slope=(0.94, 1.00, 1.08), cdl_offset=(0.020, 0.018, 0.026), cdl_power=(1.06, 1.02, 0.94),
    crosstalk=0.080, crosstalk_bias=(0.7, 1.1, 1.4),
    toe_lift=0.070, shoulder=0.10, contrast=1.18,
    saturation=0.88,
    split_shadow=(-0.020, 0.000, 0.034), split_highlight=(0.014, 0.008, -0.004),
    split_strength=1.0, rolloff=0.20,
    halation=Halation(strength=0.55, threshold=0.68, radius_pct=0.018, tint=(1.0, 0.34, 0.18)),
    grain=Grain(amount=0.060, size_px1000=3.4, mu=0.38, sigma=0.32, shadow_floor=0.07, chroma=0.40),
    vignette=Vignette(amount=0.38, radius=0.70),
)

MUNICIPAL = Look(
    id="municipal", name="Municipal", family="cool-negative",
    temp=-0.025, tint=-0.045,
    cdl_slope=(0.97, 1.03, 1.00), cdl_offset=(0.008, 0.012, 0.008),
    crosstalk=0.050, crosstalk_bias=(0.9, 1.4, 0.9),
    toe_lift=0.026, shoulder=0.16, contrast=1.04,
    saturation=0.90,
    split_shadow=(-0.008, 0.012, 0.010), split_strength=0.9, rolloff=0.30,
    halation=Halation(strength=0.15, threshold=0.86),
    grain=Grain(amount=0.045, size_px1000=2.7),
    vignette=Vignette(amount=0.20),
)

# ---------------------------------------------------------------------------
# Family 3 — punchy reversal / slide
# High saturation, high contrast, very fine grain, unforgiving on skin.
# Slide film had no printing stage to rescue it, so what you shot is what you got.
# ---------------------------------------------------------------------------

POSTCARD = Look(
    id="postcard", name="Postcard", family="reversal",
    cdl_slope=(1.04, 1.02, 1.02), cdl_offset=(-0.006, -0.004, -0.004), cdl_power=(1.00, 1.00, 0.99),
    crosstalk=0.020,
    black_point=0.006, toe_lift=0.0, shoulder=0.08, contrast=1.30,
    saturation=1.28,
    split_highlight=(0.004, 0.008, 0.010), split_strength=0.5, rolloff=0.15,
    halation=Halation(strength=0.12, threshold=0.88, radius_pct=0.008),
    grain=Grain(amount=0.015, size_px1000=1.5, sigma=0.22, shadow_floor=0.06),
    vignette=Vignette(amount=0.16),
)

RALLY = Look(
    id="rally", name="Rally", family="reversal",
    temp=0.020,
    cdl_slope=(1.07, 1.01, 0.99), cdl_offset=(-0.010, -0.006, -0.002), cdl_power=(0.97, 1.00, 1.02),
    crosstalk=0.030, crosstalk_bias=(1.3, 1.0, 0.9),
    black_point=0.010, shoulder=0.06, contrast=1.38,
    saturation=1.34,
    split_shadow=(0.006, -0.004, -0.010), split_highlight=(0.012, 0.006, -0.004),
    split_strength=0.8, rolloff=0.12,
    halation=Halation(strength=0.20, threshold=0.84, radius_pct=0.009),
    grain=Grain(amount=0.021, size_px1000=1.6, sigma=0.24, shadow_floor=0.08),
    vignette=Vignette(amount=0.24),
)

# ---------------------------------------------------------------------------
# Family 4 — muted pastel
# Heavily lifted blacks, low saturation, soft contrast. The modern "faded"
# register that reads as scanned-and-left-in-a-drawer.
# ---------------------------------------------------------------------------

LINEN = Look(
    id="linen", name="Linen", family="pastel",
    temp=0.015,
    cdl_slope=(0.96, 0.96, 0.95), cdl_offset=(0.030, 0.028, 0.026), cdl_power=(1.00, 1.00, 1.01),
    crosstalk=0.045,
    toe_lift=0.085, shoulder=0.30, contrast=0.84,
    saturation=0.80,
    split_shadow=(0.010, 0.008, 0.006), split_highlight=(0.014, 0.012, 0.008),
    split_strength=1.0, rolloff=0.60,
    halation=Halation(strength=0.16, threshold=0.80, radius_pct=0.013),
    grain=Grain(amount=0.030, size_px1000=2.0, sigma=0.30),
    vignette=Vignette(amount=0.08),
)

POWDER = Look(
    id="powder", name="Powder", family="pastel",
    temp=-0.015, tint=0.020,
    cdl_slope=(0.95, 0.95, 0.97), cdl_offset=(0.034, 0.032, 0.036),
    crosstalk=0.055,
    toe_lift=0.100, shoulder=0.34, contrast=0.78,
    saturation=0.74,
    split_shadow=(0.006, 0.004, 0.016), split_highlight=(0.018, 0.010, 0.014),
    split_strength=1.0, rolloff=0.65,
    halation=Halation(strength=0.14, threshold=0.80),
    grain=Grain(amount=0.027, size_px1000=2.1, sigma=0.32),
    vignette=Vignette(amount=0.06),
)

# ---------------------------------------------------------------------------
# Family 5 — black and white
# Channel weights matter more than anything else here: a red-heavy mix darkens
# skies and lightens skin, which is what makes a mono look deliberate rather
# than like a desaturation slider.
# ---------------------------------------------------------------------------

GRAPHITE = Look(
    id="graphite", name="Graphite", family="mono",
    contrast=1.16, toe_lift=0.020, shoulder=0.12,
    mono_weights=(0.30, 0.59, 0.11),
    halation=Halation(strength=0.18, threshold=0.82, tint=(1.0, 1.0, 1.0)),
    grain=Grain(amount=0.054, size_px1000=2.8, chroma=0.0, shadow_floor=0.06),
    vignette=Vignette(amount=0.24),
)

SELENIUM = Look(
    id="selenium", name="Selenium", family="mono",
    contrast=1.24, toe_lift=0.014, shoulder=0.10,
    mono_weights=(0.34, 0.54, 0.12), mono_tone=(-0.012, 0.000, 0.026),
    halation=Halation(strength=0.15, threshold=0.84, tint=(0.8, 0.9, 1.0)),
    grain=Grain(amount=0.048, size_px1000=2.5, chroma=0.0),
    vignette=Vignette(amount=0.28),
)

FOXGLOVE = Look(
    id="foxglove", name="Foxglove", family="mono",
    contrast=1.02, toe_lift=0.050, shoulder=0.24,
    mono_weights=(0.42, 0.50, 0.08), mono_tone=(0.040, 0.014, -0.020),
    rolloff=0.40,
    halation=Halation(strength=0.30, threshold=0.76, radius_pct=0.014),
    grain=Grain(amount=0.051, size_px1000=3.0, chroma=0.0, shadow_floor=0.07),
    vignette=Vignette(amount=0.34, radius=0.72),
)

# ---------------------------------------------------------------------------
# Family 6 — camera artefact looks
# Not film stocks. These model a *camera*, which is the other half of what the
# category actually sells: the disposable with the flash on, and the 2003 compact.
# ---------------------------------------------------------------------------

FLASHBULB = Look(
    id="flashbulb", name="Flashbulb", family="camera",
    exposure_ev=0.12, temp=0.020,
    cdl_slope=(1.06, 1.03, 1.00), cdl_offset=(0.014, 0.012, 0.010), cdl_power=(0.96, 0.98, 1.00),
    crosstalk=0.075, crosstalk_bias=(1.2, 1.0, 0.9),
    toe_lift=0.045, shoulder=0.08, contrast=1.22,
    saturation=1.10,
    split_shadow=(0.008, 0.000, -0.010), split_highlight=(0.014, 0.008, 0.000),
    split_strength=0.9, rolloff=0.30,
    focal=32, frame="none",
    halation=Halation(strength=0.65, threshold=0.66, radius_pct=0.020, weights=(0.42, 0.36, 0.22)),
    grain=Grain(amount=0.060, size_px1000=3.2, mu=0.42, shadow_floor=0.06),
    vignette=Vignette(amount=0.52, radius=0.62, softness=0.35),
    optics=Optics(aberration=0.0030, softness=0.55),
    leak=Leak(strength=0.38, seed=4417),
    stamp=Stamp(enabled=True),
)

COMPACT = Look(
    id="compact", name="Compact", family="camera",
    temp=-0.030, tint=0.010,
    cdl_slope=(1.00, 1.01, 1.04), cdl_offset=(0.006, 0.006, 0.010), cdl_power=(1.02, 1.00, 0.98),
    crosstalk=0.015,
    black_point=0.012, toe_lift=0.010, shoulder=0.04, contrast=1.26,
    saturation=1.16,
    split_shadow=(-0.010, 0.002, 0.014), split_strength=0.8, rolloff=0.10,
    focal=38, frame="none",
    halation=Halation(strength=0.10, threshold=0.90, radius_pct=0.006),
    grain=Grain(amount=0.018, size_px1000=1.4, sigma=0.20, shadow_floor=0.05, chroma=0.50),
    vignette=Vignette(amount=0.14, radius=0.84),
    optics=Optics(aberration=0.0016, softness=0.22),
    stamp=Stamp(enabled=True, size_pct=0.030),
)


FRAME135 = Look(
    id="frame135", name="Frame 135", family="camera",
    temp=0.020,
    cdl_slope=(1.02, 1.00, 0.97), cdl_offset=(0.010, 0.006, 0.002),
    crosstalk=0.060, crosstalk_bias=(1.2, 1.0, 0.85),
    toe_lift=0.030, shoulder=0.20, contrast=1.06,
    saturation=1.02,
    split_highlight=(0.016, 0.008, -0.004), split_strength=0.9, rolloff=0.40,
    focal=35, frame="sprocket",
    halation=Halation(strength=0.38, threshold=0.76, radius_pct=0.013),
    grain=Grain(amount=0.042, size_px1000=2.7),
    vignette=Vignette(amount=0.18),
    optics=Optics(aberration=0.0012, softness=0.20),
    leak=Leak(strength=0.20, seed=1350),
)

INSTANT = Look(
    id="instant", name="Instant", family="camera",
    temp=0.030, tint=0.020,
    cdl_slope=(1.02, 0.99, 0.97), cdl_offset=(0.036, 0.032, 0.030), cdl_power=(0.98, 1.00, 1.04),
    crosstalk=0.090, crosstalk_bias=(1.3, 1.0, 0.8),
    toe_lift=0.090, shoulder=0.30, contrast=0.88,
    saturation=0.86,
    split_shadow=(0.014, 0.006, 0.004), split_highlight=(0.022, 0.014, 0.000),
    split_strength=1.0, rolloff=0.60,
    focal=41, frame="instant",
    halation=Halation(strength=0.30, threshold=0.74, radius_pct=0.016),
    grain=Grain(amount=0.030, size_px1000=2.3, sigma=0.32),
    vignette=Vignette(amount=0.22, radius=0.74),
    optics=Optics(aberration=0.0022, softness=0.45),
    leak=Leak(strength=0.26, seed=6001),
)


ALL_LOOKS: list[Look] = [
    SUNDECK, TERRACOTTA, HONEYLINE,
    COLDSTORE, NIGHTBUS, MUNICIPAL,
    POSTCARD, RALLY,
    LINEN, POWDER,
    GRAPHITE, SELENIUM, FOXGLOVE,
    FLASHBULB, COMPACT, FRAME135, INSTANT,
]

BY_ID: dict[str, Look] = {lk.id: lk for lk in ALL_LOOKS}
