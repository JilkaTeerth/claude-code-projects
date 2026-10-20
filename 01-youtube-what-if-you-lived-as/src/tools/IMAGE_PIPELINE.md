# Image Pipeline, fal Flux schnell (locked 2026-07-17)

Replaces GPT Image 2 / Nano Banana for episode frame generation. Same crude-charming
"tardigrade" doodle look (the ep005 breakout style, 1k+ views), at a fraction of the cost.

## Why
| Model | Per image | 71-frame episode |
|---|---:|---:|
| **fal Flux schnell** ← use this | ~$0.003 | **~$0.20** |
| Nano Banana / Gemini Flash | ~$0.039 | ~$2.77 |
| GPT Image 2 (medium) | ~$0.07 | ~$4.97 |
| Nano Banana Pro | ~$0.12+ | ~$8.50+ |

~13 to 40× cheaper. Text renders as gibberish on cheap models, so frames are generated
**wordless**, the VO + burned captions carry all meaning (this is how the real episodes work).

## How
`tools/.venv/bin/python tools/batch_images.py videos/<episode-folder>`

Reads that episode's `02_IMAGE_PROMPTS.md`, and for every beat:
- **content frames** → fal Flux schnell, wrapped in the locked style template, text-stripped, wordless.
- **chapter cards** → composited locally with PIL (crisp title text over a warm textured bg).
- writes `assets/frames/img_NNN.png` + `assets/CONTACT_SHEET.png` for review.

Key settings baked into `batch_images.py`:
- `enable_safety_checker: false`, Flux's checker false-trips on pink-blob prompts and returns
  pure-black frames. Off = fixed. (Re-check with the brightness scan; regen any <25 mean.)
- `clean_scene()` strips quoted text/label requests so Flux draws no words.
- `NOTEXT` directive forbids letters/numbers in-frame.
- seeds are deterministic (`2000 + idx*13`) so reruns are reproducible; bump to reroll.

## Locked style template (the winning formula)
> Charming childlike hand-drawn doodle in a warm storybook felt-tip marker style. Bold clean
> black outlines, flat solid fill colors, only soft gentle shading. Soothing warm earthy palette:
> soft pink, warm brown, cream, muted amber. Calm, cozy, friendly, never scary, never realistic.
> Background is a simple hand-drawn scene with gentle soothing texture (soft cross-hatched earth,
> warm ambient glow, subtle grain). Uncluttered, generous negative space.

Character anchor: rounded soft-pink body, two big square buck teeth, small friendly eyes, stick
legs, thin tail, silly and cute, same simple way every frame.

## Requirements
- `FAL_KEY` in `youtube-automation/.env` (gitignored).
- venv at `tools/.venv` with `pillow` (google libs already there for the analytics tool).

## Known trade-offs
- Flux occasionally leaves a tiny fake-signature scribble in a corner, harmless, croppable.
- Frames are wordless; if a specific number/label matters (a clock reading, a graph), PIL-overlay
  it in production rather than trusting the model to spell it.
