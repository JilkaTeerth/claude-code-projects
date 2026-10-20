"""Vocals and harmony skill: acapellas, mashups, wordplay hand offs, key shifts.

Importing this module registers three techniques into autodj.mix.TECHNIQUES:
  acapella_over_v2  B's vocal teases over A's instrumental (polished: gate, HPF, mid lift,
                    short reverb, A gets a small vocal pocket), resonant build, beats swap on the one
  mashup            a full section of B's acapella over A's instrumental, then the instrumentals
                    swap on the EQ under the voice (DJ Carlo's "acapella link"). opts.direction
                    "a_over_b" keeps A's acapella over B's instrumental instead
  wordplay          A sings its line to the end, the last word is thrown into an echo, and B lands
                    on the answering line (a drop: b_entry_bar is where B lands, like slam)

Tools (pure readers of analysis/, lyrics/, stems/):
  python -m autodj.skills.vocals find [A B]        ranked lyric hand offs with bars + plan snippet
  python -m autodj.skills.vocals mashups [A B]     ranked acapella-over-instrumental spots, measured key fit
  python -m autodj.skills.vocals shift A a0 a1 B b0 b1   best pitch_semitones for B (cap 2), measured
  python -m autodj.skills.vocals run plans/x.json  build + critic + vocal overlap / clash / word cut numbers

Rules this follows (skills/VOCALS.md has the sources): one lead vocal at a time unless it is a
deliberate in-key mashup; wordplay max 2 or 3 per set; key shift max 2 semitones (1 preferred);
an acapella is never played over a vocal section; isolated vocals get mids and a little reverb.
"""
import json
import math
import re
import sys
from functools import lru_cache
from pathlib import Path

import librosa
import numpy as np
import pedalboard as pb
import soundfile as sf

from autodj import mix
from autodj.mix import (INST, SNAP, STEMS, cut, db, eq, hold, ramp, vocal_echo)
from autodj.analyze import SR

ROOT = mix.ROOT

# ---------------------------------------------------------------- keys

def camelot_parse(c):
    m = re.match(r"(\d+)([AB])", c)
    return int(m.group(1)), m.group(2)


def camelot_shift(c, semis):
    """Camelot code after pitching by `semis` semitones (+1 semitone = +7 on the wheel)."""
    n, l = camelot_parse(c)
    return f"{(n - 1 + 7 * semis) % 12 + 1}{l}"


def camelot_fit(c1, c2):
    """How well two keys sit together, 0..1, the Mixed In Key rules.
    same 1.0 | +-1 same letter or relative (same number) 0.9 | diagonal (+-1, other letter) 0.6 |
    +-2 same letter ("energy boost") 0.45 | anything else 0.1"""
    n1, l1 = camelot_parse(c1)
    n2, l2 = camelot_parse(c2)
    d = min((n1 - n2) % 12, (n2 - n1) % 12)
    if l1 == l2:
        return {0: 1.0, 1: 0.9, 2: 0.45}.get(d, 0.1)
    return {0: 0.9, 1: 0.6}.get(d, 0.1)


DISSONANCE = np.array([0.0, 1.0, 0.45, 0.15, 0.1, 0.05, 0.8])  # same table as listen.py


def clash(ca, cb):
    """listen.py's dissonance of two pitch class profiles, normalised by each one with itself:
    ~1.0 = as consonant as each part alone, > 1.15 sour, > 1.35 clashes."""
    D = np.array([[DISSONANCE[min((i - j) % 12, (j - i) % 12)] for j in range(12)] for i in range(12)])
    cross = ca @ D @ cb
    self_ref = (ca @ D @ ca + cb @ D @ cb) / 2
    return float(cross / (self_ref + 1e-9))


@lru_cache(maxsize=64)
def _analysis(stem):
    return json.loads((ROOT / "analysis" / f"{stem}.json").read_text())


def bar_time(stem, bar):
    a = _analysis(stem)
    return a["first_downbeat"] + bar * 4 * a["beat_period"]


def time_bar(stem, t):
    a = _analysis(stem)
    return (t - a["first_downbeat"]) / (4 * a["beat_period"])


def note_histogram(x, top=3):
    """Pitch class histogram of the notes that are actually sounding: per frame keep only the
    `top` strongest pitch classes (1 for a lead vocal, 3 for chords), weight by loudness, skip
    quiet frames. Plain mean chroma is nearly flat on real mixes (every frame is normalised to
    its own max), which makes every pair look consonant; this is ~5x more discriminating."""
    c = librosa.feature.chroma_cqt(y=x, sr=SR, hop_length=2048, norm=None)
    e = c.sum(axis=0)
    keep = e > np.percentile(e, 40)
    c, e = c[:, keep], e[keep]
    if c.shape[1] < 4:
        return None
    h = np.zeros(12)
    idx = np.argsort(-c, axis=0)[:top]
    for k in range(top):
        np.add.at(h, idx[k], e * (1.0 / (k + 1)))
    return h / (h.sum() + 1e-9)


@lru_cache(maxsize=256)
def stem_chroma(stem, part, bar0, bar1):
    """Note histogram of one stem between two bars of the original song."""
    t0, t1 = bar_time(stem, bar0), bar_time(stem, bar1)
    p = ROOT / "stems" / stem / f"{part}.flac"
    x, _ = sf.read(p, start=max(0, int(t0 * SR)), stop=int(t1 * SR), dtype="float32", always_2d=True)
    x = x.mean(axis=1)
    if len(x) < SR or np.abs(x).max() < 1e-4:
        return None
    h = note_histogram(x, top=1 if part == "vocals" else 3)
    return None if h is None else tuple(h)


def choose_shift(a_stem, a_bars, b_stem, b_bars, cap=2, b_part="vocals", a_part="other",
                 a_pitch=0, penalty=0.05):
    """The auto key shift chooser. Measures the dissonance of B's part (default its vocal, the
    acapella case) against A's harmonic stem over the bars they would share, for every shift
    from -cap to +cap, and picks the least sour, preferring no shift (each semitone costs
    `penalty`). Pitch shifting a chroma profile is a roll, so this is exact and cheap.
    Returns (best_shift, {shift: clash})."""
    ca = stem_chroma(a_stem, a_part, *a_bars)
    cb = stem_chroma(b_stem, b_part, *b_bars)
    if ca is None or cb is None:
        return 0, {}
    ca = np.roll(np.array(ca), a_pitch)
    cb = np.array(cb)
    scores = {s: round(clash(ca, np.roll(cb, s)), 3) for s in range(-cap, cap + 1)}
    best = min(scores, key=lambda s: scores[s] + penalty * abs(s))
    return best, scores


# ---------------------------------------------------------------- vocal polish (artifact hiding)

def expander(x, rel_db=-30.0, floor_db=-24.0, hop=441):
    """Downward expander for demucs bleed: frames more than `rel_db` below the stem's active
    level (90th percentile frame RMS) are pulled down, by up to `floor_db`. Fast attack (one
    hop), ~150 ms release, so word onsets are untouched and breaths/bleed between lines drop.
    pedalboard's NoiseGate measured as a no-op on these stems, hence this."""
    mono = np.abs(x).mean(axis=1)
    m = len(mono) // hop
    if m < 4:
        return x
    fr = np.sqrt((mono[: m * hop].reshape(m, hop) ** 2).mean(axis=1) + 1e-12)
    act = np.percentile(fr, 90)
    thr = act * 10 ** (rel_db / 20)
    g = np.clip((fr / thr) ** 2, 10 ** (floor_db / 20), 1.0)  # 1:3 expansion below threshold
    rel = np.exp(-hop / (0.15 * SR))
    sm = np.empty_like(g)
    cur = 1.0
    for i, v in enumerate(g):
        cur = v if v > cur else cur * rel + v * (1 - rel)
        sm[i] = cur
    env = np.interp(np.arange(len(x)), np.arange(m) * hop + hop / 2, sm).astype(np.float32)
    return x * env[:, None]


def polish_chain(beat, o):
    """The acapella chain (after `expander`, which kills demucs bleed between phrases before the
    reverb can smear it). Clean the lows (they belong to the instrumental underneath),
    take a little mud out, lift the presence so it cuts through a mix that was not made for it,
    tame the hiss band where separation artifacts live, glue with gentle compression, then a
    short room and a quiet 1/8 note slap so the dry stem sits inside someone else's track."""
    return pb.Pedalboard([
        pb.HighpassFilter(o.get("hp_hz", 140.0)),
        pb.PeakFilter(cutoff_frequency_hz=300.0, gain_db=-2.0, q=1.0),
        pb.PeakFilter(cutoff_frequency_hz=3000.0, gain_db=o.get("mid_lift_db", 2.5), q=0.8),
        pb.HighShelfFilter(cutoff_frequency_hz=9000.0, gain_db=-2.0, q=0.7),
        pb.Compressor(threshold_db=-20.0, ratio=2.5, attack_ms=8.0, release_ms=120.0),
        pb.Delay(delay_seconds=beat / 2, feedback=0.15, mix=o.get("slap_mix", 0.07)),
        pb.Reverb(room_size=o.get("room", 0.35), damping=0.55, wet_level=o.get("reverb_wet", 0.15),
                  dry_level=1.0 - o.get("reverb_wet", 0.15) * 0.5, width=0.8),
    ])


def polish_vocal(t, t0, t1, o=None):
    """Process t's vocal stem in place between local times t0 and t1 (plus a reverb tail), with
    short crossfades to the untouched stem at both ends. Loudness matched to the dry stem."""
    o = o or {}
    i0, i1 = t.idx(t0), t.idx(t1)
    tail = int(1.5 * SR)
    i2 = min(t.n, i1 + tail)
    if i1 - i0 < SR // 2:
        return
    dry = t.stems["vocals"][i0:i2].astype(np.float32)
    gated = expander(dry, o.get("gate_rel_db", -30.0)) if o.get("gate", True) else dry
    wet = polish_chain(t.bar_len / 4, o)(np.ascontiguousarray(gated.T), SR).T[: len(dry)]
    # match level on the active part (so the polish is a sound change, not a volume change)
    rd, rw = np.sqrt((dry[: i1 - i0] ** 2).mean() + 1e-12), np.sqrt((wet[: i1 - i0] ** 2).mean() + 1e-12)
    wet *= min(rd / rw, 2.0) * db(o.get("vocal_gain_db", 0.0))
    n = len(dry)
    w = np.ones(n, dtype=np.float32)
    xf_in, xf_out = int(0.02 * SR), min(tail, n - (i1 - i0))
    w[:xf_in] = np.linspace(0, 1, xf_in)
    if xf_out > 0:
        w[i1 - i0:] = np.linspace(1, 0, n - (i1 - i0))
    t.stems["vocals"][i0:i2] = wet * w[:, None] + dry * (1 - w[:, None])
    t.refresh()


# ---------------------------------------------------------------- techniques

def first_line_start(t, t_from, back_beats=1.0, min_gap=0.2):
    """Local time of the first sung line that starts at or after t_from (or up to `back_beats`
    before it, a pickup): a word with >= min_gap s of silence before it. Opening a vocal there
    instead of on the bar line means the incoming singer never enters on the tail of a word
    (the critic caught 'songs' and 'Young' being clipped that way)."""
    words = mix.load_words(t)
    beat = t.bar_len / 4
    for i, w in enumerate(words):
        if w["s"] < t_from - back_beats * beat:
            continue
        prev_e = words[i - 1]["e"] if i else -9.0
        if w["s"] - prev_e >= min_gap:
            return w["s"]
    return None


def _open_vocal_on_line(t, t_from, until, back_beats=1.0):
    """Hold t's vocal shut from t_from until its first line start, then open it on that word."""
    v_on = first_line_start(t, t_from, back_beats)
    if v_on is None or v_on > until:
        v_on = t_from
    start = v_on - 0.03
    hold(t, ["vocals"], max(0.0, min(t_from, start) - 4 * t.bar_len), start, 0)
    ramp(t, ["vocals"], start, start + SNAP, 0, 1)
    return start


def _snap_in(t, stems, at, level=1.0):
    for st in stems:
        ramp(t, [st], at, at + SNAP, float(t.g[st][max(0, t.idx(at) - 1)]), level)


def t_acapella_over_v2(A, B, ts, te, bars, o):
    """STUDY.md R5, done the way the acapella tutorials say. A's line has ended; B's vocal comes
    in (opening early for its pickup, respect_words does that) over A's full instrumental.
    B's vocal is polished (gate, HPF, mid lift, short room). A's mids dip 3 dB as a vocal pocket.
    The last `build_bars` (4) get a resonant high pass climb on A and A's lows ease to half; with
    opts.b_hats B's hats creep in under the build. On the one, A's beat is gone and B's is in."""
    a, b = A.local, B.local
    L = te - ts
    if o.get("vocal_echo", True):
        vocal_echo(A, a(ts))
    cut(A, ["vocals"], a(ts), 0)
    hold(B, INST, b(ts), b(te), 0)
    _open_vocal_on_line(B, b(ts), b(te), back_beats=0.5)
    if o.get("polish", True):
        polish_vocal(B, b(ts) - B.bar_len, b(te) + o.get("polish_after_bars", 2) * B.bar_len, o)
    eq(A, "mid", a(ts), a(ts) + A.bar_len / 4, 0, o.get("a_pocket_db", -3))
    build = min(o.get("build_bars", 4) * A.bar_len, L)
    if build > 0:
        A.sweeps.append((a(te) - build, a(te), 30.0, o.get("max_hz", 600.0), "high", 1.2))
        ramp(A, ["bass"], a(te) - min(build, 2 * A.bar_len), a(te), 1, 0.5)
        if o.get("b_hats"):
            ramp(B, ["drums"], b(te) - build, b(te) - build + A.bar_len, 0, db(-10))
            eq(B, "mid", b(te) - build, b(te), -18, -18)
    cut(A, INST, a(te), 0)
    eq(B, "mid", b(te), b(te) + SNAP, -18 if o.get("b_hats") else 0, 0)
    _snap_in(B, INST, b(te))


def t_mashup(A, B, ts, te, bars, o):
    """A live mashup for a whole section, then the "acapella link" (DJ Carlo): the voice keeps
    going while the instrumentals swap underneath on the EQ, so the crowd hears one song turn
    into another without the singer stopping. Use 16 to 32 bars; keys must fit (measure with
    choose_shift and put the result in B's pitch_semitones, max 2).

    direction "b_over_a" (default): B's acapella over A's instrumental, the last `swap_bars` (4)
    bring B's beat in hats first, lows swap halfway, A leaves. B's song simply carries on.
    direction "a_over_b": B's instrumental replaces A's over the first `swap_bars`, A's acapella
    rides B's beat until the end of the overlap, B's own vocal starts on the next phrase."""
    a, b = A.local, B.local
    L = te - ts
    sw = min(o.get("swap_bars", 4) * A.bar_len, L)
    if o.get("direction", "b_over_a") == "a_over_b":
        s0, s1 = ts, ts + sw
        hold(B, ["vocals"], b(ts), b(te), 0)
        if o.get("polish", True):
            polish_vocal(A, a(ts), a(te) + A.bar_len, o)
        _instrument_swap(A, B, s0, s1, o)
        if o.get("vocal_echo", True):
            vocal_echo(A, a(te))
        cut(A, ["vocals"], a(te), 0)
        _open_vocal_on_line(B, b(te), b(te) + 4 * B.bar_len, back_beats=1.5)
        return
    s0, s1 = te - sw, te
    if o.get("vocal_echo", True):
        vocal_echo(A, a(ts))
    cut(A, ["vocals"], a(ts), 0)
    hold(B, INST, b(ts), b(s0), 0)
    _open_vocal_on_line(B, b(ts), b(te), back_beats=0.5)
    if o.get("polish", True):
        polish_vocal(B, b(ts) - B.bar_len, b(te) + B.bar_len, o)
    eq(A, "mid", a(ts), a(ts) + A.bar_len / 4, 0, o.get("a_pocket_db", -3))
    _instrument_swap(A, B, s0, s1, o, a_mid_start=o.get("a_pocket_db", -3))


def _instrument_swap(A, B, s0, s1, o, a_mid_start=0):
    """eq_blend on the instruments only (no vocal moves), over [s0, s1)."""
    a, b = A.local, B.local
    L = s1 - s0
    mid = s0 + L / 2
    hold(B, ["bass"], b(s0), b(mid), 0)
    ramp(B, ["drums", "other"], b(s0), b(s0 + L * 0.25), 0, 1, law="power")
    eq(B, "mid", b(s0), b(mid), -12, -6)
    eq(B, "mid", b(mid), b(s0 + L * 0.875), -6, 0)
    eq(A, "hi", a(s0 + L * 0.25), a(mid), 0, -6)
    cut(A, ["bass"], a(mid), 0)
    ramp(B, ["bass"], b(mid), b(mid) + 0.025, 0, 1)
    eq(A, "mid", a(mid), a(s0 + L * 0.875), a_mid_start, -8)
    eq(A, "hi", a(mid), a(s0 + L * 0.875), -6, -16)
    ramp(A, ["drums"], a(s0 + L * 0.625), a(s0 + L * 0.875), 1, 0)
    ramp(A, ["other"], a(s0 + L * 0.75), a(s1), 1, 0, law="power")
    cut(A, ["drums", "other", "bass"], a(s1), 0)


def t_wordplay(A, B, ts, te, bars, o):
    """The lyric hand off (a drop: B lands at te on b_entry_bar, like slam).
    A plays full and sings its line to the end; a gentle resonant high pass climbs on A's music
    (not its vocal: the words must stay clear), A's lows ease off on the last two beats. A's
    last word is thrown into a 1/2 beat echo that rings over B's first bar, and B arrives with
    the answering line (its pickup sung over A's echo, respect_words opens it early).
    style "blend": B's drums and music (no lows, no vocal) creep in under A at -10 dB first.
    Plan it with `find`: a_exit_bar = first bar after A's line ends, b_entry_bar = the bar of
    B's answering line, bars = 2."""
    a, b = A.local, B.local
    beat = A.bar_len / 4
    hold(B, STEMS, b(ts), b(te), 0)
    if o.get("style") == "blend":
        ramp(B, ["drums", "other"], b(ts), b(ts) + beat, 0, db(-10))
        eq(B, "mid", b(ts), b(te), -8, -8)
        eq(B, "mid", b(te), b(te) + SNAP, -8, 0)
        eq(A, "hi", a(ts), a(te), 0, -8)
    else:
        # music only: the sweep runs on A's instruments by thinning them, the vocal stays dry
        eq(A, "mid", a(ts), a(te), 0, -4)
        eq(A, "hi", a(ts), a(te), 0, -10)
    ramp(A, ["bass"], a(te - 2 * beat), a(te), 1, 0.5)
    if o.get("throw", True):
        vocal_echo(A, a(te), beats=o.get("throw_beats", 1.0))
    cut(A, STEMS, a(te), 0)
    _snap_in(B, INST, b(te))
    # B's voice opens exactly on the answering line (opts.b_line_bar from `find`), never on
    # whatever B was singing just before it ("Young money" before Bieber's "Tonight")
    if "b_line_bar" in o:
        target = B.bar(o["b_line_bar"]) - 0.15
        _open_vocal_on_line(B, target, target + B.bar_len, back_beats=0.3)
    else:
        _open_vocal_on_line(B, b(te) - o.get("pickup_beats", 1.0) * beat, b(te) + 2 * B.bar_len, back_beats=0.0)


mix.TECHNIQUES.update({"acapella_over_v2": t_acapella_over_v2, "mashup": t_mashup,
                       "wordplay": t_wordplay})
mix.DROPS.add("wordplay")


# ---------------------------------------------------------------- lyric hand off finder v2

STOP = set("""i a the and to of in on it is you me my your we our be so oh yeah ah uh
that this but for with just like cause 'cause its it's i'm im all now up down no yes
do don't dont got get can can't what when where who are was were will gonna wanna
baby hey ooh na la let's lets yo eh woo whoa ha hmm mmm ay ayy""".split())
# loose sound / meaning families: a hand off between two members is a "sounds like" link
FAMILIES = [{"night", "tonight", "friday", "weekend", "party", "club"},
            {"dance", "move", "floor", "dancing", "moving"},
            {"fall", "falling", "fallin", "fell"},
            {"love", "lover", "heart"},
            {"world", "life", "alive", "live", "young"},
            {"worry", "fear", "scared", "afraid"},
            {"feel", "feeling", "feelin"},
            {"close", "near"},
            {"home", "phone", "payphone"}]
THEME = {"night", "tonight", "friday", "party", "dance", "floor", "love", "fall", "falling", "feel",
         "feeling", "close", "young", "world", "worry", "everything", "beat", "music", "body", "dj",
         "high", "fire", "heart", "crazy", "city", "home", "last", "live", "life", "hot", "cold"}
GENERIC = {"could", "because", "right", "what's", "about", "think", "need", "let", "time", "nothing",
           "said", "know", "never", "make", "want", "girl", "boy", "way", "thing", "see", "say", "tell",
           "come", "go", "going", "take", "give", "really", "every", "still", "back", "one"}
# skits and crowd talk in the video versions (bars, from STATE.md): never land a hand off there
SKITS = {"Katy_Perry_Last_Friday_Night": [(0, 25), (150, 260)],
         "Swedish_House_Mafia_Dont_You_Worry_Child": [(42, 50)],
         "Rihanna_We_Found_Love": [(0, 24)],
         "Justin_Bieber_Beauty_And_A_Beat": [(128, 160)]}


def norm(w):
    w = re.sub(r"[^a-z']", "", w.lower()).strip("'")
    w = {"tonite": "tonight", "nite": "night", "fallin": "falling", "lovin": "loving",
         "feelin": "feeling", "gotta": "got", "cuz": "cause"}.get(w, w)
    if w.endswith("in'"):
        w = w[:-1] + "g"
    return w


def root(w):
    for suf in ("ing", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w


def phrases(stem):
    """Sung phrases from word timestamps: split on whisper line ends and on gaps > 0.45 s.
    Each phrase knows its start / end bar and the silence before / after it."""
    from autodj.lyrics import clean_words
    lyr = json.loads((ROOT / "lyrics" / f"{stem}.json").read_text())
    words = clean_words(lyr["words"])
    ends = {round(l["end"], 2) for l in lyr["lines"]}
    starts = [l["start"] for l in lyr["lines"]]
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        nxt = words[i + 1] if i + 1 < len(words) else None
        if nxt is None or nxt["start"] - w["end"] > 0.45 or round(w["end"], 2) in ends:
            out.append(cur)
            cur = []
    res = []
    for k, ws in enumerate(out):
        toks = [norm(w["w"]) for w in ws]
        keep = [(t, w) for t, w in zip(toks, ws) if t]
        if len(keep) < 2:
            continue
        s, e = keep[0][1]["start"], keep[-1][1]["end"]
        prev_e = out[k - 1][-1]["end"] if k else -9
        next_s = out[k + 1][0]["start"] if k + 1 < len(out) else 1e9
        res.append({"toks": [t for t, _ in keep], "words": [w for _, w in keep],
                    "text": " ".join(w["w"] for _, w in keep), "s": s, "e": e,
                    "bar0": time_bar(stem, s), "bar1": time_bar(stem, e),
                    "gap_before": s - prev_e, "gap_after": next_s - e,
                    "line_start": any(abs(s - x) < 0.35 for x in starts),
                    "line_end": round(e, 2) in ends})
    return res


@lru_cache(maxsize=1)
def _corpus():
    stems = sorted(p.stem for p in (ROOT / "lyrics").glob("*.json") if (ROOT / "analysis" / f"{p.stem}.json").exists())
    ph = {s: phrases(s) for s in stems}
    df = {}
    for s in stems:
        for t in {root(t) for p in ph[s] for t in p["toks"]}:
            df[t] = df.get(t, 0) + 1
    hooks = json.loads((ROOT / "analysis" / "_hooks.json").read_text())
    return stems, ph, df, hooks


def idf(tok):
    stems, _, df, _ = _corpus()
    return math.log((len(stems) + 1) / (df.get(root(tok), 0) + 0.5))


def content(tok):
    return tok not in STOP and len(tok) > 2


def jacc(a, b):
    a, b = set(a), set(b)
    return len(a & b) / max(1, len(a | b))


def repeats(stem, p):
    """How many times this phrase (or one nearly the same) is sung in the song."""
    _, ph, _, _ = _corpus()
    return sum(1 for q in ph[stem] if jacc(p["toks"], q["toks"]) >= 0.6)


def is_hook(stem, p):
    _, _, _, hooks = _corpus()
    h = hooks.get(stem, {}).get("hook")
    if not h:
        return False
    ht = [norm(w) for w in h.split() if norm(w)]
    return len(set(p["toks"]) & set(ht)) / max(1, len(set(p["toks"]))) >= 0.6


def in_skit(stem, bar):
    return any(a <= bar < b for a, b in SKITS.get(stem, []))


def tempo_gap(bpm_a, bpm_b):
    """Smallest relative tempo gap allowing half / double time."""
    return min(abs(bpm_a * k / bpm_b - 1) for k in (0.5, 1, 2))


def link(pa, pb_):
    """Lexical / sound link between the end of A's phrase and the start of B's phrase.
    A's whole line can echo into B (Usher's 'the last, last night of your life' ->
    'Last Friday night'), weighted toward its end; B's side is its first 4 words."""
    ta, tb = pa["toks"], pb_["toks"][:4]
    na = len(ta)
    best, shared, order = 0.0, [], []
    for j, y in enumerate(tb):
        if not content(y):
            continue
        wb = 0.8 ** j
        for i in reversed(range(na)):  # the latest occurrence in A's line counts
            x = ta[i]
            if not content(x):
                continue
            wa = 0.92 ** (na - 1 - i)
            if root(x) == root(y):
                v = idf(y) * wa * wb
                if root(y) not in [root(s) for s in shared]:
                    shared.append(y)
                    order.append(i)
                    best += v
                break
    kind = "word"
    a_last = next((x for x in reversed(ta) if content(x)), None)
    b_first = next((y for y in tb if content(y)), None)
    bonus = 0.0
    if a_last and b_first and root(a_last) == root(b_first):
        # anadiplosis: A's last word is the first thing B says. Worth most on a word that means
        # something on a dance floor or is rare; filler words ("could", "right") barely count
        bonus += 2.0 if (a_last in THEME or idf(a_last) >= 1.2) and a_last not in GENERIC else \
            (0.3 if a_last in GENERIC else 1.0)
        kind = "echo"
    if len(shared) >= 2 and order == sorted(order):
        bonus += 2.0 * (len(shared) - 1)  # the phrase comes back in order ("last ... night")
        kind = "phrase"
    if not shared and a_last and b_first:
        if any(a_last in f and b_first in f for f in FAMILIES):
            best, kind, shared = 0.9, "family", [f"{a_last}~{b_first}"]
        elif a_last != b_first and len(a_last) > 3 and len(b_first) > 3 and a_last[-3:] == b_first[-3:]:
            best, kind, shared = 0.6, "rhyme", [f"{a_last}~{b_first}"]
    return best + bonus, shared, kind


def score_handoff(sa, pa, sb, pb_):
    a, b = _analysis(sa), _analysis(sb)
    lex, shared, kind = link(pa, pb_)
    if lex < 0.9:
        return None
    notes = []
    s = lex
    # musical placement on the grid
    a_exit = math.ceil(pa["bar1"] - 0.05)
    frac_b = pb_["bar0"] - math.floor(pb_["bar0"])
    b_entry = math.floor(pb_["bar0"]) + (1 if frac_b > 0.6 else 0)  # > 0.6: a pickup into the next bar
    gap = (a_exit - pa["bar1"]) + (pb_["bar0"] - b_entry)  # bars of breath between the two singers
    if 0.15 <= gap <= 0.8:
        s += 1.0
    elif gap < 0.05 or gap > 1.3:
        s -= 2.0
        notes.append(f"gap {gap:.2f} bars")
    po_a, po_b = a.get("phrase_offset", 0), b.get("phrase_offset", 0)
    if (a_exit - po_a) % 4 == 0:
        s += 0.5
    if (b_entry - po_b) % 4 == 0:
        s += 0.5
    beat_a = a["beat_period"]
    if pa["gap_after"] >= beat_a:
        s += 0.5  # A's line really ends there
    elif pa["gap_after"] < 0.3 * beat_a and not pa["line_end"]:
        s -= 0.5  # the next line follows at once: fine if no word is chopped (respect_words)
        notes.append("A runs straight on")
    if pb_["gap_before"] >= b["beat_period"]:
        s += 0.5
    elif pb_["gap_before"] < 0.15 and not pb_["line_start"]:
        s -= 1.0  # B's "line" starts mid sentence (whisper split it): not an answering line
        notes.append("B mid sentence")
    if len(pb_["toks"]) < 3:
        s -= 1.0
        notes.append("B line too short")
    # how known the lines are
    if is_hook(sb, pb_) or repeats(sb, pb_) >= 3:
        s += 1.5
        notes.append("B hook")
    if repeats(sa, pa) >= 3 or is_hook(sa, pa):
        s += 0.5
        notes.append("A hook")
    _, ph, _, _ = _corpus()
    if ph[sb] and abs(pb_["s"] - ph[sb][0]["s"]) < 0.1:
        s += 1.0
        notes.append("B opening line")
    # noise: chants and whisper loops
    for p in (pa, pb_):
        c = [t for t in p["toks"] if content(t)]
        if c and max(c.count(t) for t in c) >= 3:
            s -= 1.5
            notes.append("chant")
            break
    if in_skit(sa, pa["bar1"]) or in_skit(sb, pb_["bar0"]):
        s -= 4
        notes.append("skit")
    if pb_["bar0"] < 2 or b_entry < 1:
        s -= 1.0
    # feasibility
    tg = tempo_gap(a["bpm"], b["bpm"])
    if tg > 0.08:
        s -= 1.0
        notes.append(f"tempo {tg * 100:.0f}%")
    kf = camelot_fit(a["camelot"], b["camelot"])
    s += 0.5 * kf
    return {"score": round(s, 2), "kind": kind, "shared": shared, "A": sa, "B": sb,
            "a_line": pa["text"], "b_line": pb_["text"], "a_end_bar": round(pa["bar1"], 2),
            "b_start_bar": round(pb_["bar0"], 2), "a_exit_bar": a_exit, "b_entry_bar": b_entry,
            "gap_bars": round(gap, 2), "pickup_beats": round(max(0.0, (b_entry - pb_["bar0"]) * 4) + 0.6, 2),
            "keys": f"{a['camelot']}->{b['camelot']}", "tempo_gap": round(tg, 3), "notes": notes}


def find_handoffs(filt_a="", filt_b="", top=40, per_pair=2):
    stems, ph, _, _ = _corpus()
    sa = [s for s in stems if filt_a.lower() in s.lower()]
    sb = [s for s in stems if filt_b.lower() in s.lower()]
    rows = []
    for A in sa:
        for B in sb:
            if A == B:
                continue
            cand = []
            for pa in ph[A]:
                for pb_ in ph[B]:
                    r = score_handoff(A, pa, B, pb_)
                    if r:
                        cand.append(r)
            cand.sort(key=lambda r: -r["score"])
            seen = set()
            kept = []
            for r in cand:
                key = " ".join(sorted(root(x) for x in r["shared"]))
                if key in seen:
                    continue
                seen.add(key)
                kept.append(r)
                if len(kept) >= per_pair:
                    break
            rows += kept
    rows.sort(key=lambda r: -r["score"])
    return rows[:top]


def plan_snippet(r, a_id=None, b_id=None):
    return {"from": a_id or r["A"], "to": b_id or r["B"], "technique": "wordplay",
            "a_exit_bar": r["a_exit_bar"], "b_entry_bar": r["b_entry_bar"], "bars": 2,
            "why": f"WORDPLAY: '...{r['a_line'][-40:]}' -> '{r['b_line'][:40]}'",
            "opts": {"pickup_beats": r["pickup_beats"], "b_line_bar": r["b_start_bar"]}}


# ---------------------------------------------------------------- mashup finder

def runs(mask, min_len):
    out, start = [], None
    for i, m in enumerate(list(mask) + [False]):
        if m and start is None:
            start = i
        if not m and start is not None:
            if i - start >= min_len:
                out.append((start, i))
            start = None
    return out


def word_coverage(stem):
    """Fraction of each bar covered by sung words (whisper timestamps)."""
    from autodj.lyrics import clean_words
    a = _analysis(stem)
    lyr = json.loads((ROOT / "lyrics" / f"{stem}.json").read_text())
    cov = np.zeros(a["n_bars"] + 1)
    for w in clean_words(lyr["words"]):
        b0, b1 = time_bar(stem, w["start"]), time_bar(stem, w["end"])
        for k in range(max(0, int(b0)), min(len(cov), int(b1) + 1)):
            cov[k] += max(0.0, min(b1, k + 1) - max(b0, k))
    return cov


def instrumental_spots(stem, min_bars=8):
    """Loud stretches with no lead vocal (drops, instrumental choruses, intros with a beat):
    no sung words (whisper) and a low vocal stem level, at or above the song's median loudness."""
    a = _analysis(stem)
    vb = np.array(a.get("vocal_bars") or [])
    if not len(vb):
        return []
    dbs = np.array([b["db"] for b in a["bars"]])[: len(vb)]
    cov = word_coverage(stem)[: len(vb)]
    loud = dbs > np.median(dbs) - 3
    quiet_voice = (cov < 0.12) & (vb < 0.35)
    spots = []
    po = a.get("phrase_offset", 0)
    for s, e in runs(quiet_voice & loud, min_bars - 2):
        s2 = s + (po - s) % 4  # start on a phrase line
        e2 = s2 + (e - s2) // 4 * 4
        if e2 - s2 >= min_bars - 4 and not in_skit(stem, s2):
            spots.append((s2, e2))
    return spots


def vocal_spots(stem, bars=8):
    """Where B's best acapella material is: its hook repeats (8 bars from each)."""
    _, ph, _, hooks = _corpus()
    a = _analysis(stem)
    po = a.get("phrase_offset", 0)
    out = []
    for p in ph[stem]:
        if (is_hook(stem, p) or repeats(stem, p) >= 3) and not in_skit(stem, p["bar0"]):
            s = math.floor(p["bar0"] + 0.4)
            s -= (s - po) % 4  # back to the phrase line
            if all(abs(s - x) >= bars for x, _ in out):
                out.append((s, p["text"]))
    return out


def find_mashups(filt_a="", filt_b="", top=40, cap=2):
    stems, _, _, _ = _corpus()
    rows = []
    for A in stems:
        if filt_a.lower() not in A.lower():
            continue
        # native instrumental stretches first; then A's choruses with A's vocal stem muted (the
        # stems era mashup: the bleed left in A's music is masked by B's voice on top)
        ia = [(s, e, "native") for s, e in instrumental_spots(A)][:3] + \
             [(s, s + 8, "muted") for s, _ in vocal_spots(A)[:2]]
        if not ia:
            continue
        for B in stems:
            if A == B or filt_b.lower() not in B.lower():
                continue
            a, b = _analysis(A), _analysis(B)
            tg = tempo_gap(a["bpm"], b["bpm"])
            if tg > 0.08:
                continue
            for b0, text in vocal_spots(B)[:3]:
                vlev = np.mean((b.get("vocal_bars") or [0])[b0:b0 + 8] or [0])
                for s, e, how in ia:
                    n = min(8, e - s)
                    shift, sc = choose_shift(A, (s, s + n), B, (b0, b0 + n), cap=cap)
                    if not sc:
                        continue
                    c = sc[shift]
                    score = 3.0 - 2.5 * max(0, c - 0.9) - 0.4 * abs(shift) - 10 * tg + 0.8 * min(vlev, 0.8) \
                        + 0.3 * min(e - s, 32) / 8 - (0.6 if how == "muted" else 0)
                    rows.append({"score": round(score, 2), "A": A, "a_bars": [s, e], "a_how": how,
                                 "B": B, "b_bar": b0,
                                 "b_line": text, "shift": shift, "clash": c, "clash_no_shift": sc[0],
                                 "keys": f"{a['camelot']}->{b['camelot']}"
                                         f"{' (B as ' + camelot_shift(b['camelot'], shift) + ')' if shift else ''}",
                                 "tempo_gap": round(tg, 3)})
    rows.sort(key=lambda r: -r["score"])
    seen, out = set(), []
    for r in rows:
        k = (r["A"], r["B"])
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out[:top]


# ---------------------------------------------------------------- measuring a rendered plan

def vocal_activity(t, hop=0.05):
    """Per hop (local time): RMS of the vocal stem x its fader, and the song's active level."""
    x = (t.stems["vocals"] * t.g["vocals"][:, None]).mean(axis=1)
    n = int(hop * SR)
    m = len(x) // n
    rms = np.sqrt((x[: m * n].reshape(m, n) ** 2).mean(axis=1) + 1e-12)
    raw = t.stems["vocals"].mean(axis=1)
    rr = np.sqrt((raw[: m * n].reshape(m, n) ** 2).mean(axis=1) + 1e-12)
    active = np.percentile(rr[rr > 1e-4], 70) if (rr > 1e-4).any() else 1e-3
    return rms, active


def vocal_overlap(tracks, events, hop=0.05):
    """Seconds where two vocals are both really singing (each above its own song's active
    level - 14 dB) around each transition. Echo throws are not counted (they are not lead)."""
    out = []
    acts = {k: vocal_activity(t, hop) for k, t in tracks.items()}
    for tr, A, B, ts, te in events:
        ra, aa = acts[A.id]
        rb, ab = acts[B.id]
        both = 0
        t = ts - 2 * A.bar_len
        while t < te + 2 * B.bar_len:
            ia, ib = int(A.local(t) / hop), int(B.local(t) / hop)
            va = ra[ia] if 0 <= ia < len(ra) else 0
            vb = rb[ib] if 0 <= ib < len(rb) else 0
            if va > aa * db(-14) and vb > ab * db(-14):
                both += 1
            t += hop
        out.append(round(both * hop, 2))
    return out


def sharp_clash(A, B, ts, te):
    """Like listen.harmonic_clash (same dissonance table) but on note histograms of what is
    actually audible (stems x faders): A's vocal + music vs B's vocal + music."""
    def hist(t, a, b):
        i0, i1 = t.idx(a), t.idx(b)
        if i1 - i0 < SR:
            return None
        x = sum(t.stems[s][i0:i1] * t.g[s][i0:i1, None] for s in ("vocals", "other")).mean(axis=1)
        if np.abs(x).max() < 1e-3:
            return None
        return note_histogram(x.astype(np.float32), top=3)
    ca, cb = hist(A, A.local(ts), A.local(te)), hist(B, B.local(ts), B.local(te))
    if ca is None or cb is None:
        return None
    return round(clash(ca, cb), 3)


def run(plan_path):
    """Build a plan (with these techniques registered), run the critic, then print the vocal
    numbers: lead vocal overlap seconds, harmonic clash, word cut verdicts."""
    from autodj import listen as L
    mix.build(plan_path)
    problems = L.listen(plan_path)
    plan, tracks, events = mix.layout(plan_path)
    ov = vocal_overlap(tracks, events)
    res = []
    for k, (tr, A, B, ts, te) in enumerate(events):
        hc = L.harmonic_clash(A, B, ts, te) if te - ts > 1 else None
        a_cut = L.fader_edges(A, "vocals", A.local(ts - A.bar_len), A.local(te + A.bar_len), rising=False)
        b_in = L.fader_edges(B, "vocals", B.local(ts - B.bar_len), B.local(te + 2 * B.bar_len), rising=True)
        ex = L.describe_exit(A, a_cut) if a_cut is not None else "-"
        en = L.describe_entry(B, b_in) if b_in is not None else "-"
        res.append({"n": k + 1, "technique": tr["technique"], "vocal_overlap_s": ov[k], "harmonic_clash": hc,
                    "sharp_clash": sharp_clash(A, B, ts, te) if te - ts > 1 else None,
                    "a_exit": ex, "b_entry": en,
                    "word_cut": ex.startswith("CHOPS") or en.startswith("ENTERS MID-WORD")})
    name = Path(plan_path).stem
    (ROOT / "mixes" / f"{name}.vocals.json").write_text(json.dumps({"critic_problems": problems, "transitions": res},
                                                                    indent=1))
    print("\n== vocal numbers")
    for r in res:
        print(f"  #{r['n']} {r['technique']}: overlap {r['vocal_overlap_s']}s, clash {r['harmonic_clash']} "
              f"(sharp {r['sharp_clash']}), "
              f"word cut {r['word_cut']}\n     exit: {r['a_exit'][:110]}\n     entry: {r['b_entry'][:110]}")
    return res


def main(args):
    cmd = args[0] if args else "find"
    if cmd == "find":
        rows = find_handoffs(*(args[1:3] if len(args) >= 3 else ("", "")), top=40)
        for r in rows:
            print(f"{r['score']:5.1f} {r['kind']:<6} [{' '.join(r['shared'])}] {r['A'][:26]} bar {r['a_end_bar']} "
                  f"\"...{r['a_line'][-42:]}\"\n        -> {r['B'][:26]} bar {r['b_start_bar']} \"{r['b_line'][:46]}\""
                  f"  | exit {r['a_exit_bar']} entry {r['b_entry_bar']} gap {r['gap_bars']} {r['keys']} "
                  f"{' '.join(r['notes'])}")
    elif cmd == "mashups":
        rows = find_mashups(*(args[1:3] if len(args) >= 3 else ("", "")))
        for r in rows:
            print(f"{r['score']:5.2f} {r['B'][:26]} vocal bar {r['b_bar']} \"{r['b_line'][:40]}\"\n"
                  f"        over {r['A'][:26]} {r['a_how']} instrumental bars {r['a_bars']}  shift {r['shift']:+d} "
                  f"clash {r['clash']} (unshifted {r['clash_no_shift']}) {r['keys']} tempo {r['tempo_gap'] * 100:.1f}%")
    elif cmd == "shift":
        A, a0, a1, B, b0, b1 = args[1:7]
        best, sc = choose_shift(A, (int(a0), int(a1)), B, (int(b0), int(b1)))
        print(f"best pitch_semitones for B: {best:+d}   clash per shift: {sc}")
    elif cmd == "run":
        run(args[1])


if __name__ == "__main__":
    main(sys.argv[1:])
