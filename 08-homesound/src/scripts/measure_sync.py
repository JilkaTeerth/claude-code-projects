"""Measure the REAL residual sync error between two speakers, while playing.

Why this exists
---------------
`calibrate.measure_latency` opens a fresh CoreAudio stream for every repeat.
On Bluetooth that measures "latency of a just-started A2DP stream", which is
not the latency you get during continuous playback -- and it came back with a
400ms spread across 3 repeats on the Edifier, so it cannot be trusted.

This script never restarts a stream. The engine keeps both outputs open the
whole time and we solo each speaker by MUTING the other (a gain multiply in
the callback). The mic records throughout.

Clicks are emitted on a fixed 2.0s grid on the engine timeline, so each
speaker's arrival PHASE (mod 2.0s) is directly comparable without needing any
absolute time reference. The difference between the two phases is the residual
sync error you would actually hear.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request

import numpy as np
import sounddevice as sd

API = "http://127.0.0.1:8777"
SR = 48000
PERIOD = 2.0
TRACK = os.path.expanduser("~/Projects/homesound/media/clicks-2s.wav")
SOLO_SEC = 8.0          # how long each speaker gets the floor
SETTLE_SEC = 1.0        # discard this much after a mute flip


def post(path: str, body: dict | None = None) -> dict:
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(API + path, data=data,
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=30))


def get(path: str) -> dict:
    return json.load(urllib.request.urlopen(API + path, timeout=15))


def click_template() -> np.ndarray:
    n = int(SR * 0.006)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 2200 * t) * np.exp(-t * 900.0)).astype(np.float64)


def arrival_phases(mic: np.ndarray, t_start: float) -> list[float]:
    """Return the phase (mod PERIOD, in ms) of every click heard in `mic`.

    t_start is the offset of this slice within the recording, in seconds --
    needed so phases from different slices share one clock.
    """
    ref = click_template()
    x = mic - mic.mean()
    corr = np.abs(np.correlate(x, ref, mode="valid"))
    if corr.size == 0:
        return []
    # The JBL Go 3 is ~5x quieter into the mic than the Edifier, so this has
    # to stay permissive; the 0.25s guard below is what prevents double-counts.
    floor = np.median(corr)
    thresh = max(floor * 6.0, corr.max() * 0.25)

    phases = []
    guard = int(SR * 0.25)          # one detection per 0.25s
    i = 0
    while i < len(corr):
        if corr[i] > thresh:
            j = min(i + guard, len(corr))
            peak = i + int(np.argmax(corr[i:j]))
            t_abs = t_start + peak / SR
            ph = (t_abs % PERIOD) * 1000.0
            if ph > PERIOD * 1000.0 / 2:
                ph -= PERIOD * 1000.0
            phases.append(ph)
            i = peak + guard
        else:
            i += 1
    return phases


def circ_stats(phases: list[float]) -> tuple[float, float]:
    """Median and spread, computed circularly so values near the +-1000ms
    wrap boundary don't average to nonsense."""
    if not phases:
        return float("nan"), float("nan")
    ang = np.array(phases) / (PERIOD * 1000.0) * 2 * np.pi
    m = np.arctan2(np.sin(ang).mean(), np.cos(ang).mean())
    med = m / (2 * np.pi) * PERIOD * 1000.0
    dev = [(p - med + PERIOD * 500.0) % (PERIOD * 1000.0) - PERIOD * 500.0
           for p in phases]
    return float(med), float(np.max(dev) - np.min(dev))


def main() -> int:
    st = get("/api/state")
    group = st["group"]
    if len(group) != 2:
        print(f"need exactly 2 speakers in the group, found {len(group)}")
        return 1
    a, b = group[0], group[1]
    print(f"A = {a['name']}  (trim {a['trim_ms']}ms, total {a['total_delay_ms']}ms)")
    print(f"B = {b['name']}  (trim {b['trim_ms']}ms, total {b['total_delay_ms']}ms)")

    post("/api/source/file", {"path": TRACK})
    for s in (a, b):
        post("/api/group/set", {"id": s["id"], "muted": False})
    post("/api/transport/play")

    total = SOLO_SEC * 2 + 2.0
    n = int(SR * total)
    rec = np.zeros(n, dtype=np.float32)
    pos = 0

    def cb(indata, frames, time_info, status):  # noqa: ANN001
        nonlocal pos
        end = min(pos + frames, n)
        if end > pos:
            rec[pos:end] = indata[: end - pos, 0]
        pos = end

    stream = sd.InputStream(samplerate=SR, channels=1, dtype="float32",
                            blocksize=512, callback=cb)
    stream.start()
    t0 = time.perf_counter()

    # --- solo A ---
    post("/api/group/set", {"id": b["id"], "muted": True})
    a_from = time.perf_counter() - t0
    time.sleep(SOLO_SEC)
    a_to = time.perf_counter() - t0

    # --- solo B ---
    post("/api/group/set", {"id": b["id"], "muted": False})
    post("/api/group/set", {"id": a["id"], "muted": True})
    b_from = time.perf_counter() - t0
    time.sleep(SOLO_SEC)
    b_to = time.perf_counter() - t0

    stream.stop(); stream.close()
    post("/api/transport/stop")
    post("/api/group/set", {"id": a["id"], "muted": False})

    def slice_phases(f: float, t: float) -> list[float]:
        s = int((f + SETTLE_SEC) * SR)
        e = min(int(t * SR), pos)
        if e <= s:
            return []
        return arrival_phases(rec[s:e].astype(np.float64), (f + SETTLE_SEC))

    pa = slice_phases(a_from, a_to)
    pb = slice_phases(b_from, b_to)

    print(f"\nheard {len(pa)} clicks from A, {len(pb)} from B")
    if not pa or not pb:
        print("FAILED -- turn the speakers up / move them nearer the mic.")
        return 1

    ma, sa = circ_stats(pa)
    mb, sb = circ_stats(pb)
    print(f"  A phase  {ma:8.1f} ms   jitter {sa:6.1f} ms   ({len(pa)} clicks)")
    print(f"  B phase  {mb:8.1f} ms   jitter {sb:6.1f} ms   ({len(pb)} clicks)")

    err = (mb - ma + PERIOD * 500.0) % (PERIOD * 1000.0) - PERIOD * 500.0
    print(f"\nRESIDUAL SYNC ERROR (B late by): {err:+.1f} ms")
    print(f"  worst-case jitter: {max(sa, sb):.1f} ms")
    print(f"  to correct: set {b['name']} trim to "
          f"{b['trim_ms'] - err:+.1f} ms  (currently {b['trim_ms']:+.1f})")

    if max(sa, sb) > 25:
        print("\n  WARNING: jitter alone exceeds the ~20ms echo threshold.")
        print("  A static trim cannot fix this -- the link itself is unstable.")
    elif abs(err) < 20:
        print("\n  IN SYNC -- below the ~20ms audible echo threshold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
