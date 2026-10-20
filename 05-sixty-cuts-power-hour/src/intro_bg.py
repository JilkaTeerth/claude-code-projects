#!/usr/bin/env python3
"""Render the blue light-streak background the reference's intro card sits on.

The source uses a stock motion background: a dark navy ground, a dozen or so
vertical light beams of varying width and brightness that drift and pulse, a
scattering of soft bokeh, and one bright horizontal bar low in the frame. None
of that is text, so it is generated here rather than in the editor, and the
card's actual wording is laid over it as live text afterwards.

Writes intro_bg.mp4, silent, 1280x720 at 30fps.
"""
import math
import subprocess
import sys

import numpy as np

W, H, FPS = 1280, 720, 30
DUR = 24.0
OUT = "intro_bg.mp4"

# beams: x position, width, base brightness, drift speed, pulse rate, phase
RNG = np.random.default_rng(11)
BEAMS = [(RNG.uniform(0, W), RNG.uniform(6, 46), RNG.uniform(0.25, 1.0),
          RNG.uniform(-9, 9), RNG.uniform(0.25, 0.9), RNG.uniform(0, 6.28))
         for _ in range(16)]
BOKEH = [(RNG.uniform(0, W), RNG.uniform(0, H), RNG.uniform(4, 13),
          RNG.uniform(0.3, 0.9), RNG.uniform(0.3, 1.1), RNG.uniform(0, 6.28))
         for _ in range(22)]

BAR_Y = 562          # the bright horizontal streak sits low in the frame


def frame(t):
    x = np.arange(W)[None, :]
    y = np.arange(H)[:, None]

    # ground: a slightly lit navy, brighter towards the middle of the frame
    g = 0.10 + 0.05 * np.exp(-(((y - H * 0.45) / (H * 0.85)) ** 2))
    r = np.zeros((H, W)) + g * 0.16
    gr = np.zeros((H, W)) + g * 0.42
    b = np.zeros((H, W)) + g * 0.86

    for bx, bw, amp, drift, rate, ph in BEAMS:
        cx = (bx + drift * t) % W
        d = np.minimum(np.abs(x - cx), W - np.abs(x - cx))
        prof = np.exp(-(d / bw) ** 2)
        lvl = amp * (0.55 + 0.45 * math.sin(2 * math.pi * rate * t + ph))
        # beams fade towards the top and bottom edges rather than running flat
        vert = 0.45 + 0.55 * np.exp(-(((y - H * 0.5) / (H * 0.75)) ** 2))
        v = prof * lvl * vert
        r += v * 0.20
        gr += v * 0.52
        b += v * 1.00

    # the bright horizontal bar, with a soft halo above and below
    bar = np.exp(-((y - BAR_Y) / 5.0) ** 2) + 0.30 * np.exp(-((y - BAR_Y) / 26.0) ** 2)
    sweep = 0.55 + 0.45 * math.sin(2 * math.pi * 0.16 * t)
    horiz = 0.35 + 0.65 * np.exp(-(((x - W * (0.30 + 0.4 * sweep)) / (W * 0.45)) ** 2))
    v = bar * horiz * 0.9
    r += v * 0.55
    gr += v * 0.80
    b += v * 1.00

    for ox, oy, rad, amp, rate, ph in BOKEH:
        d2 = ((x - ox) ** 2 + (y - oy) ** 2) / (rad ** 2)
        v = amp * np.exp(-d2) * (0.4 + 0.6 * math.sin(2 * math.pi * rate * t + ph))
        r += v * 0.35
        gr += v * 0.65
        b += v * 1.00

    # per channel gain, fitted so the ground reads the reference's measured
    # mean of (25.5, 76.1, 144.2) instead of the roughly half-bright first pass
    rgb = np.stack([r * 1.76, gr * 2.10, b * 2.15], axis=-1)
    return (np.clip(rgb, 0, 1) * 255).astype(np.uint8)


def main():
    n = int(DUR * FPS)
    p = subprocess.Popen(
        ["ffmpeg", "-nostdin", "-y", "-v", "error",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-framerate", str(FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
         "-pix_fmt", "yuv420p", "-r", str(FPS), OUT],
        stdin=subprocess.PIPE)
    for i in range(n):
        p.stdin.write(frame(i / FPS).tobytes())
        if i % 120 == 0:
            print(f"  {i/FPS:5.1f}s / {DUR:.0f}s", flush=True)
    p.stdin.close()
    if p.wait() != 0:
        raise SystemExit("ffmpeg failed")
    print(f"wrote {OUT}  ({DUR:.0f}s)")


if __name__ == "__main__":
    sys.exit(main())
