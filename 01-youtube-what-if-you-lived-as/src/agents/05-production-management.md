# Agent 05, Production Management

## Mission
Turn the script + prompts + SEO + thumbnail into a finished, uploadable video.

## Inputs
- `01_SCRIPT.md`, `02_IMAGE_PROMPTS.md`, `03_SEO.md`, `04_THUMBNAIL.md`
- `templates/ELEVENLABS_GUIDE.md`

## Steps
1. **Voiceover (ElevenLabs).** Paste the narration (timestamps stripped) using the settings in ELEVENLABS_GUIDE.md. Export WAV. Keep the eerie/measured delivery.
2. **Images.** Generate one image per prompt in `02_IMAGE_PROMPTS.md`, in order, named `img_001.png`, `img_002.png`... matching timestamp order.
3. **Verify parity.** Run the check: number of images == number of timestamps == number of narration lines. If mismatch, STOP and report.
4. **Assemble.** Each image is on screen for the duration of its narration line (align image N start to timestamp N). Add subtle ambient/eerie bed music low under VO. Optional light zoom on each image.
5. **Captions.** Burn or upload SRT built from timestamps.
6. **Export** 1080p (or 1440p) MP4. Write `edit.md` noting music track, any manual timing tweaks, and total runtime.

## Parity check (pseudo)
```
timestamps  = count("[MM:SS]" lines in 01_SCRIPT.md)
prompts     = count(entries in 02_IMAGE_PROMPTS.md)
images      = count(img_*.png)
assert timestamps == prompts == images
```

## Handoff
Deliver final MP4 + thumbnail PNG + runtime to Agent 06.
