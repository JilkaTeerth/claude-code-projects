"""Make synthetic test tracks with a known tempo, key and structure.

Lets us check the engine (beat grid, alignment, EQ swaps) before real songs exist.
usage: python tools/synth_test.py out.wav BPM ROOT_MIDI [bars]
"""
import sys
import numpy as np
import soundfile as sf

SR = 44100


def tone(freq, dur, kind="saw"):
    t = np.arange(int(dur * SR)) / SR
    if kind == "sine":
        return np.sin(2 * np.pi * freq * t)
    # band limited-ish saw: a few harmonics
    return sum(np.sin(2 * np.pi * freq * k * t) / k for k in range(1, 8)) * 0.6


def env(n, attack=0.005, decay=0.25):
    t = np.arange(n) / SR
    return np.minimum(t / attack, 1.0) * np.exp(-t / decay)


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def make(bpm, root, bars=64):
    beat = 60.0 / bpm
    n = int(bars * 4 * beat * SR) + SR
    out = np.zeros(n)

    def add(sig, at):
        i = int(at * SR)
        out[i:i + len(sig)] += sig[: max(0, n - i)]

    # kick: pitch drop sine
    kt = np.arange(int(0.3 * SR)) / SR
    kick = np.sin(2 * np.pi * (50 + 120 * np.exp(-kt * 30)) * kt) * np.exp(-kt * 9)
    hat = np.random.default_rng(0).standard_normal(int(0.05 * SR)) * env(int(0.05 * SR), 0.001, 0.015) * 0.25

    prog = [0, -4, 3, -2]  # i VI III VII in natural minor
    for bar in range(bars):
        t0 = bar * 4 * beat
        main = 16 <= bar < 48
        chord_root = root + prog[(bar // 2) % 4]
        for b in range(4):
            add(kick * 0.9, t0 + b * beat)
            add(hat, t0 + b * beat + beat / 2)
            if main:
                # offbeat bass, one octave down from chord root
                note = tone(midi(chord_root - 12), beat / 2, "saw") * env(int(beat / 2 * SR), 0.005, 0.12)
                add(note * 0.9, t0 + b * beat + beat / 2)
        if main:
            # minor triad pad for the whole bar
            pad = sum(tone(midi(chord_root + 12 + iv), 4 * beat, "saw") for iv in (0, 3, 7))
            add(pad * env(len(pad), 0.05, 3.0) * 0.18, t0)
    out /= np.max(np.abs(out)) * 1.1
    return np.stack([out, out], axis=1)


if __name__ == "__main__":
    path, bpm, root = sys.argv[1], float(sys.argv[2]), int(sys.argv[3])
    bars = int(sys.argv[4]) if len(sys.argv) > 4 else 64
    sf.write(path, make(bpm, root, bars), SR)
    print(f"wrote {path}: {bpm} bpm, root midi {root}, {bars} bars")
