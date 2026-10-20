"""The v2 camera profile schema: `CameraProfile` and its sub-profiles.

Mirrors CLAUDE.md section 3 field-for-field. This module defines *data*, not
behaviour: no rendering, no defaults dialled in by eye. Authoring an actual
profile (picking numbers) is out of scope here on purpose — see section 7,
"the engine is worthless with invented parameters." What lives here is the
shape a calibrated profile will eventually fill in, plus the machinery that
makes it impossible to forget where a number came from.

Two ideas carry the whole module:

**Every numeric parameter is a `Param`, not a bare float.** A `Param` bundles
`value` with `confidence` (the five-case hierarchy from section 3) and an
optional `source` string pointing into `Sources/<Profile>.md`. A profile is
therefore not just numbers, it is a numbers-plus-evidence document. `validate()`
walks the whole tree and surfaces every parameter that is either an admitted
guess (`artisticApproximation`) or unsourced, so an impressively parametrised
but entirely invented camera cannot hide inside a passing `check`.

**A sub-profile field left as `None` means "not modelled", which is different
from "modelled badly."** CLAUDE.md section 3 is explicit that fake precision
is worse than an honest `unknown`. Every field on the leaf profiles below
(`SensorProfile`, `LensProfile`, ...) is therefore `Optional[Param] = None`:
leaving one out is a legitimate, inspectable statement that the calibration
harness has not produced a number for it yet, not a bug to paper over with a
guess. `validate()` only ever inspects `Param`s that are actually present.

Which optional sub-profile is attached to a `CameraProfile` selects which of
the three pipelines in CLAUDE.md section 2 runs: `film` present -> the film
chain, `instantFilm` present -> the instant chain, neither -> digital. See
`CameraProfile.family`.
"""

from __future__ import annotations

import json
import operator
from dataclasses import dataclass, fields as dc_fields, is_dataclass
from enum import Enum
from typing import Any, Iterator, Optional, Union, get_args, get_origin, get_type_hints

# ---------------------------------------------------------------------------
# Confidence and Param — the provenance system. Everything else in this module
# exists to be built out of these two things correctly.
# ---------------------------------------------------------------------------


class Confidence(str, Enum):
    """The five-case hierarchy from CLAUDE.md section 3, verbatim.

    Ordered strongest to weakest evidence for a *single parameter value* (this
    is not the same ordering as section 7's evidence hierarchy for *authoring
    a profile*, which ranks manufacturer docs above measurement because a
    manufacturer spec is authoritative for the whole product line while one
    measurement is one sample; the two hierarchies answer different questions
    and should not be conflated). `.rank` gives the ordering as an int so
    `Param` arithmetic and the validator can compare two confidences.
    """

    MEASURED = "measured"                             # we measured it
    MANUFACTURER_DOCUMENTED = "manufacturerDocumented" # primary source
    LITERATURE_BASED = "literatureBased"               # imaging science
    REFERENCE_CALIBRATED = "referenceCalibrated"       # tuned against references
    ARTISTIC_APPROXIMATION = "artisticApproximation"   # a choice, and labelled as one

    @property
    def rank(self) -> int:
        return _CONFIDENCE_RANK[self]


_CONFIDENCE_RANK = {
    Confidence.MEASURED: 0,
    Confidence.MANUFACTURER_DOCUMENTED: 1,
    Confidence.LITERATURE_BASED: 2,
    Confidence.REFERENCE_CALIBRATED: 3,
    Confidence.ARTISTIC_APPROXIMATION: 4,
}


def _weaker(a: Confidence, b: Confidence) -> Confidence:
    return a if a.rank >= b.rank else b


def _merge_sources(a: Optional[str], b: Optional[str]) -> Optional[str]:
    """Combine two source strings for a derived Param, de-duplicated, order preserved."""
    parts = [s for s in (a, b) if s]
    if not parts:
        return None
    seen: list[str] = []
    for p in parts:
        if p not in seen:
            seen.append(p)
    return " & ".join(seen)


@dataclass(frozen=True)
class Param:
    """A number that knows how sure we are of it and why.

    Bad, per CLAUDE.md section 3: `"sensorNoise": 0.037281` with no evidence.
    Good: `Param(0.037, Confidence.REFERENCE_CALIBRATED, "Sources/iPhone5.md#noise")`.

    Ergonomics: arithmetic (`+ - * / neg abs`, comparisons) works directly on
    `Param`, against either another `Param` or a plain number, so pipeline code
    that composes parameters (`profile.exposure.ev_compensation + lens_bias`)
    stays readable instead of unwrapping `.value` everywhere. A derived `Param`
    inherits the *weaker* of its inputs' confidences and the union of their
    sources — arithmetic never launders an `artisticApproximation` into
    something that looks `referenceCalibrated` just because it was added to a
    measured number.

    Unwrapping: `float(p)` or `p.value` for the common case of feeding a numpy
    pipeline (`ops.py`, ``pipeline.py``). Param is deliberately not numpy-aware
    (no `__array_priority__` dance) — mixing it into a numpy expression on
    purpose is a sign the value should have been unwrapped first, not that
    `Param` should grow broadcast semantics.
    """

    value: float
    confidence: Confidence
    source: Optional[str] = None

    def __float__(self) -> float:
        return float(self.value)

    def __repr__(self) -> str:
        src = self.source or "UNSOURCED"
        return f"Param({self.value:g}, {self.confidence.value}, {src})"

    @staticmethod
    def _value_of(other: Any) -> float:
        return other.value if isinstance(other, Param) else float(other)

    def _derived(self, value: float, other: Any) -> "Param":
        if isinstance(other, Param):
            return Param(value, _weaker(self.confidence, other.confidence), _merge_sources(self.source, other.source))
        return Param(value, self.confidence, self.source)

    def __add__(self, other: Any) -> "Param":
        return self._derived(operator.add(self.value, self._value_of(other)), other)

    def __radd__(self, other: Any) -> "Param":
        return self._derived(operator.add(self._value_of(other), self.value), other)

    def __sub__(self, other: Any) -> "Param":
        return self._derived(operator.sub(self.value, self._value_of(other)), other)

    def __rsub__(self, other: Any) -> "Param":
        return self._derived(operator.sub(self._value_of(other), self.value), other)

    def __mul__(self, other: Any) -> "Param":
        return self._derived(operator.mul(self.value, self._value_of(other)), other)

    def __rmul__(self, other: Any) -> "Param":
        return self._derived(operator.mul(self._value_of(other), self.value), other)

    def __truediv__(self, other: Any) -> "Param":
        return self._derived(operator.truediv(self.value, self._value_of(other)), other)

    def __rtruediv__(self, other: Any) -> "Param":
        return self._derived(operator.truediv(self._value_of(other), self.value), other)

    def __neg__(self) -> "Param":
        return Param(-self.value, self.confidence, self.source)

    def __pos__(self) -> "Param":
        return self

    def __abs__(self) -> "Param":
        return Param(abs(self.value), self.confidence, self.source)

    def __lt__(self, other: Any) -> bool:
        return self.value < self._value_of(other)

    def __le__(self, other: Any) -> bool:
        return self.value <= self._value_of(other)

    def __gt__(self, other: Any) -> bool:
        return self.value > self._value_of(other)

    def __ge__(self, other: Any) -> bool:
        return self.value >= self._value_of(other)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Param):
            return self.value == other.value
        if isinstance(other, (int, float)):
            return self.value == other
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.value, self.confidence, self.source))

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"value": self.value, "confidence": self.confidence.value}
        if self.source:
            d["source"] = self.source
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Param":
        return cls(value=float(data["value"]), confidence=Confidence(data["confidence"]), source=data.get("source"))


# ---------------------------------------------------------------------------
# Category and pipeline family
# ---------------------------------------------------------------------------


class CameraCategory(str, Enum):
    """`category: CameraCategory // digital | instant | film | disposable | phone`."""

    DIGITAL = "digital"
    INSTANT = "instant"
    FILM = "film"
    DISPOSABLE = "disposable"
    PHONE = "phone"


class PipelineFamily(str, Enum):
    """Which of the three render graphs in CLAUDE.md section 2 a profile runs.

    This is orthogonal to `CameraCategory`: category is what the *product* is
    (a disposable is still a physical camera you'd shop for), family is which
    *pipeline* processes it. A disposable loaded with print film is category
    `disposable`, family `film`. An instant camera is category `instant`,
    family `instantFilm`. Everything else with neither sub-profile attached is
    `digital`, regardless of category (`phone`, `disposable` with a digital
    sensor, etc.).
    """

    DIGITAL = "digital"
    FILM = "film"
    INSTANT_FILM = "instantFilm"


# ---------------------------------------------------------------------------
# Sub-profiles. Every numeric field is `Optional[Param]`: present means
# modelled-with-evidence, `None` means not modelled yet. See module docstring.
# ---------------------------------------------------------------------------


@dataclass
class SensorProfile:
    """Section 4, Sensor. Static sensor characteristics — the noise *model's*
    parameters live in `NoiseProfile`; this is dynamic range, response and
    clipping, i.e. what the sensor sees rather than what it adds."""

    dynamic_range_stops: Optional[Param] = None
    channel_sensitivity: tuple[Optional[Param], Optional[Param], Optional[Param]] = (None, None, None)  # R, G, B
    color_crosstalk: Optional[Param] = None       # inter-channel response bleed, distinct from noise
    highlight_clip: Optional[Param] = None        # display-referred level (0..1) where the sensor clips
    pixel_pitch_um: Optional[Param] = None        # physical pixel size; drives noise-per-generation comparisons


@dataclass
class LensProfile:
    """Section 4, Lens + Chromatic aberration + Vignette.

    CA is wavelength-dependent radial sampling, near zero at centre and
    growing with distance — never a uniform RGB offset, which reads as a
    glitch. Vignette is radial with strength/radius/falloff/asymmetry, never a
    flat black circle. `edge_softness` and `distortion_k*` are the other two
    things a cheap lens does that a colour grade cannot fake.
    """

    distortion_k1: Optional[Param] = None       # radial (barrel/pincushion) distortion, 1st order
    distortion_k2: Optional[Param] = None       # 2nd order term
    chromatic_aberration: Optional[Param] = None  # fractional radial offset between channels at the corner
    vignette_strength: Optional[Param] = None
    vignette_radius: Optional[Param] = None
    vignette_falloff: Optional[Param] = None
    vignette_asymmetry: Optional[Param] = None
    edge_softness: Optional[Param] = None        # optical blur growth from centre to corner
    center_sharpness: Optional[Param] = None     # baseline optical blur at the centre (diffraction, coating, etc.)


@dataclass
class ExposureProfile:
    """How the camera's metering and base sensitivity behave, upstream of the
    sensor's own response. Distinct from `ToneProfile`: this is "how much
    light reached the sensor", tone is "what the sensor/ISP does with it"."""

    iso_base: Optional[Param] = None
    exposure_compensation_ev: Optional[Param] = None
    metering_bias_ev: Optional[Param] = None     # systematic under/over-exposure from the metering pattern


@dataclass
class ColorProfile:
    """Section 4, Colour. A 3x3 matrix, per-channel behaviour, saturation, hue
    rotation, and *optionally* a LUT path as one stage inside this model — a
    LUT is never a substitute for it (section 4, section 10)."""

    matrix_3x3: Optional[tuple[
        tuple[Param, Param, Param],
        tuple[Param, Param, Param],
        tuple[Param, Param, Param],
    ]] = None
    saturation: Optional[Param] = None
    hue_rotation_deg: Optional[Param] = None
    highlight_tint: tuple[Optional[Param], Optional[Param], Optional[Param]] = (None, None, None)
    shadow_tint: tuple[Optional[Param], Optional[Param], Optional[Param]] = (None, None, None)
    crosstalk: Optional[Param] = None
    lut_path: Optional[str] = None  # relative path under build/, one stage inside the model, not the whole model


@dataclass
class ToneProfile:
    """Section 4, Tone. Historical cameras clip highlights and lose shadows —
    do not simulate modern HDR/local-contrast behaviour here (section 10)."""

    black_point: Optional[Param] = None
    white_point: Optional[Param] = None
    shadow_lift: Optional[Param] = None
    midtone_contrast: Optional[Param] = None
    highlight_compression: Optional[Param] = None
    shoulder: Optional[Param] = None


@dataclass
class NoiseProfile:
    """Section 4/5, sensor noise. Photon noise scales with sqrt(signal), read
    noise is roughly constant, chroma noise and pixel-response non-uniformity
    (PRNU) are separate terms, and noise generally becomes more visible in
    shadows — this is a decomposition, not "add grain-shaped noise everywhere"
    (section 10: never run the film-grain algorithm for a digital sensor)."""

    photon_noise_gain: Optional[Param] = None    # coefficient on sqrt(signal)
    read_noise: Optional[Param] = None           # signal-independent floor
    chroma_noise: Optional[Param] = None
    prnu: Optional[Param] = None                 # fixed per-pixel response non-uniformity
    shadow_visibility_boost: Optional[Param] = None  # how much more visible noise is in shadows vs midtones


@dataclass
class SharpeningProfile:
    """Section 4, Sharpening. Unsharp mask with radius/strength/threshold. Many
    2000s cameras sharpened hard — the threshold is what keeps faces from
    turning crunchy while edges stay crisp (section 4)."""

    radius_px: Optional[Param] = None
    strength: Optional[Param] = None
    threshold: Optional[Param] = None


@dataclass
class BloomProfile:
    """Highlight bloom/halation source term. Distinct from `NoiseProfile` and
    from the film-specific halation folded into `FilmProfile` (a backing-layer
    effect); this is the digital-sensor analogue — blooming charge overflow
    and lens flare around a blown highlight."""

    threshold: Optional[Param] = None            # luminance above which bloom seeds
    radius_pct: Optional[Param] = None           # of image width
    strength: Optional[Param] = None
    tint: tuple[Optional[Param], Optional[Param], Optional[Param]] = (None, None, None)


@dataclass
class CompressionProfile:
    """Section 4, Compression. Encode/decode through JPEG via ImageIO where
    the artefacts are part of the target. Not every camera needs this stage —
    leave the whole sub-profile off a camera that shoots losslessly."""

    jpeg_quality: Optional[Param] = None         # 0-100, ImageIO scale
    chroma_subsampling: str = ""                 # e.g. "4:2:0"; categorical, not a measured Param
    resize_before_encode_pct: Optional[Param] = None  # optional downsize applied before the encoder, if documented


@dataclass
class ResolutionProfile:
    """Section 4, Resolution. Downsample, process, sharpen, optionally
    upscale back — genuinely different from blurring the final output,
    because intermediate stages (sharpening, noise) see the lower-res signal."""

    native_megapixels: Optional[Param] = None
    downsample_factor: Optional[Param] = None
    upscale_after: Optional[Param] = None        # 1.0 = no upscale; >1.0 = upscaled back after processing


@dataclass
class FlashProfile:
    """Section 4, Flash. Falls off roughly as 1/distance^2, has its own colour
    temperature, and combines with ambient rather than replacing it. Critical
    for disposable, Polaroid and digicam profiles (section 6)."""

    intensity: Optional[Param] = None
    falloff_power: Optional[Param] = None        # nominally 2.0 for an inverse-square point source
    color_temp_k: Optional[Param] = None
    center_bias: Optional[Param] = None          # how strongly the flash favours frame centre over edges
    ambient_mix: Optional[Param] = None


@dataclass
class FilmProfile:
    """Section 2/6, the film pipeline's stock-specific stages: exposure onto
    film, film response, development, scanning. The shared `ColorProfile` /
    `ToneProfile` on the same `CameraProfile` still carry the overall grade;
    this carries what is specific to *this stock* independent of which camera
    it is loaded in (section 6: camera and stock are orthogonal)."""

    stock_name: str = ""                          # identity only, not a measured quantity
    iso: Optional[Param] = None
    reciprocity_failure_gamma: Optional[Param] = None  # long-exposure response departure from linear
    grain_rms: Optional[Param] = None
    grain_size_um: Optional[Param] = None
    development_variance: Optional[Param] = None  # push/pull and lab-to-lab variability
    scan_gamma: Optional[Param] = None            # scanner's own tone response, separate from the stock's
    halation_strength: Optional[Param] = None     # backing-layer halation characteristic of this stock


@dataclass
class InstantFilmProfile:
    """Section 6, Instant. Its own engine: narrow dynamic range, distinctive
    and temperature-dependent chemistry, seeded regional variation so no two
    frames are pixel-identical, kept subtle. Highlights clip sooner and
    shadows crush sooner than digital. Warm development gives yellow/orange/
    pink casts, cold gives blue/green and reduced saturation — neither at full
    strength by default (that is a look-authoring decision, not a schema one).

    `chemistry_note` exists specifically to carry the disclaimer CLAUDE.md
    requires: current Polaroid chemistry differs from 1980s chemistry, and a
    profile must say which one it is modelling rather than conflating them.
    """

    dynamic_range_stops: Optional[Param] = None
    highlight_clip: Optional[Param] = None
    shadow_crush: Optional[Param] = None
    development_temp_reference_c: Optional[Param] = None
    temp_sensitivity: Optional[Param] = None      # how strongly colour cast responds to temp deviation from reference
    warm_shift_tint: tuple[Optional[Param], Optional[Param], Optional[Param]] = (None, None, None)
    cold_shift_tint: tuple[Optional[Param], Optional[Param], Optional[Param]] = (None, None, None)
    regional_variation_strength: Optional[Param] = None
    regional_variation_seed: int = 0              # a mechanism, not a measured quantity
    chemistry_note: str = ""                      # e.g. "modern (2021-) chemistry" vs "1980s chemistry"


@dataclass
class FrameProfile:
    """The physical frame layer: paper border, edge shadow, texture. A
    separate layer applied last (it occludes rather than tints), per the
    render-order note in pipeline.py. Instant frames carry a larger bottom
    border; sprocket frames (35mm) carry perforations instead of a border."""

    style: str = "none"                           # none | sprocket | instant; categorical
    border_top_pct: Optional[Param] = None
    border_bottom_pct: Optional[Param] = None
    border_left_pct: Optional[Param] = None
    border_right_pct: Optional[Param] = None
    paper_tint: tuple[Optional[Param], Optional[Param], Optional[Param]] = (None, None, None)
    edge_shadow_strength: Optional[Param] = None
    texture_strength: Optional[Param] = None


# ---------------------------------------------------------------------------
# CameraProfile — CLAUDE.md section 3, verbatim field list.
# ---------------------------------------------------------------------------


@dataclass
class CameraProfile:
    """The v2 profile. Adding a camera means filling this in plus references
    plus calibration (section 7) — never writing a new Swift renderer
    (section 3). Which optional sub-profile is attached selects the pipeline;
    see `family`.
    """

    id: str
    name: str
    category: CameraCategory

    sensor: Optional[SensorProfile] = None
    lens: Optional[LensProfile] = None
    exposure: Optional[ExposureProfile] = None
    color: Optional[ColorProfile] = None
    tone: Optional[ToneProfile] = None
    noise: Optional[NoiseProfile] = None
    sharpening: Optional[SharpeningProfile] = None
    bloom: Optional[BloomProfile] = None
    compression: Optional[CompressionProfile] = None
    resolution: Optional[ResolutionProfile] = None
    flash: Optional[FlashProfile] = None

    film: Optional[FilmProfile] = None
    instant_film: Optional[InstantFilmProfile] = None
    frame: Optional[FrameProfile] = None

    @property
    def family(self) -> PipelineFamily:
        """Which render graph (section 2) this profile runs.

        `film` and `instant_film` are mutually exclusive by construction — a
        camera is either loaded with print film, is an instant camera, or is
        digital, never two at once. Raising here rather than silently
        preferring one is deliberate: a profile that sets both is a data bug,
        and picking one pipeline for it anyway would hide that bug behind a
        result that looks fine and is quietly wrong.
        """
        if self.film is not None and self.instant_film is not None:
            raise ValueError(
                f"{self.id!r}: both `film` and `instant_film` are set; a profile selects exactly one pipeline"
            )
        if self.instant_film is not None:
            return PipelineFamily.INSTANT_FILM
        if self.film is not None:
            return PipelineFamily.FILM
        return PipelineFamily.DIGITAL

    def to_dict(self) -> dict[str, Any]:
        return to_dict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent) + "\n"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CameraProfile":
        return from_dict(cls, data)

    @classmethod
    def from_json(cls, text: str) -> "CameraProfile":
        return cls.from_dict(json.loads(text))


# ---------------------------------------------------------------------------
# Generic dataclass <-> JSON. Small and specific to the shapes this schema
# actually uses (dataclasses, Enum, Param, Optional, list, fixed-length and
# variadic tuples, plain scalars) rather than a general-purpose library,
# because "JSON round-trip must preserve confidence" is the actual
# requirement and a bespoke walker is easier to trust than a dependency.
# ---------------------------------------------------------------------------


def _unwrap_optional(tp: Any) -> Any:
    if get_origin(tp) is Union:
        args = [a for a in get_args(tp) if a is not type(None)]
        if len(args) == 1:
            return args[0]
    return tp


def to_dict(obj: Any) -> Any:
    """Recursively lower a profile (or any piece of one) to plain JSON-able data."""
    if obj is None:
        return None
    if isinstance(obj, Param):
        return obj.to_dict()
    if isinstance(obj, Enum):
        return obj.value
    if is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: to_dict(getattr(obj, f.name)) for f in dc_fields(obj)}
    if isinstance(obj, (list, tuple)):
        return [to_dict(v) for v in obj]
    return obj  # str, int, float, bool


def from_dict(tp: Any, data: Any) -> Any:
    """Recursively rebuild a typed value from plain JSON-able data, guided by
    `tp` (a dataclass, `Param`, `Enum`, `Optional[...]`, `list[...]`, a fixed
    or variadic `tuple[...]`, or a plain scalar type)."""
    if data is None:
        return None
    tp = _unwrap_optional(tp)
    if tp is Param:
        return Param.from_dict(data)

    origin = get_origin(tp)
    if origin is list:
        (item_t,) = get_args(tp)
        return [from_dict(item_t, v) for v in data]
    if origin is tuple:
        args = get_args(tp)
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(from_dict(args[0], v) for v in data)
        return tuple(from_dict(t, v) for t, v in zip(args, data))

    if isinstance(tp, type) and issubclass(tp, Enum):
        return tp(data)
    if is_dataclass(tp):
        hints = get_type_hints(tp)
        kwargs = {f.name: from_dict(hints[f.name], data[f.name]) for f in dc_fields(tp) if f.name in data}
        return tp(**kwargs)

    return data  # str, int, float, bool already in their final shape


# ---------------------------------------------------------------------------
# Validation — the guard the whole module exists for.
# ---------------------------------------------------------------------------


@dataclass
class ValidationIssue:
    path: str
    value: float
    confidence: Confidence
    source: Optional[str]
    reason: str

    def __str__(self) -> str:
        src = self.source or "no source"
        return f"{self.path}: {self.reason} (value={self.value!r}, confidence={self.confidence.value}, {src})"


def iter_params(obj: Any, path: str = "") -> Iterator[tuple[str, Param]]:
    """Walk a profile (or any dataclass/list/tuple tree) and yield every
    `(dotted.path, Param)` actually present. `None` fields are not modelled
    and are skipped, not flagged — see the module docstring."""
    if obj is None:
        return
    if isinstance(obj, Param):
        yield path, obj
        return
    if is_dataclass(obj) and not isinstance(obj, type):
        for f in dc_fields(obj):
            val = getattr(obj, f.name)
            sub = f"{path}.{f.name}" if path else f.name
            yield from iter_params(val, sub)
        return
    if isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            yield from iter_params(v, f"{path}[{i}]")
        return
    # str, int, float, bool, Enum: nothing to descend into


def validate(profile: CameraProfile) -> list[ValidationIssue]:
    """Report every present parameter that is either an admitted guess or
    unsourced, per CLAUDE.md section 3's "fake precision is worse than an
    honest unknown." An empty return means every number in the profile that
    exists has a source and is not flagged as artistic. It does not mean the
    profile is complete — fields left as `None` are invisible to this
    function by design; completeness is a calibration-coverage question,
    this is a provenance-honesty question.
    """
    issues: list[ValidationIssue] = []
    for path, p in iter_params(profile):
        if p.confidence is Confidence.ARTISTIC_APPROXIMATION:
            issues.append(ValidationIssue(path, p.value, p.confidence, p.source, "artisticApproximation"))
        elif p.source is None:
            issues.append(ValidationIssue(path, p.value, p.confidence, p.source, "missing source"))
    return issues


def format_validation_report(profile: CameraProfile) -> str:
    """Human-readable form of `validate()`, for `python3 -m filmlab` output."""
    issues = validate(profile)
    if not issues:
        return f"{profile.id}: every present parameter is sourced and non-artistic."
    lines = [f"{profile.id}: {len(issues)} parameter(s) need attention:"]
    lines += [f"  - {i}" for i in issues]
    return "\n".join(lines)
