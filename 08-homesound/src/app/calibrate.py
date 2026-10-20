"""Acoustic auto-calibration.

Tapping a spacebar in time with a click gets you within maybe 30-50ms, which
is not good enough -- the ear starts hearing echo around 20ms.

So instead we measure it properly: emit a chirp from ONE speaker, record it
on the Mac's microphone, and cross-correlate to find the true end-to-end
acoustic delay. That captures everything -- Bluetooth codec latency, device
buffering, and speaker distance -- in one number, with sub-millisecond
resolution.

Run it once per speaker and the whole group lines up automatically.
"""
from __future__ import annotations

import time

import numpy as np
import sounddevice as sd

from .engine import CHANNELS, SR

CHIRP_SEC = 0.25
LISTEN_SEC = 1.6
SPEED_OF_SOUND = 343.0  # m/s, for the distance readout


def make_chirp(sr: int = SR) -> np.ndarray:
    """Log sweep 500Hz -> 8kHz. Cross-correlates far more sharply than a click
    and survives cheap speakers' bad low-end response."""
    n = int(sr * CHIRP_SEC)
    t = np.arange(n) / sr
    f0, f1 = 500.0, 8000.0
    k = np.log(f1 / f0)
    phase = 2 * np.pi * f0 * CHIRP_SEC / k * (np.exp(t * k / CHIRP_SEC) - 1.0)
    sig = np.sin(phase).astype(np.float32)
    # taper the ends so we don't add a broadband click of our own
    ramp = int(sr * 0.01)
    win = np.ones(n, dtype=np.float32)
    win[:ramp] = np.linspace(0, 1, ramp)
    win[-ramp:] = np.linspace(1, 0, ramp)
    return sig * win


def measure_latency(
    output_index: int,
    input_index: int | None = None,
    amplitude: float = 0.45,
    repeats: int = 3,
) -> dict:
    """Play a chirp on `output_index`, record on the mic, return the delay.

    Repeats and takes the median so one bad measurement (a door slamming,
    someone talking) doesn't poison the result.
    """
    chirp = make_chirp()
    n_listen = int(SR * LISTEN_SEC)

    pad = np.zeros((int(SR * 0.15), CHANNELS), dtype=np.float32)
    body = np.column_stack([chirp, chirp]) * amplitude
    playbuf = np.concatenate([pad, body,
                              np.zeros((n_listen - len(pad) - len(body), CHANNELS),
                                       dtype=np.float32)])
    play_offset = len(pad)

    results: list[float] = []
    confidences: list[float] = []

    for _ in range(repeats):
        rec = np.zeros((n_listen, 1), dtype=np.float32)
        pos_p = 0
        pos_r = 0

        def out_cb(outdata, frames, time_info, status):  # noqa: ANN001
            nonlocal pos_p
            chunk = playbuf[pos_p: pos_p + frames]
            if len(chunk) < frames:
                outdata[: len(chunk)] = chunk
                outdata[len(chunk):] = 0
                raise sd.CallbackStop
            outdata[:] = chunk
            pos_p += frames

        def in_cb(indata, frames, time_info, status):  # noqa: ANN001
            nonlocal pos_r
            end = min(pos_r + frames, n_listen)
            rec[pos_r:end] = indata[: end - pos_r]
            pos_r = end

        istream = sd.InputStream(
            device=input_index, samplerate=SR, channels=1,
            dtype="float32", blocksize=512, callback=in_cb,
        )
        ostream = sd.OutputStream(
            device=output_index, samplerate=SR, channels=2,
            dtype="float32", blocksize=512, callback=out_cb,
        )
        istream.start()
        time.sleep(0.05)  # let the mic settle before the chirp fires
        ostream.start()
        time.sleep(LISTEN_SEC + 0.15)
        for s in (ostream, istream):
            try:
                s.stop(); s.close()
            except Exception:
                pass

        mic = rec[:, 0].astype(np.float64)
        if np.abs(mic).max() < 1e-4:
            continue  # heard nothing at all

        ref = chirp.astype(np.float64)
        mic = mic - mic.mean()
        corr = np.correlate(mic, ref, mode="valid")
        peak = int(np.argmax(np.abs(corr)))

        # confidence = how much the peak stands out from the rest
        mag = np.abs(corr)
        floor = np.median(mag) + 1e-12
        conf = float(min(1.0, (mag[peak] / floor) / 40.0))

        delay_frames = peak - play_offset
        delay_ms = delay_frames * 1000.0 / SR
        if -50.0 < delay_ms < 1500.0:
            results.append(delay_ms)
            confidences.append(conf)

    if not results:
        return {
            "ok": False,
            "error": "Nothing detected. Turn the speaker up, move it nearer the "
                     "Mac, and make sure microphone permission is granted.",
        }

    med = float(np.median(results))
    spread = float(np.max(results) - np.min(results)) if len(results) > 1 else 0.0

    # Peak sharpness alone is NOT confidence. It reported 1.0 on a measurement
    # whose repeats disagreed by 407ms (see logs/decisions.md 2026-08-02).
    # Repeatability is the honest signal, so fold spread in: anything with more
    # than ~20ms of spread is worthless, because 20ms is the echo threshold.
    sharpness = float(np.median(confidences))
    repeatability = 1.0 / (1.0 + (spread / 20.0))
    confidence = sharpness * repeatability

    return {
        "ok": True,
        "latency_ms": round(med, 2),
        "spread_ms": round(spread, 2),
        "confidence": round(confidence, 3),
        "peak_sharpness": round(sharpness, 3),
        "samples": len(results),
        "approx_distance_m": round(med / 1000.0 * SPEED_OF_SOUND, 2),
        "note": "Includes speaker distance from the mic (~2.9ms per metre).",
        # Bluetooth re-buffers on every stream start and this function opens a
        # fresh stream per repeat, so it is unreliable for BT speakers.
        # Use scripts/measure_sync.py, which measures without restarting.
        "unreliable_for_bluetooth": spread > 20.0,
    }


def default_input() -> int | None:
    try:
        return sd.default.device[0]
    except Exception:
        return None
