"""filmlab CLI.

    python3 -m filmlab check       verify the LUT layout invariants
    python3 -m filmlab build       emit .cubedata + .cube + looks.json
    python3 -m filmlab sheet       render contact sheets for review
    python3 -m filmlab calibrate   compare a render against a reference photo

`build` is what feeds the iOS app. `sheet` is what feeds your eyes. `calibrate`
is what feeds a `Param`'s `source` field — see CLAUDE.md section 7 and
`calibrate.py`'s module docstring.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from . import calibrate, charts, contact_sheet, lut, pipeline
from .looks import ALL_LOOKS, BY_ID

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "build"


def _downscale(img: np.ndarray, factor: int) -> np.ndarray:
    """Box-average by an integer factor.

    Why the contact sheet renders large and then shrinks: grain cell size is a
    fraction of image width, so at a small render width the cell collapses to a
    single pixel and reads as digital noise rather than grain. A phone never
    shows you that; it shows a 4032px render scaled down, where the grain
    averages into texture. Reviewing at the render resolution makes every look
    seem far too grainy and leads you to under-dial the amount.
    """
    if factor <= 1:
        return img
    h = img.shape[0] // factor * factor
    w = img.shape[1] // factor * factor
    trimmed = img[:h, :w]
    return trimmed.reshape(h // factor, factor, w // factor, factor, 3).mean(axis=(1, 3)).astype(np.float32)


def _load_image(path: Path, width: int) -> np.ndarray:
    """Load a real photograph as float32 sRGB, scaled to `width`.

    Synthetic charts exaggerate grain, because flat patches give it nothing to
    hide behind. Always confirm a look on a real photograph before trusting the
    chart; detail masks grain and the honest amount is usually higher than the
    chart suggests.
    """
    from PIL import Image

    img = Image.open(path).convert("RGB")
    if width and img.width != width:
        h = max(int(round(img.height * width / img.width)), 1)
        img = img.resize((width, h), Image.LANCZOS)
    return (np.asarray(img, dtype=np.float32) / 255.0).astype(np.float32)


def cmd_check(_: argparse.Namespace) -> int:
    """Prove the cube layout before anything downstream trusts it."""
    ident = lut.identity_error()
    asym = lut.asymmetry_error()
    print(f"identity round-trip max error : {ident:.3e}")
    print(f"asymmetry (R/B transposition) : {asym:.3e}")

    ok = ident < 1e-5 and asym < 1e-5
    if not ok:
        print("\nFAIL: cube layout is wrong. Do not generate LUTs until this passes.")
        return 1

    # Every look must produce finite, in-range output for every lattice point.
    bad = []
    for lk in ALL_LOOKS:
        cube = lut.build(lk, 17)
        if not np.isfinite(cube).all():
            bad.append(f"{lk.id}: non-finite values")
        elif cube.min() < -1e-4 or cube.max() > 1.0 + 1e-4:
            bad.append(f"{lk.id}: out of range [{cube.min():.3f}, {cube.max():.3f}]")
    if bad:
        print("\nFAIL:")
        for b in bad:
            print("  " + b)
        return 1

    print(f"\nall {len(ALL_LOOKS)} looks grade clean")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    """Emit the artefacts the app consumes."""
    out = Path(args.out) if args.out else BUILD
    lut_dir = out / "luts"
    cube_dir = out / "cube"

    manifest = []
    for lk in ALL_LOOKS:
        cube = lut.build(lk, args.size)
        blob = lut.to_cubedata(cube)
        import hashlib

        digest = hashlib.sha256(blob).hexdigest()

        # Content-hash naming: retuning a look writes a new file and leaves the
        # old one intact, so shots already graded with it keep rendering.
        lut.write_cubedata(lut_dir / f"{digest}.cubedata", cube)
        if not args.no_cube:
            lut.write_cube(cube_dir / f"{lk.id}.cube", cube, title=lk.name)

        entry = lk.to_json()
        entry["lut"] = {"data": f"luts/{digest}.cubedata", "size": args.size, "amount": 1.0, "sha256": digest}
        manifest.append(entry)
        print(f"  {lk.id:12} {lk.family:16} {digest[:12]}  {len(blob) / 1024:6.1f} KB")

    looks_json = out / "looks.json"
    looks_json.parent.mkdir(parents=True, exist_ok=True)
    looks_json.write_text(json.dumps({"version": 1, "looks": manifest}, indent=2) + "\n")

    total = sum((lut_dir / f"{e['lut']['sha256']}.cubedata").stat().st_size for e in manifest)
    print(f"\n{len(manifest)} looks → {looks_json}")
    print(f"LUT payload: {total / 1024 / 1024:.2f} MB at size {args.size}")
    return 0


def cmd_sheet(args: argparse.Namespace) -> int:
    """Render contact sheets for visual review."""
    out = Path(args.out) if args.out else BUILD / "sheets"
    selected = [BY_ID[i] for i in args.looks] if args.looks else ALL_LOOKS

    ss = max(args.supersample, 1)
    if args.source:
        source = _load_image(Path(args.source), args.width * ss)
    else:
        source = charts.test_sheet()
        ss = 1  # charts are already at review size
    tile = pipeline.make_noise_tile()

    tiles: list[tuple[str, np.ndarray]] = [("00 · SOURCE", _downscale(source, ss))]
    for lk in selected:
        cube = lut.build(lk, args.size)
        rendered = pipeline.render(source, lk, cube=cube, tile=tile, grain_on=not args.no_grain)
        tiles.append((f"{lk.id} · {lk.family}", _downscale(rendered, ss)))

    sheet = contact_sheet.grid(tiles, cols=args.cols)
    path = contact_sheet.save(sheet, out / "looks-contact-sheet.jpg")
    print(f"wrote {path}  ({sheet.width}x{sheet.height})")

    # A halation-only sheet, because that stage is invisible on a colour chart.
    hi = charts.highlight_scene(420)
    hal_tiles: list[tuple[str, np.ndarray]] = [("00 · SOURCE", hi)]
    for lk in selected:
        cube = lut.build(lk, args.size)
        hal_tiles.append(
            (f"{lk.id} · hal {lk.halation.strength:.2f}",
             pipeline.render(hi, lk, cube=cube, tile=tile, grain_on=not args.no_grain))
        )
    hsheet = contact_sheet.grid(hal_tiles, cols=args.cols)
    hpath = contact_sheet.save(hsheet, out / "halation-contact-sheet.jpg")
    print(f"wrote {hpath}  ({hsheet.width}x{hsheet.height})")
    return 0


def cmd_calibrate(args: argparse.Namespace) -> int:
    """Compare a rendered image against a reference photo, stage by stage.

    Deliberately thin: all the actual work — and the "why not just diff the
    pixels" reasoning — lives in `calibrate.py`. This just loads both images
    at a shared analysis width and prints the report.
    """
    print(calibrate.run(Path(args.rendered), Path(args.reference), args.width))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="filmlab", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="verify LUT layout invariants")
    c.set_defaults(fn=cmd_check)

    b = sub.add_parser("build", help="emit .cubedata + .cube + looks.json")
    b.add_argument("--size", type=int, default=lut.DEFAULT_SIZE)
    b.add_argument("--out", default=None)
    b.add_argument("--no-cube", action="store_true", help="skip the .cube exports")
    b.set_defaults(fn=cmd_build)

    s = sub.add_parser("sheet", help="render contact sheets")
    s.add_argument("--size", type=int, default=lut.DEFAULT_SIZE)
    s.add_argument("--cols", type=int, default=4)
    s.add_argument("--out", default=None)
    s.add_argument("--looks", nargs="*", default=None, help="look ids; default all")
    s.add_argument("--no-grain", action="store_true")
    s.add_argument("--source", default=None, help="a real photo to grade instead of the charts")
    s.add_argument("--width", type=int, default=520, help="review width for --source")
    s.add_argument("--supersample", type=int, default=4, help="render at N x review width, then downscale")
    s.set_defaults(fn=cmd_sheet)

    cal = sub.add_parser("calibrate", help="compare a render against a reference photo, stage by stage")
    cal.add_argument("rendered", help="path to the rendered image (our pipeline's output)")
    cal.add_argument("reference", help="path to the reference photograph (the real camera's output)")
    cal.add_argument("--width", type=int, default=1024, help="shared analysis width both images are resampled to")
    cal.set_defaults(fn=cmd_calibrate)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
