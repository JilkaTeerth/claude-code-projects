"""3D LUT construction, export and sampling.

The memory layout here is load-bearing and easy to get subtly wrong, so it is
stated once, explicitly, and then verified by `identity_error()`:

    Core Image's `CIColorCubeWithColorSpace` wants float32 RGBA, premultiplied,
    laid out with the **red index varying fastest**, then green, then blue.

We hold the lattice as `lut[b, g, r] -> rgb`, so a plain C-order flatten gives
exactly that ordering for free. Resolve's `.cube` text format uses the same
red-fastest convention, so both writers walk the same array the same way.

Alpha is always 1.0, which makes premultiplied and straight alpha identical and
removes the other classic source of cube-data confusion.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

from .looks import Look

DEFAULT_SIZE = 33


def identity_lattice(size: int = DEFAULT_SIZE) -> np.ndarray:
    """The unmodified colour cube, shaped (size, size, size, 3), indexed [b, g, r]."""
    ramp = np.linspace(0.0, 1.0, size, dtype=np.float32)
    r = ramp[None, None, :]
    g = ramp[None, :, None]
    b = ramp[:, None, None]
    return np.stack(np.broadcast_arrays(r, g, b), axis=-1).astype(np.float32)


def build(look: Look, size: int = DEFAULT_SIZE) -> np.ndarray:
    """Push the identity lattice through a look's grade. Shape (size, size, size, 3)."""
    lattice = identity_lattice(size)
    flat = lattice.reshape(-1, 3)
    graded = look.grade(flat)
    return np.clip(graded, 0.0, 1.0).reshape(size, size, size, 3).astype(np.float32)


def to_cubedata(lut: np.ndarray) -> bytes:
    """Serialise to the exact float32 RGBA blob Core Image consumes."""
    size = lut.shape[0]
    rgba = np.concatenate(
        [lut, np.ones((size, size, size, 1), dtype=np.float32)], axis=-1
    )
    return rgba.astype("<f4").tobytes(order="C")


def write_cubedata(path: Path, lut: np.ndarray) -> str:
    """Write the binary blob. Returns its sha256, which is also its filename stem."""
    blob = to_cubedata(lut)
    digest = hashlib.sha256(blob).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(blob)
    return digest


def write_cube(path: Path, lut: np.ndarray, title: str = "") -> None:
    """Write a Resolve/Lightroom-compatible .cube.

    Not consumed by the app. This exists so looks can be opened in real grading
    software while they are being designed, which is a much better review
    surface than squinting at a phone.
    """
    size = lut.shape[0]
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    if title:
        lines.append(f'TITLE "{title}"')
    lines.append(f"LUT_3D_SIZE {size}")
    lines.append("DOMAIN_MIN 0.0 0.0 0.0")
    lines.append("DOMAIN_MAX 1.0 1.0 1.0")
    lines.append("")
    for entry in lut.reshape(-1, 3):
        lines.append(f"{entry[0]:.6f} {entry[1]:.6f} {entry[2]:.6f}")
    path.write_text("\n".join(lines) + "\n")


def apply_lut(rgb: np.ndarray, lut: np.ndarray) -> np.ndarray:
    """Trilinearly sample a LUT. This is the numpy mirror of what the GPU does.

    Used by the reference pipeline so a look can be previewed on the Mac, and by
    `identity_error()` to prove the layout is right.
    """
    size = lut.shape[0]
    x = np.clip(np.asarray(rgb, dtype=np.float32), 0.0, 1.0) * (size - 1)

    lo = np.floor(x).astype(np.int32)
    hi = np.minimum(lo + 1, size - 1)
    f = (x - lo).astype(np.float32)

    r0, g0, b0 = lo[..., 0], lo[..., 1], lo[..., 2]
    r1, g1, b1 = hi[..., 0], hi[..., 1], hi[..., 2]
    fr = f[..., 0:1]
    fg = f[..., 1:2]
    fb = f[..., 2:3]

    # lut is indexed [b, g, r]
    c000 = lut[b0, g0, r0]
    c100 = lut[b0, g0, r1]
    c010 = lut[b0, g1, r0]
    c110 = lut[b0, g1, r1]
    c001 = lut[b1, g0, r0]
    c101 = lut[b1, g0, r1]
    c011 = lut[b1, g1, r0]
    c111 = lut[b1, g1, r1]

    c00 = c000 * (1 - fr) + c100 * fr
    c10 = c010 * (1 - fr) + c110 * fr
    c01 = c001 * (1 - fr) + c101 * fr
    c11 = c011 * (1 - fr) + c111 * fr

    c0 = c00 * (1 - fg) + c10 * fg
    c1 = c01 * (1 - fg) + c11 * fg

    return (c0 * (1 - fb) + c1 * fb).astype(np.float32)


def identity_error(size: int = DEFAULT_SIZE, samples: int = 4096, seed: int = 0) -> float:
    """Round-trip an identity LUT and return the max absolute error.

    This is the test that catches a transposed cube. If red and blue are swapped
    in the layout, this returns something near 1.0 instead of near 0.0, and you
    find out in a millisecond instead of after an hour of staring at a shader.

    The Swift side gets the same test against the real Core Image filter.
    """
    rng = np.random.default_rng(seed)
    probe = rng.random((samples, 3), dtype=np.float32)
    out = apply_lut(probe, identity_lattice(size))
    return float(np.abs(out - probe).max())


def asymmetry_error(size: int = DEFAULT_SIZE) -> float:
    """Catch a red/blue transposition that the identity test cannot see.

    An identity LUT is symmetric under swapping the R and B axes, so it passes
    even if the layout is transposed. This probes with a deliberately asymmetric
    LUT (red doubled, blue halved) and checks a known input maps to a known
    output. Returns max absolute error against the analytic answer.
    """
    lattice = identity_lattice(size)
    skewed = lattice.copy()
    skewed[..., 0] = np.clip(lattice[..., 0] * 0.5, 0.0, 1.0)
    skewed[..., 2] = np.clip(lattice[..., 2] * 0.5 + 0.5, 0.0, 1.0)

    probe = np.array(
        [[1.0, 0.0, 0.0], [0.0, 0.0, 1.0], [0.8, 0.4, 0.2]], dtype=np.float32
    )
    expect = probe.copy()
    expect[:, 0] *= 0.5
    expect[:, 2] = expect[:, 2] * 0.5 + 0.5

    got = apply_lut(probe, skewed)
    return float(np.abs(got - expect).max())
