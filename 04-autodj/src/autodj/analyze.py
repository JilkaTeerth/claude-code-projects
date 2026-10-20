"""Ears: turn an audio file into the numbers a DJ hears.

Output per track: bpm, a constant tempo beat grid, downbeats (bar starts), key and
Camelot code, per bar energy, and phrase-level sections. Saved as JSON so the
Brain (Claude) can read it and plan transitions.
"""
import json
import sys
from pathlib import Path

import librosa
import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100

# Krumhansl-Kessler key profiles
MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
# Camelot number for each pitch class
CAMELOT_MAJOR = {0: 8, 7: 9, 2: 10, 9: 11, 4: 12, 11: 1, 6: 2, 1: 3, 8: 4, 3: 5, 10: 6, 5: 7}
CAMELOT_MINOR = {9: 8, 4: 9, 11: 10, 6: 11, 1: 12, 8: 1, 3: 2, 10: 3, 5: 4, 0: 5, 7: 6, 2: 7}


def load(path):
    y, _ = librosa.load(path, sr=SR, mono=False)
    if y.ndim == 1:
        y = np.stack([y, y])
    return y.T  # (samples, channels)


def fit_grid(beat_times):
    """Least squares line through beat times -> steady period and phase."""
    idx = np.arange(len(beat_times))
    period, offset = np.polyfit(idx, beat_times, 1)
    for _ in range(3):
        resid = np.abs(beat_times - (offset + period * idx))
        keep = resid < max(0.03, np.percentile(resid, 60))
        period, offset = np.polyfit(idx[keep], beat_times[keep], 1)
    # pull offset back to the first beat at or after 0
    offset = offset - np.floor(offset / period) * period
    return period, offset


def detect_key(mono):
    # ignore the kick/sub so it does not smear the pitch picture
    harm = librosa.effects.harmonic(sosfilt(butter(4, 120, "high", fs=SR, output="sos"), mono))
    chroma = librosa.feature.chroma_cqt(y=harm, sr=SR, hop_length=4096).mean(axis=1)
    best = (-2, None, None)
    for tonic in range(12):
        for mode, prof in (("major", MAJOR), ("minor", MINOR)):
            r = np.corrcoef(chroma, np.roll(prof, tonic))[0, 1]
            if r > best[0]:
                best = (r, tonic, mode)
    r, tonic, mode = best
    num = (CAMELOT_MAJOR if mode == "major" else CAMELOT_MINOR)[tonic]
    return {
        "key": f"{NAMES[tonic]} {mode}",
        "camelot": f"{num}{'B' if mode == 'major' else 'A'}",
        "confidence": round(float(r), 3),
    }


def analyze(path):
    y = load(path)
    mono = y.mean(axis=1)
    dur = len(mono) / SR

    _, beats = librosa.beat.beat_track(y=mono, sr=SR, units="time", tightness=400)
    period, offset = fit_grid(beats)
    if 60 / period < 80:  # half time read on a dance track
        period /= 2

    # the tracker often locks onto offbeats (hats, offbeat bass), so re-pick the grid
    # offset as the one where low end onsets (kicks) line up best
    low = sosfilt(butter(4, 150, "low", fs=SR, output="sos"), mono)
    low_onset = librosa.onset.onset_strength(y=low, sr=SR, hop_length=128)
    def kick_score(off):
        fr = librosa.time_to_frames(np.arange(off, dur, period), sr=SR, hop_length=128)
        return low_onset[fr.clip(0, len(low_onset) - 1)].mean()
    offset = max(np.arange(0, period, 0.003), key=kick_score)
    grid = np.arange(offset, dur, period)
    low_onset = librosa.onset.onset_strength(y=low, sr=SR, hop_length=512)
    chroma = librosa.feature.chroma_stft(y=mono, sr=SR, hop_length=512)
    frames = librosa.time_to_frames(grid, sr=SR, hop_length=512).clip(0, len(low_onset) - 1)

    def norm(x):
        return x / (x.max() + 1e-9)

    # kick strength: peak onset in a small window after each beat
    kick = np.array([low_onset[f:f + 4].max() for f in frames])
    # harmony change: chroma of the beat vs the beat before (chords move on the one)
    bsync = librosa.util.sync(chroma, frames, aggregate=np.mean)
    bsync = bsync / (bsync.sum(axis=0, keepdims=True) + 1e-9)
    change = np.r_[0, np.linalg.norm(np.diff(bsync, axis=1), axis=0)]
    change = change[: len(grid)] if len(change) >= len(grid) else np.r_[change, np.zeros(len(grid) - len(change))]
    strength = 0.5 * norm(kick) + norm(change)
    phase = int(np.argmax([strength[p::4].mean() for p in range(4)]))
    downbeats = grid[phase::4]

    # per bar energy and features for section finding
    bars = []
    feats = []
    for i, t in enumerate(downbeats[:-1]):
        a, b = int(t * SR), int(downbeats[i + 1] * SR)
        seg, lseg = mono[a:b], low[a:b]
        rms = float(np.sqrt(np.mean(seg ** 2)) + 1e-9)
        lrms = float(np.sqrt(np.mean(lseg ** 2)) + 1e-9)
        c = chroma[:, a // 512:b // 512].mean(axis=1)
        bars.append({"bar": i, "t": round(float(t), 3),
                     "db": round(20 * np.log10(rms), 1), "low_db": round(20 * np.log10(lrms), 1)})
        # energy in 2 dB units dominates; chroma only nudges (chords cycle inside a section)
        feats.append(np.r_[20 * np.log10(rms) / 2, 20 * np.log10(lrms) / 2, c / (c.sum() + 1e-9)])
    feats = np.array(feats)

    # novelty between the 8 bars (one pop phrase) before and after each bar
    nov = np.zeros(len(feats))
    for i in range(2, len(feats) - 2):
        w = min(8, i, len(feats) - i)
        nov[i] = np.linalg.norm(feats[i:i + w].mean(0) - feats[i - w:i].mean(0))
    inner = nov[4:-8] if len(nov) > 16 else nov
    thresh = np.median(inner) * 1.5
    peaks = [i for i in range(4, len(nov) - 6)
             if nov[i] > thresh and nov[i] >= nov[max(0, i - 3):i + 4].max()]
    # songs often start with a pickup bar, so learn which bar (mod 4) phrases start on
    votes = np.zeros(4)
    for i in peaks:
        votes[i % 4] += nov[i]
    phrase_offset = int(np.argmax(votes)) if peaks else 0
    snapped = sorted({min(range(i - 2, i + 3), key=lambda j: (j % 4 != phrase_offset, abs(j - i)))
                      for i in peaks})
    bounds = [0] + [b for b in snapped if 0 < b < len(feats)]
    bounds.append(len(feats))
    loud = np.median([b["db"] for b in bars])
    sections = []
    for s, e in zip(bounds[:-1], bounds[1:]):
        db = float(np.mean([b["db"] for b in bars[s:e]]))
        low_db = float(np.mean([b["low_db"] for b in bars[s:e]]))
        sections.append({"start_bar": s, "end_bar": e, "bars": e - s,
                         "t": bars[s]["t"], "energy_db": round(db, 1), "low_db": round(low_db, 1),
                         "label": "high" if db >= loud else "low"})

    return {
        "file": str(Path(path).resolve()),
        "duration": round(dur, 2),
        "bpm": round(60 / period, 2),
        "beat_period": period,
        "first_downbeat": round(float(downbeats[0]), 4),
        "n_bars": len(bars),
        "phrase_offset": phrase_offset,
        **detect_key(mono),
        "sections": sections,
        "novelty": [round(float(x), 3) for x in nov],
        "bars": bars,
    }


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent.parent / "analysis"
    out_dir.mkdir(exist_ok=True)
    for p in sys.argv[1:]:
        a = analyze(p)
        out = out_dir / (Path(p).stem + ".json")
        out.write_text(json.dumps(a, indent=1))
        secs = ", ".join(f"{s['start_bar']}-{s['end_bar']} {s['label']}" for s in a["sections"])
        print(f"{Path(p).name}: {a['bpm']} bpm, {a['key']} ({a['camelot']}), "
              f"{a['n_bars']} bars, first downbeat {a['first_downbeat']}s | {secs}")
