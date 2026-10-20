# Sixty Cuts power hour

A finished 60 minute movie power hour: 60 rounds of exactly 60 seconds, alternating Bollywood and Hollywood scenes. The format is cloned shot for shot from an existing YouTube video, only the films are new.

## How it was built

- Claude measured the reference video frame by frame at 1280x720 and wrote every measurement into `SPEC.md`: when the picture reveals, where the title fades in, the countdown numeral sizes.
- ffmpeg and Python make what an editor can't: 60 loudness levelled 60 second clips (`clean.sh`), a ProRes 4444 countdown leader with real alpha (`leader_ref.py`), the intro background.
- **Palmier Pro MCP** assembles the whole hour live: 361 objects on six tracks.

## Accuracy

No installed font matched the reference numerals, so digits are rendered large, cropped to the ink and resampled to the measured box. Countdown numeral 282x417 vs a target of 286x420. "Drink!" 630x161 vs 629x161.

Palmier quirk found along the way: `fontSize` renders at about 0.66x canvas pixels and caps at 300, so big text has to be scaled or baked into video.

## What's in `src/`

README, SPEC, the build scripts and the scene list. The video itself is left out (copyrighted film clips).
