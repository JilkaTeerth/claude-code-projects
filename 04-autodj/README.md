# autodj

An AI DJ. Claude plans the set, a deterministic engine mixes it.

## Pipeline: Ears, Brain, Hands, Judge

- **Ears** (`analyze.py`): BPM, beat grid, downbeat phase, key in Camelot notation, 16 and 32 bar sections.
- **Brain**: Claude writes a JSON mix plan, which tracks, what tempo zone, which transition technique and on which bar, with a written reason for each.
- **Hands** (`mix.py`): tempo stretch, per stem faders, bass swaps, filter blends, echo outs, loop rolls.
- **Judge** (`judge.py`): checks every transition for beat offset, bass clash, vocal clash and loudness jumps, and draws spectrograms.

## How it got better from feedback

- Set 1, my verdict: "horrible", two vocals at once. Root cause: no stems. Added demucs stem separation and a vocal clash counter. Set 2: 0 clashes on all 12 transitions.
- Set 2, "booming noise". Root cause: the incoming kick and sub under the outgoing bass. Fix: everything under 150 Hz rides the bass fader.
- Then Claude researched how real pop DJs transition and wrote the rules into `TRANSITIONS.md`: keep one vocal going through the change, 8 bar blends, no echo outs.
- Whisper on vocal stems gives word timings for wordplay transitions.

## A real bug found

Rubber Band's R3 time stretch drifts about 30 ms per minute while keeping total length exact, so beats slowly slide apart. Switched to R2 and verified beat lock at 1.5 ms.

## What's in `src/`

The `autodj` package, the transitions playbook, one mix plan, and a synthetic track test. Songs, stems, lyrics and rendered mixes are left out because they're commercial music.
