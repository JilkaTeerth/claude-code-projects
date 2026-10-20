"""Judge: score every transition before a human listens.

Checks, per transition:
  beat_offset_ms  how far B's kicks sit from A's in the overlap (want < 10 ms)
  bass_clash      share of the overlap where both basslines are up at once (want ~0)
  lufs_jump       loudness 8 s before vs 8 s after (want < 1.5 dB)
  key_step        Camelot distance (0 or 1 is safe, 2 is a deliberate energy move)
and saves a spectrogram of each transition so the bass handoff is visible.
"""
import re
from pathlib import Path

import librosa
import librosa.display
import matplotlib
import numpy as np
import pyloudnorm as pyln
from scipy.signal import butter, sosfiltfilt

from .analyze import SR

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BLENDS = {"bass_swap", "filter_blend", "stem_swap", "loop_bridge"}  # techniques where both beats play together


def camelot_step(a, b):
    na, la = int(re.match(r"\d+", a).group()), a[-1]
    nb, lb = int(re.match(r"\d+", b).group()), b[-1]
    d = min((na - nb) % 12, (nb - na) % 12)
    return d + (1 if la != lb and d else 0) if la != lb else d


def onset_env(x):
    low = sosfiltfilt(butter(4, 150, "low", fs=SR, output="sos"), x.mean(axis=1))
    return librosa.onset.onset_strength(y=low, sr=SR, hop_length=64)


def beat_offset_ms(A, B, ts, te, confidence=False):
    """Cross correlate the raw (unautomated) kick onsets of both tracks in the overlap."""
    a = A.audio[A.idx(A.local(ts)):A.idx(A.local(te))]
    b = B.audio[B.idx(B.local(ts)):B.idx(B.local(te))]
    n = min(len(a), len(b))
    if n < SR:
        return None
    ea, eb = onset_env(a[:n]), onset_env(b[:n])
    ea, eb = ea - ea.mean(), eb - eb.mean()  # zero mean, or every lag correlates about the same
    max_lag = int(0.08 * SR / 64)
    lags = range(-max_lag, max_lag + 1)
    corr = np.array([np.dot(ea[max(0, l):len(ea) + min(0, l)], eb[max(0, -l):len(eb) - max(0, l)])
                     for l in lags])
    lag = round(lags[int(np.argmax(corr))] * 64 / SR * 1000, 1)
    if confidence:
        # a real kick lock gives one sharp peak; no drums in either track gives a flat curve
        # normalised correlation at the peak: ~0 means no shared pulse, > 0.3 is a clear lock
        return lag, float(corr.max() / (np.linalg.norm(ea) * np.linalg.norm(eb) + 1e-9))
    return lag


def bass_clash(A, B, ts, te):
    ia = slice(A.idx(A.local(ts)), A.idx(A.local(te)))
    ib = slice(B.idx(B.local(ts)), B.idx(B.local(te)))
    n = min(ia.stop - ia.start, ib.stop - ib.start)
    if n <= 0:
        return 0.0
    both = (A.g["bass"][ia][:n] > 0.35) & (B.g["bass"][ib][:n] > 0.35)
    return round(float(both.mean()), 3)


def vocal_clash(A, B, ts, te):
    """Bars (of the overlap, plus 2 after) where both songs have an audible lead vocal.
    Uses the vocal stem map (how much singing is in that bar) times the vocal fader."""
    bad = []
    t = ts - A.bar_len  # include the bar before, catches a B vocal coming in early
    while t < te + 2 * A.bar_len:
        def level(T):
            k = int(np.floor((T.local(t) - T.first_db) / T.bar_len + 1e-6))
            i0, i1 = T.idx(T.local(t)), T.idx(T.local(t + A.bar_len))
            fader = float(T.g["vocals"][i0:i1].mean()) if i1 > i0 else 0.0
            return fader * T.vocal_level(k)
        if level(A) > 0.25 and level(B) > 0.25:
            bad.append(round(t, 1))
        t += A.bar_len
    return bad


def lufs(mix, t0, t1):
    seg = mix[max(0, int(t0 * SR)):int(t1 * SR)]
    if len(seg) < SR:
        return None
    return pyln.Meter(SR).integrated_loudness(seg)


def judge(mix, events, name):
    out_dir = ROOT / "mixes" / f"{name}_judge"
    out_dir.mkdir(parents=True, exist_ok=True)
    report = []
    for k, (tr, A, B, ts, te) in enumerate(events):
        before, after = lufs(mix, ts - 8, ts), lufs(mix, te, te + 8)
        r = {
            "n": k + 1, "from": A.id, "to": B.id, "technique": tr["technique"],
            "beat_offset_ms": (beat_offset_ms(A, B, ts, te)
                               if tr["technique"] in BLENDS and te - ts > 1 else None),
            "bass_clash": bass_clash(A, B, ts, te),
            "vocal_clash_bars": len(vocal_clash(A, B, ts, te)),
            "lufs_jump": round(abs(after - before), 2) if before and after else None,
            "key_step": camelot_step(A.a["camelot"], B.a["camelot"]),
            "tempo_stretch_pct": round(max(abs(A.ratio - 1), abs(B.ratio - 1)) * 100, 1),
        }
        flags = []
        lock = beat_offset_ms(A, B, ts, te, confidence=True) if tr["technique"] in BLENDS and te - ts > 1 else None
        r["shared_pulse"] = round(lock[1], 2) if lock else None
        if lock and lock[1] < 0.15:
            r["beat_offset_ms"] = None  # one side has no drums here, nothing to flam
        if r["beat_offset_ms"] is not None and abs(r["beat_offset_ms"]) > 10:
            flags.append("beats drift")
        if r["vocal_clash_bars"]:
            flags.append(f"TWO VOCALS for {r['vocal_clash_bars']} bars")
        if r["bass_clash"] > 0.05:
            flags.append("two basslines")
        if r["lufs_jump"] and r["lufs_jump"] > 2.0:
            flags.append("volume jump")
        if r["key_step"] >= 2 and tr["technique"] not in ("echo_out", "cut"):
            flags.append("key clash")
        if r["tempo_stretch_pct"] > 8:
            flags.append("heavy stretch")
        r["verdict"] = "clean" if not flags else ", ".join(flags)
        report.append(r)

        # spectrogram: 4 s either side of the overlap, low end on a log axis
        seg = mix[max(0, int((ts - 4) * SR)):int((te + 4) * SR)].mean(axis=1)
        S = librosa.amplitude_to_db(np.abs(librosa.stft(seg, n_fft=4096, hop_length=1024)), ref=np.max)
        fig, ax = plt.subplots(figsize=(10, 3.2))
        librosa.display.specshow(S, sr=SR, hop_length=1024, x_axis="time", y_axis="log", ax=ax, cmap="magma")
        ax.axvline(4, color="w", lw=1, ls="--")
        ax.axvline(4 + te - ts, color="w", lw=1, ls="--")
        ax.set_title(f"{k + 1}. {A.id} -> {B.id}  ({tr['technique']})  {r['verdict']}")
        fig.tight_layout()
        fig.savefig(out_dir / f"{k + 1:02d}_{tr['technique']}.png", dpi=110)
        plt.close(fig)
    return report


def print_report(report):
    for r in report:
        print(f"  {r['n']}. {r['from']} -> {r['to']} [{r['technique']}] "
              f"beat {r['beat_offset_ms']} ms | vocal clash {r['vocal_clash_bars']} bars | bass clash {r['bass_clash']:.0%} | "
              f"lufs jump {r['lufs_jump']} | key step {r['key_step']} | "
              f"stretch {r['tempo_stretch_pct']}% => {r['verdict']}")
