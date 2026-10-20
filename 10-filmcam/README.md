# FilmCam

A retro film camera app for iOS in native Swift: live filtered preview, 15 original film looks, a re editable roll.

## The clever bit: a look lab outside the phone

Without a simulator and with a 7 day signing certificate, a rebuild and squint loop would make look design painful. So Claude built `tools/filmlab`, a numpy reference version of the whole render pipeline, where most "does this colour work" questions are answered in seconds.

- Parametric colour ops: CDL, channel crosstalk, split toning, monotonic tone curves, highlight rolloff.
- 15 looks across 6 families (Kodak Gold, Polaroid 600, 2000s digicam, early iPhone and more), each split into a grade baked into a 3D LUT plus spatial effects (halation, grain, vignette).
- `filmlab check` proves the LUT memory layout with an identity round trip and an asymmetry probe, because an identity LUT passes even when red and blue are swapped.
- LUTs are named by content hash and never deleted, so retuning a look never changes photos already taken.

## Swift side

Capture session, Metal preview, a render engine, a grain kernel and the camera library, driven by `looks.json` from the lab.

## What's in `src/`

The Swift app source, the filmlab toolkit and the research notes on each film stock.
