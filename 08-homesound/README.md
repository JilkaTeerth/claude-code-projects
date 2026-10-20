# homesound

Free multi room audio: one source playing on a house full of mismatched cheap speakers, in sync, from a Mac.

## Result

An Edifier D32 and a JBL Go 3 over Bluetooth playing in sync at **7.4 ms** residual error, for ₹0.

## How

- Started with Snapcast and dropped it. Bluetooth latency differs per speaker and Snapcast couldn't correct it well enough.
- Claude wrote a custom CoreAudio engine (`app/engine.py`) that delays each output by its measured latency.
- `scripts/measure_sync.py` plays clicks and measures the offset between speakers through the mic, so calibration is measured, not guessed.
- Every architecture decision is logged in `logs/decisions.md`.

## What's in `src/`

The engine, device probing, calibration, measurement scripts, the plan, research and state docs. The web UI JavaScript was never written, that's the open task.
