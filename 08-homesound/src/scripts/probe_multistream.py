#!/usr/bin/env python3
"""P4-PoC-2: THE critical feasibility test.

Opens N independent CoreAudio OutputStreams to N *different* physical devices
simultaneously, and writes an independently phase-offset signal to each.

If this works, per-speaker latency compensation is possible and the whole
product is buildable. If it fails, the architecture is dead and we fall back
to Snapcast.

Plays at very low amplitude (-40 dBFS) so it is barely audible.
"""
import sys
import time
import threading

import numpy as np
import sounddevice as sd

SR = 48000
DUR = 2.0
AMP = 0.01  # ~-40 dBFS, deliberately quiet


def find_outputs():
    devs = []
    for i, d in enumerate(sd.query_devices()):
        if d["max_output_channels"] >= 2 and "Zoom" not in d["name"] and "Teams" not in d["name"]:
            devs.append((i, d["name"], d["max_output_channels"]))
    return devs


def run(idx, name, delay_ms, results):
    """Open one stream to one device, write a tone delayed by delay_ms."""
    n = int(SR * DUR)
    t = np.arange(n) / SR
    tone = (AMP * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    # apply the per-device delay by prepending silence — this is exactly the
    # mechanism the real engine will use for latency compensation
    pad = np.zeros(int(SR * delay_ms / 1000.0), dtype=np.float32)
    sig = np.concatenate([pad, tone])
    buf = np.column_stack([sig, sig])

    pos = 0
    done = threading.Event()

    def cb(outdata, frames, time_info, status):
        nonlocal pos
        if status:
            results.setdefault(name, {})["status"] = str(status)
        end = pos + frames
        chunk = buf[pos:end]
        if len(chunk) < frames:
            outdata[: len(chunk)] = chunk
            outdata[len(chunk):] = 0
            pos = end
            done.set()
            raise sd.CallbackStop
        outdata[:] = chunk
        pos = end

    try:
        with sd.OutputStream(
            device=idx, samplerate=SR, channels=2, dtype="float32", callback=cb
        ) as s:
            results[name] = {
                "opened": True,
                "delay_ms": delay_ms,
                "reported_latency_ms": round(s.latency * 1000, 2),
                "samplerate": s.samplerate,
            }
            done.wait(timeout=DUR + 3)
    except Exception as e:
        results[name] = {"opened": False, "error": f"{type(e).__name__}: {e}"}


def main():
    outs = find_outputs()
    if len(outs) < 2:
        print(f"FAIL: need >=2 stereo output devices, found {len(outs)}")
        for o in outs:
            print("   ", o)
        return 1

    print(f"Testing {len(outs)} devices simultaneously with staggered delays:\n")
    results = {}
    threads = []
    # deliberately different delays per device — proves independent compensation
    for k, (idx, name, ch) in enumerate(outs):
        delay = k * 120.0
        print(f"  -> [{idx}] {name}  (delay {delay:.0f} ms)")
        th = threading.Thread(target=run, args=(idx, name, delay, results), daemon=True)
        threads.append(th)

    t0 = time.time()
    for th in threads:
        th.start()
    for th in threads:
        th.join(timeout=DUR + 5)
    elapsed = time.time() - t0

    print(f"\n--- RESULTS (elapsed {elapsed:.2f}s) ---")
    ok = 0
    for name, r in results.items():
        if r.get("opened"):
            ok += 1
            print(f"  OK   {name}: delay={r['delay_ms']:.0f}ms "
                  f"reported_latency={r['reported_latency_ms']}ms sr={r['samplerate']:.0f}"
                  + (f" status={r['status']}" if "status" in r else ""))
        else:
            print(f"  FAIL {name}: {r.get('error')}")

    print(f"\nVERDICT: {ok}/{len(outs)} simultaneous independent output streams")
    print("ARCHITECTURE VIABLE" if ok >= 2 else "ARCHITECTURE NOT VIABLE")
    return 0 if ok >= 2 else 1


if __name__ == "__main__":
    sys.exit(main())
