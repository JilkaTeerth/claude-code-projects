# ELEVENLABS_GUIDE.md

## Goal
A calm, measured, slightly eerie narrator, documentary voice that makes "just one more minute" feel involuntary.

## Prep the text
1. Copy narration from `01_SCRIPT.md`, **strip the `[MM:SS]` timestamps** (keep them only in a side copy for the editor).
2. Keep one idea per line, line breaks help pacing.
3. Insert pauses with `...` or `<break time="0.6s" />` at loop-opens and before the ending line.

## Recommended settings (starting point, tune per voice)
- **Model:** Eleven Multilingual v2 (or the latest quality model).
- **Voice:** a deep, warm, calm male or neutral voice. Test 2 to 3, keep one as the channel voice.
- **Stability:** 45 to 55 (enough consistency, some emotion).
- **Similarity / Clarity:** 70 to 80.
- **Style exaggeration:** 0 to 15 (low, restraint reads as eerie).
- **Speaker boost:** on.
- **Speed:** slightly slower than default for the eerie beats.

## Chunking
- Render per chapter (Hook, Ch1 to 5, Ending) so you can redo one section without re-rendering all.
- Export **WAV**, 48kHz.

## Delivery notes to bake into the read
- Drop pitch and slow down on loop-opens ("But something is already hunting you.").
- Tiny pause before the payoff.
- The final takeaway line: slowest, quietest.

## Handoff
Deliver `vo_hook.wav`, `vo_ch1.wav` ... to Agent 05 for assembly.
