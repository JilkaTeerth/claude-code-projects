"""Read a song like a DJ: is the grid right, where are the phrases, what is each part.

Three layers, each a pure reader of analysis/, lyrics/ and stems/ (nothing in the core
pipeline is changed; corrections are reported, and applied only inside the skills):

1. verify(stem)  cross-checks the beat grid, the downbeat (which beat is "the one") and
   the phrase grid against three independent witnesses:
     - the drum stem (kicks on the grid, drums entering on a downbeat),
     - the lyrics (sung lines start on the one or on a pickup just before it),
     - harmony (chords change on the one).
   Reports per song confidence, local tempo problems (skits, tempo changes, half time
   sections) and suggested corrections.
2. phrases(stem) finds the real phrase lines with a dynamic programme over bars that
   prefers 8 bar blocks but lets the evidence insert the odd 2 / 4 / 6 bar block
   (pickups, extra bars, skits), instead of one global "bar mod 4" offset.
3. label(stem) names every phrase block: intro / verse / pre-chorus / chorus / post-chorus /
   drop / build / breakdown / bridge / outro / talk, from lyric repetition (hooks),
   the vocal map and energy.

usage:
  python -m autodj.skills.structure verify [name_filter]
  python -m autodj.skills.structure label [name_filter]
  python -m autodj.skills.structure all          # verify + label, writes analysis/structure/*.json
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "analysis" / "structure"
SR2 = 22050
HOP = 256


# ---------------------------------------------------------------- loading

def song_list():
    return sorted(p.stem for p in (ROOT / "lyrics").glob("*.json")
                  if (ROOT / "analysis" / f"{p.stem}.json").exists())


def load_analysis(stem):
    return json.loads((ROOT / "analysis" / f"{stem}.json").read_text())


def load_words(stem):
    p = ROOT / "lyrics" / f"{stem}.json"
    if not p.exists():
        return [], []
    from ..lyrics import clean_words
    lyr = json.loads(p.read_text())
    return clean_words(lyr["words"]), lyr["lines"]


def _mono(path):
    import librosa
    import soundfile as sf
    y, sr = sf.read(path, dtype="float32", always_2d=True)
    return librosa.resample(y.mean(axis=1), orig_sr=sr, target_sr=SR2)


def features(stem):
    """Drum onset envelope, per frame drum / vocal / mix loudness and a chroma of the
    harmonic stems. Cached, because decoding 3 stems per song is the slow part."""
    import librosa
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{stem}.npz"
    if f.exists():
        return dict(np.load(f))
    sd = ROOT / "stems" / stem
    drums = _mono(sd / "drums.flac")
    vocals = _mono(sd / "vocals.flac")
    harm = _mono(sd / "other.flac") + _mono(sd / "bass.flac")
    n = min(len(drums), len(vocals), len(harm))
    drums, vocals, harm = drums[:n], vocals[:n], harm[:n]
    env = librosa.onset.onset_strength(y=drums, sr=SR2, hop_length=HOP)
    from scipy.signal import butter, sosfiltfilt
    kick = sosfiltfilt(butter(4, 150, "low", fs=SR2, output="sos"), drums)
    kenv = librosa.onset.onset_strength(y=kick, sr=SR2, hop_length=HOP)
    rms = lambda x: 20 * np.log10(librosa.feature.rms(y=x, frame_length=2048, hop_length=HOP)[0] + 1e-6)
    chroma = librosa.feature.chroma_stft(y=harm, sr=SR2, hop_length=HOP * 4)
    out = {"drum_env": env.astype(np.float32), "kick_env": kenv.astype(np.float32), "drum_db": rms(drums).astype(np.float32),
           "vocal_db": rms(vocals).astype(np.float32), "mix_db": rms(drums + vocals + harm).astype(np.float32),
           "chroma": chroma.astype(np.float32)}
    np.savez_compressed(f, **out)
    return out


def frame(t, hop=HOP):
    return int(round(t * SR2 / hop))


def sung_lines(words, wlines, beat):
    """Group words into sung lines: a new line after a breath (gap) or at a whisper
    segment start that also has a small gap. Each line carries the gap before it."""
    seg_starts = {round(l["start"], 2) for l in wlines}
    lines, cur = [], None
    for w in words:
        gap = w["start"] - cur["end"] if cur else 99.0
        if cur is None or gap >= max(0.3, 0.55 * beat) or (round(w["start"], 2) in seg_starts and gap > 0.12):
            if cur:
                lines.append(cur)
            cur = {"start": w["start"], "end": w["end"], "gap": gap, "words": [w["w"]]}
        else:
            cur["end"] = max(cur["end"], w["end"])
            cur["words"].append(w["w"])
    if cur:
        lines.append(cur)
    for l in lines:
        l["text"] = " ".join(l["words"])
    return lines


# ---------------------------------------------------------------- 1. grid verifier

def _seg_mean(x, t0, t1, hop=HOP):
    a, b = frame(t0, hop), frame(t1, hop)
    a, b = max(0, a), min(len(x), max(a + 1, b))
    return float(x[a:b].mean()) if b > a else float("nan")


def grid_lock(a, F, window_bars=8):
    """Per 8 bar window: how well the drum stem's onsets sit on the grid, the best local
    shift (ms) and the window's dominant tempo. Drifts and off tempo stretches show up here."""
    import librosa
    bp, f = a["beat_period"], a["first_downbeat"]
    # the kick alone locks better on remixes whose drum stem is mostly 16th note hats
    env = F["drum_env"] / (F["drum_env"].std() + 1e-9) + F["kick_env"] / (F["kick_env"].std() + 1e-9)
    drum_db = F["drum_db"]
    loud = np.percentile(drum_db, 90)
    tg = librosa.feature.tempogram(onset_envelope=env, sr=SR2, hop_length=HOP, win_length=768)
    bpms = librosa.tempo_frequencies(tg.shape[0], sr=SR2, hop_length=HOP)
    ok = (bpms > 60) & (bpms < 200)
    out = []
    for k in range(0, a["n_bars"], window_bars):
        t0 = f + 4 * k * bp
        t1 = t0 + 4 * window_bars * bp
        i0, i1 = frame(t0), min(len(env), frame(t1))
        if i1 - i0 < 50:
            break
        seg = env[i0:i1]
        level = _seg_mean(drum_db, t0, t1) - loud
        active = level > -18
        best, shift = -9.0, 0.0
        if seg.std() > 1e-6:
            z = (seg - seg.mean()) / seg.std()
            for sh in np.arange(-0.07, 0.0701, 0.002):
                fr = np.round((np.arange(4 * window_bars) * bp + sh) * SR2 / HOP).astype(int)
                fr = fr[(fr >= 0) & (fr < len(z))]
                sc = float(z[fr].mean()) if len(fr) else -9
                if sc > best:
                    best, shift = sc, sh
        local = tg[:, i0:i1].mean(axis=1)
        lbpm = float(bpms[ok][np.argmax(local[ok])])
        r = lbpm / a["bpm"]
        octave_err = min(abs(np.log2(r / m)) for m in (1, 2, 0.5, 1.5, 2 / 3, 4 / 3, 0.75))
        on_tempo = min(abs(np.log2(r / m)) for m in (1, 2, 0.5)) < 0.025
        out.append({"bar": k, "active": bool(active), "level_db": round(level, 1), "lock": round(best, 2), "shift_ms": round(shift * 1000),
                    "local_bpm": round(lbpm, 1), "on_tempo": bool(on_tempo or octave_err < 0.02 and best > 1.0)})
    return out


def usable_bars(a, lock):
    """Longest stretch of bars whose drums sit on the grid (windows without drums count as
    usable only if they are between good windows). Off tempo windows end the stretch."""
    good = []
    for w in lock:
        heard = w["level_db"] > -30  # some drums: enough for a wrong tempo to be audible
        off = not w["on_tempo"] and (w["lock"] < 0.6 or w["active"]) and heard
        bad = off or (w["active"] and w["lock"] < 0.3)
        good.append(not bad)
    best, cur, start = (0, 0), 0, 0
    for i, g in enumerate(good + [False]):
        if g:
            if cur == 0:
                start = i
            cur += 1
            if cur > best[1] - best[0]:
                best = (start, i + 1)
        else:
            cur = 0
    wb = lock[1]["bar"] - lock[0]["bar"] if len(lock) > 1 else 8
    lo, hi = best[0] * wb, min(a["n_bars"], best[1] * wb)
    return lo, hi, good


def _beat_series(x, a, n_beats, offset_beats=0.0, hop=HOP):
    bp, f = a["beat_period"], a["first_downbeat"]
    return np.array([_seg_mean(x, f + (j + offset_beats) * bp, f + (j + 1 + offset_beats) * bp, hop)
                     for j in range(n_beats)])


def downbeat_votes(a, F, lines, goodbar):
    """Which of the 4 beats is really the one, by three independent witnesses.
    Phase p means: the true downbeat is p beats after the analysis' downbeat.
    Only bars where the grid is trustworthy (goodbar) vote."""
    bp, f = a["beat_period"], a["first_downbeat"]
    n_beats = 4 * a["n_bars"]
    ok_bar = lambda k: 0 <= k < len(goodbar) and goodbar[k]

    # lyrics: line starts land on the one, or a pickup up to ~1.5 beats before it
    hits = np.full(4, 0.5)
    n_l = 0
    for l in lines:
        if not ok_bar(int((l["start"] - f) // (4 * bp))) or l["gap"] < 0.9 * bp:
            continue
        u = (l["start"] - f) / bp
        w = min(1.0, l["gap"] / (2 * bp))
        n_l += 1
        for p in range(4):
            x = ((u - p + 2) % 4) - 2
            if -0.6 <= x <= 0.3:
                hits[p] += w
            elif -1.6 <= x < -0.6:
                hits[p] += 0.6 * w
    L = hits / hits.sum()

    # drums: the biggest drum entrances (drops, beat coming back) happen on the one
    ddb = _beat_series(F["drum_db"], a, n_beats)
    jumps = np.full(4, 0.5)
    n_d = 0
    cand = []
    for j in range(5, n_beats - 4):
        if not ok_bar(j // 4):
            continue
        # 'before' skips the beat right before: a fill or snare roll there is a pickup, not the one
        d = np.nanmean(ddb[j:j + 4]) - np.nanmean(ddb[j - 5:j - 1])
        if d > 6 and ddb[j] - ddb[j - 1] > 3:
            cand.append((d, j))
    taken = []
    for d, j in sorted(cand, reverse=True):
        if all(abs(j - t) >= 8 for t in taken):
            taken.append(j)
            jumps[j % 4] += min(d / 10, 2.0)
            n_d += 1
        if len(taken) >= 16:
            break
    D = jumps / jumps.sum()

    # harmony: chord changes on the one
    ch = F["chroma"]
    beat_ch = np.stack([ch[:, max(0, frame(f + j * bp, HOP * 4)):max(1, frame(f + (j + 1) * bp, HOP * 4))].mean(axis=1)
                        if frame(f + (j + 1) * bp, HOP * 4) <= ch.shape[1] else np.zeros(12)
                        for j in range(n_beats)], axis=1)
    beat_ch = beat_ch / (beat_ch.sum(axis=0, keepdims=True) + 1e-9)
    change = np.r_[0, np.linalg.norm(np.diff(beat_ch, axis=1), axis=0)]
    sel = np.array([j for j in range(n_beats) if ok_bar(j // 4)] or list(range(n_beats)))
    m = np.array([change[sel[sel % 4 == p]].mean() for p in range(4)])
    z = (m - m.mean()) / (m.std() + 1e-9)
    H = np.exp(z) / np.exp(z).sum()

    # lyrics are the weakest witness at beat level (pickups vary, whisper timing is +-0.2 beat);
    # they matter more for which BAR a phrase starts on. Harmony from the stems is strong.
    wL = 0.5 if n_l >= 6 else 0.2
    wD = 1.0 if n_d >= 3 else 0.4
    wH = 1.0
    logp = wL * np.log(L) + wD * np.log(D) + wH * np.log(H)
    post = np.exp(logp - logp.max())
    post /= post.sum()
    return {"posterior": [round(float(x), 3) for x in post],
            "lyrics": [round(float(x), 3) for x in L], "drums": [round(float(x), 3) for x in D],
            "harmony": [round(float(x), 3) for x in H], "n_lines": n_l, "n_drum_jumps": n_d}


# ---------------------------------------------------------------- 2. phrase grid

def bar_evidence(a, F, lines, phase=0):
    """How strongly each bar line looks like the start of a phrase."""
    bp = a["beat_period"]
    f = a["first_downbeat"] + phase * bp
    n = a["n_bars"]
    bt = lambda k: f + 4 * k * bp
    ev = np.zeros(n + 1)
    why = [[] for _ in range(n + 1)]
    # sung lines starting on (or a pickup before) the bar, bigger after a long breath
    for l in lines:
        u = (l["start"] - f) / (4 * bp)
        k = int(round(u))
        x = (l["start"] - bt(k)) / bp
        if 0 <= k <= n and -1.6 <= x <= 0.35:
            w = min(1.0, l["gap"] / (2 * bp))
            ev[k] += 0.6 * w + (0.8 if l["gap"] >= 3 * bp else 0)
    # per bar loudness of drums, vocals and the whole mix
    dd = np.array([_seg_mean(F["drum_db"], bt(k), bt(k + 1)) for k in range(n)])
    vd = np.array([_seg_mean(F["vocal_db"], bt(k), bt(k + 1)) for k in range(n)])
    md = np.array([_seg_mean(F["mix_db"], bt(k), bt(k + 1)) for k in range(n)])
    vref = np.nanpercentile(vd, 90)
    sing = vd > vref - 14
    for k in range(2, n - 1):
        for x, scale, name in ((dd, 6.0, "drums"), (md, 4.0, "energy")):
            d = np.nanmean(x[k:k + 2]) - np.nanmean(x[k - 2:k])
            if abs(d) > 2:
                ev[k] += min(abs(d) / scale, 1.5)
                why[k].append(f"{name} {d:+.0f}dB")
        if sing[k] and not sing[k - 1] and not sing[max(0, k - 2)]:
            ev[k] += 1.0
            why[k].append("vocal in")
        if not sing[k] and sing[k - 1]:
            ev[k] += 0.6
            why[k].append("vocal out")
    # harmonic novelty from the core analysis (computed on its own downbeats)
    nov = np.array(a.get("novelty", [0] * n) + [0])[: n + 1]
    if nov.max() > 0:
        ev += 0.8 * nov / nov.max()
    return ev, why, {"drum_db": dd, "vocal_db": vd, "mix_db": md, "sing": sing}


SEG_PEN = {8: 0.0, 4: 0.45, 16: 0.25, 12: 0.9, 2: 1.6, 6: 1.4, 10: 1.8, 14: 1.8, 1: 3.0, 3: 2.6, 5: 2.6, 7: 2.4}
BOUNDARY_COST = 0.7


def phrase_dp(ev, n):
    """Best split of bars 0..n into phrase blocks. Blocks of 8 are free, 4 and 16 cheap, odd
    sizes expensive; each boundary earns its evidence minus a fixed cost. The first block can
    be any length (pickup bars, intros), and so can the last (fade, cut-off video)."""
    best = np.full(n + 1, -1e9)
    prev = np.zeros(n + 1, dtype=int)
    best[0] = 0
    for k in range(1, n + 1):
        gain = (ev[k] - BOUNDARY_COST) if k < n else 0.0
        for L, pen in SEG_PEN.items():
            j = k - L
            if j < 0:
                continue
            s = best[j] + gain - pen
            if s > best[k]:
                best[k], prev[k] = s, j
        if k <= 12:  # free form first block
            s = gain - 0.8 - 0.1 * abs(k - 8)
            if s > best[k]:
                best[k], prev[k] = s, 0
        if k == n:  # free form last block
            for j in range(max(0, n - 16), n):
                s = best[j] - 0.5
                if s > best[k]:
                    best[k], prev[k] = s, j
    bounds = [n]
    while bounds[-1] > 0:
        bounds.append(prev[bounds[-1]])
    return sorted(int(b) for b in set(bounds))


# ---------------------------------------------------------------- 3. verify (glue)

def _env(F):
    return F["drum_env"] / (F["drum_env"].std() + 1e-9) + F["kick_env"] / (F["kick_env"].std() + 1e-9)


def refit_grid(a, F, span=0.03):
    """Re-fit tempo and phase of the constant grid on the drum stem (kick + drum onsets),
    over the bars where drums play. The core analysis fits beat tracker output, which on
    remixes with half time drums lands 1 % off and drifts a beat per minute."""
    env = _env(F)
    fps = SR2 / HOP
    dd = F["drum_db"]
    loud = np.percentile(dd, 90)
    t_all = np.arange(len(env)) / fps
    weight = (dd[: len(env)] > loud - 18).astype(float) if len(dd) >= len(env) else np.ones(len(env))
    dur = len(env) / fps

    def score(per, offs):
        beats = np.arange(0, dur - per, per)
        idx = np.round((offs[:, None] + beats[None, :]) * fps).astype(int).clip(0, len(env) - 1)
        w = weight[idx]
        return (env[idx] * w).sum(axis=1) / (w.sum(axis=1) + 1e-9)

    bp = a["beat_period"]
    f0 = a["first_downbeat"] % bp
    s_old = float(score(bp, np.array([f0]))[0])
    best = (s_old, bp, f0)
    for per in bp * np.linspace(1 - span, 1 + span, 241):
        offs = np.arange(0, per, 0.004)
        sc = score(per, offs)
        i = int(np.argmax(sc))
        if sc[i] > best[0]:
            best = (float(sc[i]), per, float(offs[i]))
    _, per0, off0 = best
    for per in per0 * np.linspace(0.9993, 1.0007, 57):
        offs = np.arange(off0 - 0.012, off0 + 0.012, 0.001) % per
        sc = score(per, offs)
        i = int(np.argmax(sc))
        if sc[i] > best[0]:
            best = (float(sc[i]), per, float(offs[i]))
    s_new, per, off = best
    # keep the downbeat on the grid beat nearest to the old one
    fd = a["first_downbeat"]
    k = round((fd - off) / per)
    first = off + k * per
    while first < 0:
        first += 4 * per
    return {"score_old": round(s_old, 2), "score_new": round(s_new, 2), "bpm_old": a["bpm"],
            "bpm_new": round(60 / per, 3), "beat_period": per, "first_downbeat": first,
            "improves": s_new > 1.25 * s_old and abs(60 / per - a["bpm"]) > 0.05}


def fixed_analysis(a, F, phase, phrase_off):
    """A corrected copy of the analysis that mix.py can read as is (same schema)."""
    b = {k: v for k, v in a.items() if k not in ("bars", "sections", "novelty")}
    bp = a["beat_period"]
    first = a["first_downbeat"] + phase * bp
    if phase == 3 and first - 4 * bp >= 0:
        first -= 4 * bp  # same downbeat one bar earlier: bar numbers stay close to the old ones
    b["first_downbeat"] = round(float(first), 4)
    b["n_bars"] = int((a["duration"] - first) // (4 * bp))
    b["phrase_offset"] = int(phrase_off)
    vlin = 10 ** (F["vocal_db"] / 20)
    lv = []
    for k in range(b["n_bars"]):
        x = vlin[max(0, frame(first + 4 * k * bp)):max(1, frame(first + 4 * (k + 1) * bp))]
        lv.append(float(np.sqrt(np.mean(x ** 2))) if len(x) else 0.0)
    lv = np.array(lv)
    ref = np.percentile(lv, 90) + 1e-9
    b["vocal_bars"] = [round(float(min(1.0, v / ref)), 2) for v in lv]
    b["fixed_by"] = "autodj.skills.structure"
    return b


def verify(stem, write=True):
    a0 = load_analysis(stem)
    F = features(stem)
    words, wl = load_words(stem)
    rf = refit_grid(a0, F)
    a = dict(a0)
    if rf["improves"]:
        a.update(bpm=rf["bpm_new"], beat_period=rf["beat_period"], first_downbeat=rf["first_downbeat"])
        a["n_bars"] = int((a["duration"] - a["first_downbeat"]) // (4 * a["beat_period"]))
    bp = a["beat_period"]
    lines = sung_lines(words, wl, bp)
    lock = grid_lock(a, F)
    lo, hi, good = usable_bars(a, lock)
    wb = lock[1]["bar"] - lock[0]["bar"] if len(lock) > 1 else 8
    goodbar = [good[min(len(good) - 1, k // wb)] for k in range(a["n_bars"])]
    votes = downbeat_votes(a, F, lines, goodbar)
    post = votes["posterior"]
    phase = int(np.argmax(post))
    af = fixed_analysis(a, F, phase, 0)
    shift_bars = (af["first_downbeat"] - a["first_downbeat"]) / (4 * bp)
    af["novelty"] = list(np.interp(np.arange(af["n_bars"]) + shift_bars, np.arange(len(a0["novelty"])),
                                   a0["novelty"]).round(3))
    # phrase grid on the corrected grid
    ev, why, per_bar = bar_evidence(af, F, lines, 0)
    bounds = phrase_dp(ev, af["n_bars"])
    lo, hi = max(0, int(round(lo - shift_bars))), min(af["n_bars"], int(round(hi - shift_bars)))
    # how regular is it: share of boundaries on the dominant mod 8 line, and on the core
    # analysis' phrase_offset (mod 4)
    inner = [b for b in bounds if lo < b < hi]
    if inner:
        m8 = np.bincount([b % 8 for b in inner], minlength=8)
        off8 = int(np.argmax(m8))
        reg8 = float(m8.max() / len(inner))
        m4 = np.bincount([b % 4 for b in inner], minlength=4)
        off4 = int(np.argmax(m4))
        reg4 = float(m4.max() / len(inner))
    else:
        off8, reg8, off4, reg4 = 0, 0.0, 0, 0.0
    shifts = [w["shift_ms"] for w in lock if w["active"] and w["lock"] > 1.0]
    drift = (max(shifts) - min(shifts)) if shifts else 0
    act = [w for w in lock if w["active"]]
    lock_med = float(np.median([w["lock"] for w in act])) if act else 0.0

    # lyrics on phrase lines: share of long-breath line starts that sit at a phrase boundary
    bset = set(bounds)
    fph = af["first_downbeat"]
    big = [l for l in lines if l["gap"] >= 2 * bp]
    on = 0
    for l in big:
        k = int(round((l["start"] - fph) / (4 * bp)))
        x = (l["start"] - (fph + 4 * k * bp)) / bp
        if k in bset and -1.6 <= x <= 0.35:
            on += 1
    lyric_on_phrase = on / len(big) if big else None

    # confidence: downbeat posterior x grid lock x phrase regularity x usable share
    usable_share = (hi - lo) / max(1, af["n_bars"])
    conf_db = post[phase]
    conf_grid = float(np.clip((lock_med - 0.5) / 1.5, 0, 1))
    conf_phr = float(np.clip((reg4 - 0.4) / 0.5, 0, 1))
    conf = round(0.4 * conf_db + 0.25 * conf_grid + 0.2 * conf_phr + 0.15 * usable_share, 2)

    fixes = []
    if rf["improves"]:
        fixes.append(f"tempo refit on the drum stem: {rf['bpm_old']} -> {rf['bpm_new']} bpm "
                     f"(kick fit {rf['score_old']} -> {rf['score_new']})")
    if phase != 0:
        fixes.append(f"the one is {'%d beat(s) later' % phase if phase < 3 else '1 beat earlier'} than the analysis says "
                     f"(posterior {post[phase]:.2f}): first_downbeat {a0['first_downbeat']:.3f} -> "
                     f"{af['first_downbeat']:.3f} s")
    if off4 != a0.get("phrase_offset", 0) % 4 and reg4 > 0.5:
        fixes.append(f"phrase_offset {a0.get('phrase_offset', 0)} -> {off4} (mod 4, on the corrected grid; "
                     f"mod 8 line = {off8})")
    off_tempo = [w for w in lock if w["active"] and not w["on_tempo"]]
    if off_tempo:
        spans = ", ".join(f"bars {w['bar']}-{w['bar'] + 8} ~{w['local_bpm']}bpm" for w in off_tempo[:6])
        fixes.append(f"off tempo / off grid windows ({len(off_tempo)}): {spans}; plan only inside bars {lo}-{hi}")
    if drift > 50:
        fixes.append(f"grid drifts {drift} ms across the song: lock each transition on the kick (mix.py does) ")
    irregular = [(b0, b1) for b0, b1 in zip(bounds[:-1], bounds[1:]) if (b1 - b0) % 4 and 0 < b0 and b1 < af["n_bars"]]
    if irregular:
        fixes.append("odd length phrase blocks (extra / missing bars): "
                     + ", ".join(f"{b0}-{b1}" for b0, b1 in irregular[:6]))

    af["phrase_offset"] = off4
    af["phrase_bounds"] = bounds
    af["usable_bars"] = [lo, hi]
    ranges, st = [], None
    for k in range(af["n_bars"]):
        g = goodbar[min(len(goodbar) - 1, max(0, int(round(k + shift_bars))))]
        if g and st is None:
            st = k
        if not g and st is not None:
            ranges.append([st, k]); st = None
    if st is not None:
        ranges.append([st, af["n_bars"]])
    af["good_ranges"] = ranges
    rep = {"stem": stem, "bpm": a["bpm"], "bpm_core": a0["bpm"], "refit": {k: v for k, v in rf.items()},
           "first_downbeat_core": a0["first_downbeat"], "first_downbeat_fixed": af["first_downbeat"],
           "fixed_analysis": f"analysis/structure/fixed/{stem}.json",
           "n_bars": af["n_bars"], "confidence": conf,
           "downbeat_phase": phase, "downbeat_posterior": post, "votes": votes,
           "grid_lock_median": round(lock_med, 2), "core_grid_wrong": bool(rf["improves"] or phase != 0), "drift_ms": int(drift),
           "usable_bars": [lo, hi], "phrase_bounds": bounds, "phrase_offset_mod4": off4,
           "phrase_offset_mod8": off8, "phrase_regularity_mod4": round(reg4, 2),
           "phrase_regularity_mod8": round(reg8, 2), "lyric_lines_on_phrase": None if lyric_on_phrase is None
           else round(lyric_on_phrase, 2), "core_phrase_offset": a.get("phrase_offset", 0),
           "good_ranges": ranges, "fixes": fixes, "windows": lock,
           "evidence": [round(float(x), 2) for x in ev], "evidence_why": why}
    if write:
        CACHE.mkdir(parents=True, exist_ok=True)
        (CACHE / f"{stem}.verify.json").write_text(json.dumps(rep, indent=1, default=float))
        (CACHE / "fixed").mkdir(exist_ok=True)
        (CACHE / "fixed" / f"{stem}.json").write_text(json.dumps(af, indent=1, default=float))
    return rep, {"a": af, "F": F, "lines": lines, "per_bar": per_bar, "phase": 0}


# ---------------------------------------------------------------- 4. section labels

def tokens(text):
    return re.findall(r"[a-z']+", text.lower())


def label(stem, write=True, ver=None):
    rep, ctx = ver or verify(stem, write=write)
    a, lines, pb = ctx["a"], ctx["lines"], ctx["per_bar"]
    bp = a["beat_period"]
    f = a["first_downbeat"]
    bt = lambda k: f + 4 * k * bp
    bar_of = lambda t: (t - f) / (4 * bp)
    bounds = rep["phrase_bounds"]
    good = np.zeros(a["n_bars"] + 1, dtype=bool)
    for lo, hi in rep.get("good_ranges", [rep["usable_bars"]]):
        good[lo:hi] = True

    # hook lines: the chorus line and the title line (autodj.hooks), as bar positions
    from ..hooks import hook_candidates, words as hwords
    hook_sets = []
    try:
        for h, _ in hook_candidates(stem):
            if h:
                hook_sets.append(hwords(h["text"]))
    except FileNotFoundError:
        pass

    # line level repetition: a chorus line comes back far away (next chorus) and often
    # repeats close by too (inside the chorus). A verse line is sung once (or twice).
    toks = [set(tokens(l["text"])) for l in lines]
    lb = [bar_of(l["start"]) for l in lines]
    for i, l in enumerate(lines):
        far = near = 0
        if len(toks[i]) >= 3:
            for j in range(len(lines)):
                if j == i or len(toks[j]) < 3:
                    continue
                sim = len(toks[i] & toks[j]) / len(toks[i] | toks[j])
                if sim >= 0.5:
                    if abs(lb[i] - lb[j]) >= 16:
                        far += 1
                    elif abs(lb[i] - lb[j]) >= 1:
                        near += 1
        hook = any(len(hs & toks[i]) / max(1, len(hs)) >= 0.6 for hs in hook_sets) if len(toks[i]) >= 2 else False
        l["chorusness"] = min(far, 3) / 3 + 0.3 * min(near, 2) / 2 + (0.8 if hook else 0.0)
        l["hook"] = bool(hook)

    vref = np.nanpercentile(pb["vocal_db"], 90)
    dref = np.nanpercentile(pb["drum_db"], 90)
    mref = np.nanpercentile(pb["mix_db"], 90)
    segs = []
    for s, e in zip(bounds[:-1], bounds[1:]):
        ls = [l for l in lines if bt(s) - 1.6 * bp <= l["start"] < bt(e) - 1.6 * bp]
        dur = sum(max(0.2, l["end"] - l["start"]) for l in ls)
        ch = sum(max(0.2, l["end"] - l["start"]) * l["chorusness"] for l in ls) / dur if dur else 0.0
        segs.append({"start": s, "end": e, "bars": e - s, "n_lines": len(ls),
                     "tokens": [t for l in ls for t in tokens(l["text"])],
                     "vocal": float(np.mean(pb["sing"][s:e])),
                     "drums_db": round(float(np.nanmean(pb["drum_db"][s:e])) - dref, 1),
                     "energy_db": round(float(np.nanmean(pb["mix_db"][s:e])) - mref, 1),
                     "hooks": sum(l["hook"] for l in ls), "chorusness": round(ch, 2),
                     "good": bool(good[s:e].mean() > 0.5),
                     "text": " / ".join(l["text"] for l in ls)[:120]})
    energies = np.array([s["energy_db"] for s in segs])
    e_med = float(np.median(energies))
    sung = lambda sg: sg["vocal"] >= 0.4 and len(sg["tokens"]) >= 4
    ch_max = max([sg["chorusness"] for sg in segs if sung(sg)] or [0])
    ch_thr = max(0.45, 0.55 * ch_max)

    for sg in segs:
        sg["label"] = None
        if not sg["good"] and sg["drums_db"] < -20 and sg["vocal"] > 0.3:
            sg["label"] = "talk"  # singing or talking off the grid with no beat: a video skit
        elif sung(sg) and sg["chorusness"] >= ch_thr and sg["energy_db"] >= e_med - 6:
            sg["label"] = "chorus"
    first_voc = next((i for i, s in enumerate(segs) if sung(s) and s["label"] != "talk"), len(segs))
    last_voc = max((i for i, s in enumerate(segs) if sung(s) and s["label"] != "talk"), default=-1)
    ch_idx = [i for i, s in enumerate(segs) if s["label"] == "chorus"]
    for i, sg in enumerate(segs):
        if sg["label"]:
            continue
        nxt = segs[i + 1] if i + 1 < len(segs) else None
        prv = segs[i - 1] if i > 0 else None
        if not sung(sg):
            if i < first_voc:
                sg["label"] = "intro"
            elif i > last_voc:
                sg["label"] = "outro"
            elif sg["drums_db"] < -10 or sg["energy_db"] < e_med - 4:
                sg["label"] = "breakdown"
            elif nxt and nxt["energy_db"] > sg["energy_db"] + 2 and sg["bars"] <= 8:
                sg["label"] = "build"
            elif prv and prv["label"] in ("chorus", "post-chorus"):
                sg["label"] = "post-chorus" if sg["energy_db"] >= e_med - 1.5 else "breakdown"
            else:
                sg["label"] = "drop" if sg["energy_db"] >= e_med - 1.5 else "instrumental"
        else:
            before_chorus = nxt is not None and nxt["label"] == "chorus"
            between_late = len(ch_idx) >= 2 and ch_idx[1] < i < ch_idx[-1]
            if ch_idx and i > ch_idx[-1] and i >= last_voc and sg["energy_db"] < e_med - 3:
                sg["label"] = "outro"
            elif before_chorus and sg["bars"] <= 8 and (prv is None or prv["label"] != "chorus"):
                sg["label"] = "pre-chorus"
            elif between_late and sg["chorusness"] < 0.3:
                sg["label"] = "bridge"
            else:
                sg["label"] = "verse"
    # merge neighbours with the same label into sections, number them
    sections = []
    for sg in segs:
        if sections and sections[-1]["label"] == sg["label"] and sections[-1]["bars"] < 32:
            s = sections[-1]
            s["end"] = sg["end"]
            s["bars"] = s["end"] - s["start"]
            s["hooks"] += sg["hooks"]
            s["text"] = (s["text"] + " / " + sg["text"])[:160]
            s["vocal"] = round((s["vocal"] + sg["vocal"]) / 2, 2)
            s["energy_db"] = round(max(s["energy_db"], sg["energy_db"]), 1)
            s["chorusness"] = max(s["chorusness"], sg["chorusness"])
            s["blocks"].append([sg["start"], sg["end"]])
        else:
            sections.append({k: sg[k] for k in ("start", "end", "bars", "label", "hooks", "text", "energy_db",
                                                "drums_db", "chorusness", "good")}
                            | {"vocal": round(sg["vocal"], 2), "blocks": [[sg["start"], sg["end"]]]})
    count = {}
    for s in sections:
        count[s["label"]] = count.get(s["label"], 0) + 1
        s["name"] = f"{s['label']} {count[s['label']]}"
        s["t"] = round(bt(s["start"]), 2)
    out = {"stem": stem, "first_downbeat": round(f, 4), "bar_s": round(4 * bp, 4), "bpm": a["bpm"],
           "usable_bars": rep["usable_bars"], "good_ranges": rep.get("good_ranges"),
           "phrase_bounds": bounds, "sections": sections, "lines": [
               {"start": round(l["start"], 2), "end": round(l["end"], 2), "gap": round(min(l["gap"], 99), 2),
                "bar": round(bar_of(l["start"]), 2), "end_bar": round(bar_of(l["end"]), 2),
                "chorusness": round(l["chorusness"], 2), "hook": l["hook"], "text": l["text"][:80]}
               for l in lines]}
    if write:
        CACHE.mkdir(parents=True, exist_ok=True)
        (CACHE / f"{stem}.sections.json").write_text(json.dumps(out, indent=1, default=float))
    return out, rep


def load_structure(stem):
    """Labelled structure (cached). Planner entry point."""
    p = CACHE / f"{stem}.sections.json"
    v = CACHE / f"{stem}.verify.json"
    if p.exists() and v.exists():
        return json.loads(p.read_text()), json.loads(v.read_text())
    return label(stem)


# ---------------------------------------------------------------- CLI

def print_verify(rep):
    p = rep["downbeat_posterior"]
    v = rep["votes"]
    print(f"{rep['stem']}: conf {rep['confidence']:.2f} | downbeat phase {rep['downbeat_phase']} "
          f"(post {p}; L {v['lyrics']} n={v['n_lines']}, D {v['drums']} n={v['n_drum_jumps']}, H {v['harmony']}) | "
          f"bpm {rep['bpm_core']} -> {rep['bpm']} | "
          f"grid lock {rep['grid_lock_median']} drift {rep['drift_ms']}ms | usable {rep['usable_bars']} | "
          f"phrase mod4 {rep['phrase_offset_mod4']} (core {rep['core_phrase_offset']}) reg {rep['phrase_regularity_mod4']} "
          f"| lyric lines on phrase {rep['lyric_lines_on_phrase']}")
    print(f"   phrase bounds: {rep['phrase_bounds']}")
    for fx in rep["fixes"]:
        print(f"   FIX: {fx}")


def print_sections(out):
    print(f"{out['stem']}:")
    for s in out["sections"]:
        print(f"   {s['start']:>4}-{s['end']:<4} {s['name']:<14} voc {s['vocal']:.2f} E {s['energy_db']:+5.1f} "
              f"dr {s['drums_db']:+5.1f} hooks {s['hooks']} ch {s['chorusness']:.2f}  {s['text'][:70]}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    filt = sys.argv[2].lower() if len(sys.argv) > 2 else ""
    for st in song_list():
        if filt not in st.lower():
            continue
        if cmd == "verify":
            print_verify(verify(st)[0])
        else:
            out, rep = label(st)
            if cmd == "all":
                print_verify(rep)
            print_sections(out)
        print()
