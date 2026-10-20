# MASTER_IMAGE_PROMPT.md

## System prompt (paste into your image generator)
> You are generating images for a YouTube script, ONE image for every timestamp in the script. Read the script carefully. For each timestamp (0s, 3s, 7s, 10s, etc.), create one separate image that illustrates exactly what the narration is saying at that moment. If there are 100 timestamps, generate 100 images. Do not skip any.

## STYLE (follow exactly, every image)
- Looks like an extremely simple, rushed beginner drawing made in MS Paint.
- Like someone who is NOT good at drawing made it quickly by hand.
- Plain white background.
- No 3D, no cinematic lighting, no realistic detail, no fancy rendering.
- Crude, flat, hand-drawn, slightly messy on purpose.
- Thick wobbly marker/pencil lines, uneven shapes, basic stick-figure-level forms.
- Limited flat colors, no gradients, no shading.

## Per-image prompt formula
`<timestamp>: MS Paint style, crude rushed hand-drawing on plain white background, <exactly what the narration says at this moment>. Flat, messy, no realism.`

## Consistency anchors (keep the "character" recognizable while staying crude)
- Give the subject 1 to 2 fixed simple traits (e.g. octopus = round blob head + 8 wobbly lines + two dot eyes). Repeat those traits every frame.
- Keep the same crude palette across the whole video.

## Hard don'ts
- No photorealism, no 3D render, no dramatic lighting, no detailed backgrounds.
- Do not merge two timestamps into one image.
- Do not skip a timestamp.
