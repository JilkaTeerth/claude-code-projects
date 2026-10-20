# filmcam

A retro film camera for iOS. Live filtered preview, original film looks, a re editable roll.

Working name. Plan lives at `~/.claude/plans/use-this-new-plugin-enchanted-swing.md`.

## Status

| Phase | State |
|---|---|
| Phase 0, ism teardown | blocked, needs Chrome awake + a screen recording |
| Phase 1, stack decision | recommended native Swift, awaiting confirmation |
| Phase 2, `tools/filmlab` | **working**, 15 looks generating |
| Phase 2, iOS app | not started, blocked on Xcode install |

## tools/filmlab

The look authoring toolkit and the numpy reference implementation of the render
pipeline. This exists because the iOS side has no simulator and a 7 day signing
certificate, so a rebuild-and-squint loop would make look design unbearable.
Ninety percent of "does this colour relationship work" is answerable here in
seconds.

```
python3 -m filmlab check     # verify the LUT layout invariants
python3 -m filmlab build     # emit .cubedata + .cube + looks.json
python3 -m filmlab sheet     # contact sheets over the synthetic charts
python3 -m filmlab sheet --source photo.jpg --width 400 --supersample 3
```

Run `check` before trusting anything else. It proves the cube memory layout with
an identity round trip *and* an asymmetry probe, because an identity LUT is
symmetric under an R/B transposition and so passes even when the layout is
wrong. It then confirms all 15 looks grade to finite, in range values.

### Layout

- `ops.py`, parametric colour operations. CDL, channel crosstalk, split toning,
  monotonic PCHIP tone curves, highlight rolloff, mono channel mixing.
- `looks.py`, the 15 looks across 6 families. Each is a parameter set, split
  into a **grade** (bakes into the LUT) and **spatial** params (halation, grain,
  vignette) that the render graph executes.
- `lut.py`, 3D LUT build, export and trilinear sampling, plus the layout tests.
- `pipeline.py`, the whole pipeline in numpy. Design surface and oracle.
- `charts.py`, synthetic colour chart, skin strip, grey ramp, halation scene.
- `contact_sheet.py`, labelled grid output.

### Output

`build/looks.json` plus `build/luts/<sha256>.cubedata`. LUTs are named by content
hash and never deleted, so retuning a look writes a new file and every shot
already graded with the old one keeps rendering exactly as it did.

`.cubedata` is a raw float32 RGBA blob in exactly the layout
`CIColorCubeWithColorSpace` expects: red index varying fastest, then green, then
blue, alpha always 1.0. Swift loads it with `Data(contentsOf:)` and hands it
straight to `inputCubeData`. No parser, no PNG strip decode. A `.cube` text
export is also written so looks can be opened in DaVinci while designing.

At size 33 the full set is 8.2 MB.

## Two things that cost real time, recorded so they are not rediscovered

**Grain `amount` is a standard deviation, not a vague intensity.** The noise tile
is normalised to unit variance, so `amount=0.12` literally means noise with a std
of 0.12 in 0..1 space, which is about +/- 30/255. Real film grain is nearer
+/- 6/255. The looks were first authored around 0.12 to 0.30 and read as heavy
digital noise. The usable band is roughly **0.015 to 0.06**.

**Do not judge grain at the render resolution.** Grain cell size is a fraction of
image width so preview and capture agree, which means at a small render width
the cell collapses toward a single pixel and reads as noise. A phone never shows
you that; it shows a 4032px render scaled down. Use `--supersample` so the sheet
renders large and downscales, and always confirm on a real photograph, since
flat synthetic patches give grain nothing to hide behind.

## Looks

| Family | Looks | Behaviour modelled |
|---|---|---|
| warm-negative | Sundeck, Terracotta, Honeyline | warm cast, lifted muddy shadows, forgiving skin |
| cool-negative | Coldstore, Nightbus, Municipal | cool shadows, green midtone bias, coarser grain |
| reversal | Postcard, Rally | high saturation and contrast, fine grain, unforgiving |
| pastel | Linen, Powder | heavily lifted blacks, low saturation, soft contrast |
| mono | Graphite, Selenium, Foxglove | channel-weighted B&W, neutral / cool / sepia toned |
| camera | Flashbulb, Compact | disposable-with-flash, and the 2003 compact |

Every parameter here is original. Nothing is sampled, traced or reverse
engineered from any commercial LUT pack or from any shipping app. Where a look
is described as behaving like a class of film stock, that refers to documented
photochemical behaviour, not to any stock's trademarked identity.
