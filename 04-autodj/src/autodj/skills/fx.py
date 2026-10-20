"""Loops and FX skill: the loop roll done properly, plus echo throw, reverb wash, brake and backspin.

Importing this module registers into autodj.mix.TECHNIQUES (all of them are drops: B is silent
until the overlap ends and lands at te on b_entry_bar, so they also go into autodj.mix.DROPS):

  loop_roll     v2 of the signature move (replaces mix.t_loop_roll; the old one stays as
                "loop_roll_v1"). A word is picked from the lyrics (or given), its attack is found
                on the vocal stem, and every repetition puts that attack exactly on a grid slot:
                1 beat loops gated at the word's end ("the stop play of the word"), then 1/2,
                1/4 (and 1/8) beat stutters of the word's first syllable, under a resonant high
                pass, rising gain, optional pitch rise, optional B build underneath, then B lands.
  echo_throw    A's last word (or A's last beat, everything) into a high passed, tempo synced
                feedback echo armed one beat before the cut; B lands on the next one.
  reverb_wash   A's last bar swells into a big high passed reverb, A cuts on the one and the tail
                washes over B's first beats. For tempo / genre jumps where nothing can overlap.
  brake         A's last 1 or 2 beats slow to a stop like a turntable (or tape) and B slams in.
  backspin      A's last half bar or bar is spun backwards (fast, decaying) and B slams in.

Tools:
  python -m autodj.skills.fx pick <song> <bar>          ranked source words before that bar
  python -m autodj.skills.fx suggest <songA> <songB>    ranked loop roll spots (A word, B landing)
  python -m autodj.skills.fx run plans/skill_fx_x.json  build + critic + FX measurements

Rules (skills/FX.md has the sources and numbers): one loop roll per set (two only if the set is
over 40 minutes, at least 20 minutes apart), max 2 echo throws, 1 reverb wash, 1 brake or
backspin, never two FX transitions in a row. A roll must land on B's drop or hook.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pedalboard as pb
from scipy.signal import butter, sosfilt, sosfiltfilt

from autodj import mix
from autodj.mix import INST, SNAP, STEMS, SR, cut, db, hold, ramp

ROOT = mix.ROOT

STOP = set("""i a the and to of in on it is you me my your we our be so oh yeah ah uh
that this but for with just like cause 'cause its it's i'm im all now up down no yes
do don't dont got get can can't what when where who are was were will gonna wanna
an at as if or by from then than there their they he she his her them us
let's lets yo eh ha hmm mmm ay ayy""".split())
# words a crowd shouts back are great roll sources even if they are "small"
SHOUT = set("hey yeah oh baby tonight go up down now night love party".split())

SCHEDULES = {
    # the Disturbia roll (loved): 4 x 1 beat, 4 x 1/2, 8 x 1/4 = 8 beats (2 bars)
    "short": [(1.0, 4), (0.5, 4), (0.25, 8)],
    # STUDY R4: 8 x 1, 8 x 1/2, 8 x 1/4, 8 x 1/8 = 15 beats + stop (4 bars)
    "hype": [(1.0, 8), (0.5, 8), (0.25, 8), (0.125, 8)],
    # James Hype / DJ Carlo breakdown, condensed to 8 bars: 2 beat loops first (the phrase),
    # then the word, then the stutter. Only with B's build underneath.
    "build": [(2.0, 4), (1.0, 8), (0.5, 8), (0.25, 8), (0.125, 8)],
}


def norm(w):
    return re.sub(r"[^a-z']", "", w.lower()).strip("'")


# ====================================================================================
# words on the vocal stem
# ====================================================================================

def words_local(t):
    """[{w, s, e}] in the track's local (stretched) seconds. Uses mix.load_words for the times
    (so other skills' tempo maps apply) and the lyric file for the text."""
    p = ROOT / "lyrics" / f"{t.name}.json"
    if not p.exists():
        return []
    from autodj.lyrics import clean_words
    raw = clean_words(json.loads(p.read_text())["words"])
    times = mix.load_words(t)
    return [{"w": r["w"], "s": x["s"], "e": x["e"]} for r, x in zip(raw, times)]


def _env(x, hop):
    m = x.mean(axis=1) if x.ndim == 2 else x
    n = len(m) // hop
    if n < 1:
        return np.zeros(1)
    return np.sqrt((m[: n * hop].reshape(n, hop) ** 2).mean(axis=1) + 1e-12)


_VOICED = butter(2, [250, 2500], "band", fs=SR, output="sos")


def syllable_onsets(t, t0, t1):
    """Syllable starts on the vocal stem between local t0 and t1: a dip in the voiced band
    (250 Hz to 2.5 kHz, so sibilants and breaths do not count) followed by a rise of 6 dB or
    more within 30 ms. Returns [(time, rise_db, level_db)]."""
    hop = int(0.005 * SR)
    pad = 0.3
    i0, i1 = t.idx(t0 - pad), t.idx(t1 + pad)
    x = t.stems["vocals"][i0:i1]
    if len(x) < 10 * hop:
        return []
    v = sosfiltfilt(_VOICED, x.mean(axis=1))
    e = 20 * np.log10(_env(v, hop) + 1e-7)
    e = np.convolve(e, np.ones(3) / 3, mode="same")
    top = e.max()
    base = i0 / SR
    out = []
    W = 12  # 60 ms: a sung vowel can take that long to bloom
    j = W
    while j < len(e) - W:
        floor = e[j - W:j + 1].min()
        ahead = e[j:j + W].max()
        if e[j] >= floor + 4 and e[j - 1] < floor + 4 and ahead >= floor + 10 and ahead >= top - 35:
            tt = base + j * 0.005
            if t0 <= tt <= t1:
                out.append((tt, float(ahead - floor), float(ahead)))
            j += 8  # 40 ms before the next syllable can start
            continue
        j += 1
    return out


def _off16(t, tt):
    """Distance from the nearest 16th note line, in 16ths (0 .. 0.5)."""
    q = (tt - t.first_db) / (t.bar_len / 16)
    return abs(q - round(q))


def refine_word(t, w, nxt=None, look=0.09):
    """Where the word really starts and ends on the vocal stem. Whisper is +-50 ms or worse and
    often starts a word inside the previous word's last consonant (Pitbull's "tonight" was
    stamped 95 ms early, on the "-se" of "promise"); a loop that starts there stutters a hiss.
    Attack = the syllable onset near whisper's start that is strongest, closest, and nearest a
    16th note line (singers and rappers land syllables on the 16th grid).
    Returns (attack, end) in local seconds."""
    cands = syllable_onsets(t, w["s"] - look, w["s"] + 0.2)
    if cands:
        def score(c):
            return c[1] - 14 * _off16(t, c[0]) - 25 * abs(c[0] - w["s"])
        att = max(cands, key=score)[0]
    else:
        att = w["s"]
    hop = int(0.005 * SR)
    i0 = t.idx(att)
    i1 = t.idx(max(w["e"] + 0.2, att + 0.3))
    env = _env(t.stems["vocals"][i0:i1], hop)
    if len(env) < 6 or env.max() < 1e-5:
        return att, max(w["e"], att + 0.06)
    peak = env.max()
    # end: after the word's middle, first 30 ms run under 12% of its peak
    mid = int(max(1, 0.5 * (w["e"] - att) / 0.005))
    low = env < 0.12 * peak
    end = max(w["e"], att + 0.06) + 0.05
    for j in range(mid, len(env) - 6):
        if low[j:j + 6].all():
            end = att + j * 0.005
            break
    if nxt is not None and nxt > att + 0.1:
        end = min(end, nxt - 0.01)
    return att, max(end, att + 0.06)


def vocal_events(t, t0, t1, words):
    """Sung onsets Whisper did not write down (held notes, ad libs, "oh"s). Disturbia's loved
    roll looped one of these: the lyric file has no word there, the stem has a loud held vowel."""
    out = []
    for tt, rise, lvl in syllable_onsets(t, t0, t1):
        if any(w["s"] - 0.08 <= tt <= w["e"] for w in words):
            continue
        out.append({"w": "(vocal)", "s": tt, "e": tt + t.bar_len / 4})
    return out


def _db(x):
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9) if len(x) else -120.0


def dominance(t, t0, t1):
    """Vocal stem level minus the music (drums + other) in dB. Disturbia's loved source: +48
    (an acapella moment). Below about +3 the loop must be vocal stem only."""
    i0, i1 = t.idx(t0), t.idx(t1)
    music = t.stems["drums"][i0:i1] + t.stems["other"][i0:i1]
    return _db(t.stems["vocals"][i0:i1]) - _db(music)


def hook_words(t):
    try:
        from autodj.hooks import hook_candidates, words as hw
        out = set()
        for h, _ in hook_candidates(t.name):
            if h:
                out |= hw(h["text"])
        return out
    except Exception:
        return set()


def title_words(t):
    return {norm(x) for x in re.split(r"[_\s]+", t.name) if len(x) > 2}


def pick_word(t, before, window_beats=8, after=None, ranked=False):
    """The rule for choosing what to loop. Scores every word whose attack sits in the window
    before `before` (local seconds):
      + body: up to 1 beat long (a 1/4 beat slice of it must still be the word)
      + vocal dominance over the music (acapella moments are gold)
      + a content or shout word (not "the", "a", "I"), hook / title words more
      + the end of a line (a gap after it): the word the singer leaves hanging
      - another word starting inside its first half beat (the stutter would catch two words)
      - distance from the roll (the word should be the last thing heard)
    Returns the best candidate dict (or the ranked list)."""
    beat = t.bar_len / 4
    ws = words_local(t)
    lo = before - window_beats * beat
    hi = before - 0.25 * beat if after is None else after
    hooks, titles = hook_words(t), title_words(t)
    out = []
    pool = [w for w in ws if lo <= w["s"] <= hi]
    pool += vocal_events(t, lo, hi, ws)
    pool.sort(key=lambda w: w["s"])
    allw = sorted(ws + [w for w in pool if w["w"] == "(vocal)"], key=lambda w: w["s"])
    for w in pool:
        i = allw.index(w)
        nxt = allw[i + 1]["s"] if i + 1 < len(allw) else None
        att, end = refine_word(t, w, nxt)
        dur = (end - att) / beat
        if dur < 0.3:
            continue
        txt = norm(w["w"])
        why = []
        sc = 2 * min(dur, 1.0)
        dom = dominance(t, att, att + min(end - att, beat))
        sc += float(np.clip(dom / 6, -1, 2))
        why.append(f"{dur:.2f} beats, vocal {dom:+.0f} dB over music")
        if w["w"] == "(vocal)":
            # unlabelled: no word bonus, but a held, loud note loops seamlessly
            seg = _env(t.stems["vocals"][t.idx(att):t.idx(att + beat)], int(0.01 * SR))
            if len(seg) > 4 and (seg > 0.5 * seg.max()).mean() > 0.8:
                sc += 1
                why.append("held note")
        elif (txt in STOP or len(txt) <= 2) and txt not in SHOUT:
            sc -= 2
            why.append("filler word")
        if txt in hooks:
            sc += 1.5
            why.append("hook word")
        if txt in titles:
            sc += 1.5
            why.append("title word")
        gap = (nxt - end) / beat if nxt is not None else 9
        if gap >= 0.5 or (nxt is not None and nxt > before):
            sc += 1
            why.append("ends a line")
        if nxt is not None and nxt - att < 0.5 * beat:
            sc -= 1.5
            why.append("next word inside half a beat")
        dist = (before - att) / beat
        sc -= 0.25 * max(0.0, dist - 1.5)
        out.append({"w": w["w"], "att": att, "end": end, "s": w["s"], "e": w["e"], "beats": dur,
                    "dom": dom, "score": round(sc, 2), "why": ", ".join(why), "dist_beats": dist})
    out.sort(key=lambda c: -c["score"])
    if ranked:
        return out
    return out[0] if out else None


# ====================================================================================
# small DSP helpers
# ====================================================================================

def _fade(chunk, fin=0.004, fout=0.012):
    n = len(chunk)
    a, b = min(int(fin * SR), n // 3), min(int(fout * SR), n // 3)
    if a > 1:
        chunk[:a] *= np.linspace(0, 1, a, dtype=np.float32)[:, None]
    if b > 1:
        chunk[-b:] *= np.linspace(1, 0, b, dtype=np.float32)[:, None]
    return chunk


def _resample(x, n_out):
    """Squeeze or stretch x to n_out samples (pitch moves with speed, like key lock off)."""
    if len(x) == n_out or len(x) < 2:
        return x[:n_out]
    pos = np.linspace(0, len(x) - 1, n_out)
    return np.stack([np.interp(pos, np.arange(len(x)), x[:, c]) for c in range(x.shape[1])],
                    axis=1).astype(np.float32)


def varispeed(src, start, rate):
    """Read `src` from sample `start` with a per output sample playback rate (negative =
    backwards). Turntable physics: position is the running sum of the speed."""
    pos = start + np.concatenate([[0.0], np.cumsum(rate[:-1])])
    pos = np.clip(pos, 0, len(src) - 1)
    idx = np.arange(len(src))
    return np.stack([np.interp(pos, idx, src[:, c]) for c in range(src.shape[1])], axis=1).astype(np.float32)


def hp(x, hz, order=2):
    return sosfilt(butter(order, hz, "high", fs=SR, output="sos"), x, axis=0).astype(np.float32)


def echo_tail(src, delay_s, feedback=0.65, hp_hz=350, tail_s=2.0, level=0.8, darken=True):
    """A DJ mixer echo with the dry signal removed: repeats every delay_s, each one
    feedback times quieter, high passed (no kick or bass in the tail) and a little darker
    and thinner each time, like a tape echo."""
    x = hp(src, hp_hz, 2)
    d = max(1, int(delay_s * SR))
    n = len(x) + int(tail_s * SR)
    out = np.zeros((n, src.shape[1]), dtype=np.float32)
    g, k = level, 1
    lp_sos = butter(1, 6000, "low", fs=SR, output="sos")
    rep = x
    while k * d < n and g > 0.01:
        m = min(len(rep), n - k * d)
        out[k * d:k * d + m] += rep[:m] * g
        if darken:
            rep = sosfilt(lp_sos, hp(rep, hp_hz * 1.15, 1), axis=0).astype(np.float32)
        g *= feedback
        k += 1
    # gentle fade so the last repeats melt rather than stop
    env = np.linspace(1, 0, n) ** 1.2
    return out * env[:, None].astype(np.float32)


def reverb_tail(src, decay=0.92, hp_hz=300, tail_s=4.0, damping=0.35):
    x = hp(src, hp_hz, 2)
    buf = np.zeros((len(x) + int(tail_s * SR), x.shape[1]), dtype=np.float32)
    buf[:len(x)] = x
    rv = pb.Pedalboard([pb.Reverb(room_size=decay, damping=damping, wet_level=1.0, dry_level=0.0, width=1.0)])
    return rv(buf.T, SR).T.astype(np.float32)


def _place_fx(t, at_local, audio, gain=1.0):
    t.fx.append((at_local, (audio * gain).astype(np.float32)))


def _rms(x):
    return float(np.sqrt(np.mean(x ** 2) + 1e-12)) if len(x) else 0.0


# ====================================================================================
# landings: a roll or throw only works if B lands on something big
# ====================================================================================

def landing(B_or_name, bar):
    """How big is B's moment at `bar`? Section energy jump, B's vocal on the one, hook nearby.
    Disturbia -> car crash bar 32: +5.1 dB jump, vocal 0.16 beat after the one = a drop."""
    name = B_or_name if isinstance(B_or_name, str) else B_or_name.name
    a = json.loads((ROOT / "analysis" / f"{name}.json").read_text())
    secs = a["sections"]
    jump, label = 0.0, None
    for i, s in enumerate(secs):
        if abs(s["start_bar"] - bar) <= 1 and i > 0:
            jump, label = s["energy_db"] - secs[i - 1]["energy_db"], s["label"]
    beat = a["beat_period"]
    t_one = a["first_downbeat"] + bar * 4 * beat
    v_on = None
    p = ROOT / "lyrics" / f"{name}.json"
    if p.exists():
        from autodj.lyrics import clean_words
        for w in clean_words(json.loads(p.read_text())["words"]):
            if -1.5 * beat <= w["start"] - t_one <= 1.0 * beat:
                v_on = (w["start"] - t_one) / beat
                break
    hooks = json.loads((ROOT / "analysis" / "_hooks.json").read_text()).get(name, {})
    hook = any(abs(h - bar) <= 1 for h in hooks.get("bars", []))
    big = jump >= 3 or hook or (label == "high" and jump >= 1.5)
    return {"jump_db": round(jump, 1), "label": label, "vocal_on_beats": None if v_on is None else round(v_on, 2),
            "hook": hook, "big": big}


# ====================================================================================
# loop roll v2
# ====================================================================================

def _fit_schedule(sched, beats, stop_beats):
    """Scale the first stage so the schedule fills `beats` (minus the stop)."""
    sched = [list(s) for s in sched]
    total = sum(l * n for l, n in sched) + stop_beats
    extra = beats - total
    l0 = sched[0][0]
    sched[0][1] = max(1, int(round(sched[0][1] + extra / l0)))
    # if still off (short rolls), trim from the front stages
    total = sum(l * n for l, n in sched) + stop_beats
    while total > beats + 1e-6 and len(sched) > 1:
        if sched[0][1] > 1:
            sched[0][1] -= 1
        else:
            sched.pop(0)
        total = sum(l * n for l, n in sched) + stop_beats
    return [tuple(s) for s in sched]


def t_loop_roll_v2(A, B, ts, te, bars, o):
    """The signature roll (STUDY R4, rebuilt from the Disturbia analysis).
    opts:
      word        "auto" (default) | {"bar": 79.75} (A's bar of the word's attack) | {"text": "tonight"}
      window_beats how far back to look for the word (default 8)
      schedule    "short" (2 bars, the Disturbia one) | "hype" (4) | "build" (8) | [[beats, n], ...]
      src         "auto" | "vocals" (stem loop) | "all" (vocals + music, like a deck loop)
      a_music     "auto" | "cut" | "fade" | "loop": what A's instrumental does under a vocal loop
      gate        True: 1 and 2 beat loops play the word then stop (the stop play)
      hpf         [f0, f1, Q] resonant high pass on the roll, default [120, 1500, 1.5]
      gain_db     [g0, g1] loop level relative to A's last 2 bars, default [-2, 1]
      pitch_rise  semitones reached by the last stage (key lock off feel), default 0
      b_under     False | True | "auto": B's bars before the landing play underneath, lows and
                  vocal out, low pass opening (needs B's pre drop to be a build)
      b_level     B's level under the roll (default 0.6)
      stop_beats  silence before the landing (default 0 short, 0.5 hype/build)
      tail        "none" | "echo": the last slice rings into B through a 1/2 beat echo
      riser       noise riser level (default 0.05, 0 when B's build is under)
      pickup      True: if B's vocal starts before its one (drop on the four), the roll stops
                  there and B's pickup is heard
    """
    a, b = A.local, B.local
    beat = A.bar_len / 4
    t0, t1 = a(ts), a(te)

    # ---- the word
    wopt = o.get("word", "auto")
    cand = None
    if isinstance(wopt, dict) and "bar" in wopt:
        s = A.bar(wopt["bar"])
        ws = words_local(A)
        near = [w for w in ws if abs(w["s"] - s) < 0.6 * beat]
        w = min(near, key=lambda w: abs(w["s"] - s)) if near else {"w": "?", "s": s, "e": s + beat}
        i = ws.index(w) if w in ws else -1
        nxt = ws[i + 1]["s"] if 0 <= i < len(ws) - 1 else None
        att, end = refine_word(A, w, nxt) if near else (s, s + beat)
        if o.get("exact_bar"):
            att = s
        cand = {"w": w["w"], "att": att, "end": end, "beats": (end - att) / beat,
                "dom": dominance(A, att, att + beat), "why": "given"}
    else:
        ranked = pick_word(A, t0 + 0.5 * beat, o.get("window_beats", 8), ranked=True)
        if isinstance(wopt, dict) and "text" in wopt:
            ranked = [c for c in ranked if norm(c["w"]) == norm(wopt["text"])] or ranked
        cand = ranked[0] if ranked else None
    if cand is None:  # no lyrics: the beat before the roll, like v1
        cand = {"w": "?", "att": t0 - beat, "end": t0, "beats": 1.0, "dom": dominance(A, t0 - beat, t0),
                "why": "no lyrics, beat before the roll"}
    att, end = cand["att"], cand["end"]

    # ---- where the roll starts: the first beat at least half a beat after the attack, so the
    # word is sung once in time and then gets stuck (Disturbia: attack on the beat before)
    k = np.ceil((att - A.first_db) / beat + 0.5 - 1e-6)
    rs = A.first_db + k * beat
    rs = min(rs, t1 - 2 * beat)
    beats = int(round((t1 - rs) / beat * 8)) / 8

    name = o.get("schedule", "short" if bars <= 2.5 else ("hype" if bars <= 4.5 else "build"))
    sched = SCHEDULES[name] if isinstance(name, str) else [tuple(s) for s in name]
    stop_beats = o.get("stop_beats", 0.0 if name == "short" else 0.5)
    sched = _fit_schedule(sched, beats, stop_beats)

    # ---- source mode
    src_mode = o.get("src", "auto")
    on_grid = abs(((att - A.first_db) / beat) - round((att - A.first_db) / beat)) < 0.12
    if src_mode == "auto":
        src_mode = "all" if (cand["dom"] >= 15 and on_grid) else "vocals"
    b_under = o.get("b_under", "auto")
    lb = landing(B, _b_entry_bar(B, te))
    if b_under == "auto":
        b_under = name != "short" and lb["big"]
    a_music = o.get("a_music", "auto")
    if a_music == "auto":
        a_music = "loop" if src_mode == "all" else ("cut" if b_under else "fade")

    loop_stems = ["vocals"] + (["drums", "other"] if src_mode == "all" else [])
    if a_music == "loop" and src_mode != "all":
        loop_stems = ["vocals", "drums", "other"]
    i_att = A.idx(att)
    gate_n = max(int((end - att + 0.02) * SR), int(0.06 * SR))

    # loop level: matched to A's last 2 bars (a vocal stem alone is quieter than the mix)
    # the word keeps the loudness it had in the full mix: in an acapella moment that is its own
    # level (gain ~1, like v1); over a busy track the stem alone gets back what the music gave
    seg = slice(i_att, i_att + min(gate_n, int(beat * SR)))
    # continuity: never quieter than what the listener heard in the beat before the roll
    ref = max(_rms(A.audio[seg]), _rms(A.audio[A.idx(rs - beat):A.idx(rs)]))
    word_lvl = _rms(sum(A.stems[s][seg] for s in loop_stems))
    g0_db, g1_db = o.get("gain_db", [0.0, 1.0])
    base = float(np.clip(ref / (word_lvl + 1e-9), db(-3), db(6))) if word_lvl > 0 else 1.0

    # B pickup (drop on the four): roll stops where B's first word begins
    stop_at = t1 - stop_beats * beat
    b_pick = None
    if o.get("pickup", True):
        bw = words_local(B)
        bt = b(te)
        pre = [w for w in bw if bt - 1.5 * beat <= w["s"] < bt - 0.05 and w["e"] > bt - 0.1]
        if pre:
            b_pick = pre[0]["s"] - 0.03
            stop_at = min(stop_at, A.local(B.offset + b_pick))

    # ---- write the roll into A's stems
    keep_src = {s: A.stems[s].copy() for s in STEMS}
    i_rs, i_end = A.idx(rs), A.idx(t1 + 0.05)
    for s in loop_stems:
        A.stems[s][i_rs:i_end] = 0
    # silence the singer between the word and the roll (the next words would step on it)
    A.stems["vocals"][A.idx(end + 0.01):i_rs] *= 0
    pos = rs
    n_st = len(sched)
    semis_top = o.get("pitch_rise", 0)
    slots = []
    for si, (L, n) in enumerate(sched):
        semis = semis_top * si / max(1, n_st - 1) if semis_top else 0
        rate = 2 ** (semis / 12)
        n_slot = int(round(L * beat * SR))
        gated = o.get("gate", True) and L >= 1.0
        stage_gain = db(g0_db + (g1_db - g0_db) * si / max(1, n_st - 1))
        for r in range(n):
            if pos >= stop_at - 1e-4:
                break
            i_pos = A.idx(pos)
            take = min(n_slot, gate_n) if gated else n_slot
            take = min(take, A.idx(stop_at) - i_pos)
            if take <= 8:
                break
            src_n = int(take * rate)
            for s in loop_stems:
                ch = keep_src[s][i_att:i_att + src_n].copy()
                if rate != 1:
                    ch = _resample(ch, take)
                ch = _fade(ch, 0.003, 0.012 if gated else 0.004)
                m = min(len(ch), A.n - i_pos)
                A.stems[s][i_pos:i_pos + m] = ch[:m] * base * stage_gain
            slots.append((pos, L, take / SR))
            pos += L * beat
    A.refresh()

    # ---- A's music, filter, riser
    cut(A, ["bass"], rs, 0)
    if a_music == "cut":
        cut(A, ["drums", "other"], rs, 0)
    elif a_music == "fade":
        ramp(A, ["drums", "other"], rs, rs + min(4 * beat, (t1 - rs) / 2), 1, 0)
    f0, f1, q = o.get("hpf", [120.0, 1500.0, 1.5])
    A.sweeps.append((rs, t1, f0, f1, "high", q))
    rl = o.get("riser", 0.0 if b_under else 0.08)
    if rl:
        A.fx.append((rs, mix.riser(t1 - rs, rl)))
    if o.get("tail") == "echo" and slots:
        p_last, L_last, d_last = slots[-1]
        ch = sum(A.stems[s][A.idx(p_last):A.idx(p_last + d_last)] for s in loop_stems)
        _place_fx(A, p_last + d_last, echo_tail(ch, beat / 2, 0.6, 500, 2 * beat, 0.6))
    cut(A, STEMS, stop_at if stop_at < t1 else t1, 0)

    # ---- B: silent (or its build underneath), then the landing
    hold(B, STEMS, b(ts), b(te), 0)
    if b_under:
        lvl = o.get("b_level", 0.6)
        ramp(B, ["drums", "other"], b(A.offset + rs), b(A.offset + rs) + beat, 0, lvl)
        B.sweeps.append((b(A.offset + rs), b(te), o.get("b_lpf0", 300.0), 12000.0, "low", 1.2))
    ramp(B, STEMS, b(te), b(te) + 0.005, 0, 1)
    hold_to = b(te)
    if b_pick is not None:
        hold_to = b_pick
        B.g["vocals"][B.idx(b_pick):B.idx(b(te))] = 1.0
    A.fx_lock = ts
    B.fx_b_hold = (b(ts), hold_to)
    A.fx_report = {"fx": "loop_roll", "word": cand["w"], "attack_local": att, "end_local": end,
                   "word_beats": round(cand["beats"], 2), "dominance_db": round(cand["dom"], 1),
                   "why": cand.get("why", ""), "roll_start": rs, "te": t1, "stop_at": stop_at,
                   "schedule": sched, "src": src_mode, "a_music": a_music, "b_under": bool(b_under),
                   "slots": slots, "landing": lb, "base_gain_db": round(20 * np.log10(base), 1),
                   "b_pickup": b_pick is not None}


def _b_entry_bar(B, te):
    """B's bar number at timeline te (te is where B's b_entry_bar lands for drops)."""
    return round((B.local(te) - B.first_db) / B.bar_len)


# ====================================================================================
# echo throw
# ====================================================================================

def t_echo_throw(A, B, ts, te, bars, o):
    """STUDY R8 done right (DJcity / Digital DJ Tips / PDot): the echo is armed ONE BEAT BEFORE
    the cut, so the tail repeats the last word (or the last beat) instead of nothing; the echo
    is high passed (no kick or bass in the tail), 1 beat delay, feedback 0.65 to 0.7; A is out
    on the one and B lands on its biggest part. Plan: a_exit_bar = the bar after A's line ends,
    bars = 1 or 2 (A plays normally in the overlap until the cut), b_entry_bar = B's big part.
    opts:
      source      "word" (default: the picked word, vocal stem only) | "all" (A's last beat, all
                  but the lows, the classic echo out) | "vocals" (A's last beat of vocal)
      word        "auto" | {"bar": x} | {"text": "tonight"}
      delay_beats 1 (default) | 0.75 | 0.5
      feedback    0.65   hp_hz 350   level 0.8   tail_beats 6
      cut         "word": A goes out right after the word (default for source word)
                  "one": A plays to te then goes
      sweep       resonant HPF on A's last bar before the cut (default True)
    """
    a, b = A.local, B.local
    beat = A.bar_len / 4
    t1 = a(te)
    src = o.get("source", "word")
    delay = o.get("delay_beats", 1.0) * beat
    fb, hz, lvl = o.get("feedback", 0.65), o.get("hp_hz", 350), o.get("level", 0.8)
    tail = o.get("tail_beats", 6) * beat
    cut_at = t1
    word = None
    if src == "word":
        wopt = o.get("word", "auto")
        ranked = pick_word(A, t1 + 0.25 * beat, o.get("window_beats", 6), ranked=True)
        if isinstance(wopt, dict) and "text" in wopt:
            ranked = [c for c in ranked if norm(c["w"]) == norm(wopt["text"])] or ranked
        if isinstance(wopt, dict) and "bar" in wopt:
            s = A.bar(wopt["bar"])
            ranked = sorted(ranked, key=lambda c: abs(c["s"] - s))
        word = ranked[0] if ranked else None
    if word is not None:
        s0, s1 = word["att"] - 0.01, word["end"] + 0.03
        chunk = A.stems["vocals"][A.idx(s0):A.idx(s1)].copy()
        if o.get("cut", "word") == "word":
            cut_at = min(t1, s1)
        # the repeats fall on the word's own beat grid: first repeat one delay after the attack
        place = s0 + delay
    else:
        stems = ["vocals"] if src == "vocals" else ["vocals", "drums", "other"]
        s0, s1 = t1 - beat, t1
        chunk = sum(A.stems[s][A.idx(s0):A.idx(s1)] for s in stems)
        place = s0 + delay
    wet = echo_tail(chunk, delay, fb, hz, tail, lvl)
    # echo_tail's first repeat is at +delay inside its buffer, so place the buffer at s0
    _place_fx(A, s0, wet)
    if o.get("sweep", True):
        A.sweeps.append((max(a(ts), cut_at - A.bar_len), cut_at, 40.0, 350.0, "high", 1.4))
    ramp(A, ["bass"], cut_at - 2 * beat, cut_at, 1, 0.4)
    cut(A, STEMS, cut_at, 0)
    hold(B, STEMS, b(ts), b(te), 0)
    ramp(B, STEMS, b(te), b(te) + 0.005, 0, 1)
    A.fx_lock = ts
    B.fx_b_hold = (b(ts), b(te))
    if o.get("pickup", True):
        bw = words_local(B)
        pre = [w for w in bw if b(te) - 1.5 * beat <= w["s"] < b(te) - 0.05 and w["e"] > b(te) - 0.1]
        if pre and pre[0]["s"] > B.local(A.offset + cut_at):
            B.fx_b_hold = (b(ts), pre[0]["s"] - 0.03)
            B.g["vocals"][B.idx(pre[0]["s"] - 0.03):B.idx(b(te))] = 1.0
    A.fx_report = {"fx": "echo_throw", "word": word["w"] if word else None, "cut_local": cut_at,
                   "attack_local": word["att"] if word else s0, "delay_beats": delay / beat,
                   "feedback": fb, "hp_hz": hz, "te": t1, "landing": landing(B, _b_entry_bar(B, te))}


# ====================================================================================
# reverb wash
# ====================================================================================

def t_reverb_wash(A, B, ts, te, bars, o):
    """The wash out (Mixgraph, DJ Carlo level 3, PDot): A's reverb send swells over its last
    bar (wet 0 -> 1, high passed at 300 Hz so the wash has no low end), A's lows ease off, A
    is cut on the one and the tail decays over B's first beats, ducked so B's drop punches
    through. For tempo or genre jumps (no beat overlap possible) and big emotional exits.
    opts: decay 0.92 (room size), swell_beats 4, hp_hz 300, level 0.9, tail_beats 8,
          duck_db -6 (tail level once B is in), source "all" | "vocals", freeze False
    """
    a, b = A.local, B.local
    beat = A.bar_len / 4
    t1 = a(te)
    sw = o.get("swell_beats", 4) * beat
    stems = ["vocals"] if o.get("source") == "vocals" else ["vocals", "drums", "other"]
    s0 = t1 - sw
    send = sum(A.stems[s][A.idx(s0):A.idx(t1)] for s in stems).astype(np.float32)
    send *= (np.linspace(0, 1, len(send)) ** 1.5)[:, None].astype(np.float32)
    tail_s = o.get("tail_beats", 8) * beat
    if o.get("freeze"):
        rv = pb.Pedalboard([pb.Reverb(room_size=1.0, damping=0.3, wet_level=1.0, dry_level=0.0, freeze_mode=1.0)])
        buf = np.zeros((len(send) + int(tail_s * SR), 2), dtype=np.float32)
        buf[:len(send)] = hp(send, o.get("hp_hz", 300))
        wet = rv(buf.T, SR).T.astype(np.float32)
    else:
        wet = reverb_tail(send, o.get("decay", 0.92), o.get("hp_hz", 300), tail_s)
    # level: the wash should sit near A's own level at the cut, then duck under B
    ref = _rms(A.audio[A.idx(s0):A.idx(t1)])
    wl = _rms(wet[int(sw * SR) - int(0.5 * SR):int(sw * SR)]) + 1e-9
    wet *= float(np.clip(o.get("level", 0.9) * ref / wl, 0.05, 6))
    n = len(wet)
    env = np.ones(n, dtype=np.float32)
    k1 = int(sw * SR)
    duck = db(o.get("duck_db", -6))
    nd = int(0.25 * beat * SR)
    env[k1:k1 + nd] = np.linspace(1, duck, min(nd, n - k1))[: len(env[k1:k1 + nd])]
    env[k1 + nd:] = duck * np.linspace(1, 0, max(1, n - k1 - nd)) ** 1.5
    wet *= env[:, None]
    _place_fx(A, s0, wet)
    A.sweeps.append((s0, t1, 30.0, o.get("max_hz", 500.0), "high", 1.3))
    ramp(A, ["bass"], s0, t1, 1, 0.3)
    cut(A, STEMS, t1, 0)
    hold(B, STEMS, b(ts), b(te), 0)
    ramp(B, STEMS, b(te), b(te) + 0.005, 0, 1)
    A.fx_lock = ts
    B.fx_b_hold = (b(ts), b(te))
    A.fx_report = {"fx": "reverb_wash", "te": t1, "swell_from": s0, "landing": landing(B, _b_entry_bar(B, te))}


# ====================================================================================
# brake and backspin
# ====================================================================================

def t_brake(A, B, ts, te, bars, o):
    """Turntable stop (bonedo, Crossfader j9Ky8zpsqvY, Slex): press stop on beat 3 (2 beat
    brake) or beat 4 (1 beat) of A's last bar; the platter slows to zero exactly at the one;
    lows are cut first so the slowing bass does not mud the drop. B slams on the one.
    opts: beats 2 | 1 (default 2), curve 1.6 (>1 = holds speed then drops, like a real
          platter; 1 = linear tape stop), stems "all" | "vocals" (stop only the vocal),
          low_cut True"""
    a, b = A.local, B.local
    beat = A.bar_len / 4
    t1 = a(te)
    nb = o.get("beats", 2)
    s0 = t1 - nb * beat
    n = int(nb * beat * SR)
    x = np.linspace(0, 1, n)
    rate = (1 - x) ** o.get("curve", 1.6)
    stems = ["vocals"] if o.get("stems") == "vocals" else STEMS
    i0 = A.idx(s0)
    for s in stems:
        out = varispeed(A.stems[s], i0, rate)
        # a stopped platter fades out the last few ms (it is inaudible below ~10% speed anyway)
        out *= np.clip(rate * 6, 0, 1)[:, None].astype(np.float32)
        A.stems[s][i0:i0 + n] = out[: A.n - i0]
    A.refresh()
    if o.get("low_cut", True):
        ramp(A, ["bass"], s0, s0 + 0.5 * beat, 1, 0.25)
    cut(A, STEMS, t1, 0)
    hold(B, STEMS, b(ts), b(te), 0)
    ramp(B, STEMS, b(te), b(te) + 0.005, 0, 1)
    A.fx_lock = ts
    B.fx_b_hold = (b(ts), b(te))
    A.fx_report = {"fx": "brake", "te": t1, "from": s0, "beats": nb, "landing": landing(B, _b_entry_bar(B, te))}


def t_backspin(A, B, ts, te, bars, o):
    """Backspin (bonedo, Rob Swift): low EQ cut first, then on beat 1 or 3 of A's last bar the
    record is pulled back fast (about 3 to 4x reverse) and slips to a stop by the one; a high
    pass rides along so the spin is a whoosh, not a rumble. B is already cued and slams in.
    opts: beats 2 (default, starts on beat 3) | 4 (beat 1), speed 3.5, hp True"""
    a, b = A.local, B.local
    beat = A.bar_len / 4
    t1 = a(te)
    nb = o.get("beats", 2)
    s0 = t1 - nb * beat
    n = int(nb * beat * SR)
    x = np.linspace(0, 1, n)
    sp = o.get("speed", 3.5)
    # hand pull: speed ramps from +1 through 0 to -sp in ~60 ms, then decays (friction)
    pull = int(0.06 * SR)
    rate = np.empty(n)
    rate[:pull] = np.linspace(1, -sp, pull)
    rate[pull:] = -sp * np.exp(-3.2 * x[pull:] / x[-1]) * (1 - x[pull:]) ** 0.5
    i0 = A.idx(s0)
    for s in STEMS:
        out = varispeed(A.stems[s], i0, rate)
        env = np.clip(np.abs(rate) * 4, 0, 1) * np.linspace(1, 0.6, n)
        A.stems[s][i0:i0 + n] = (out * env[:, None])[: A.n - i0]
    A.refresh()
    ramp(A, ["bass"], s0 - beat, s0, 1, 0.2)
    if o.get("hp", True):
        A.sweeps.append((s0, t1, 60.0, 900.0, "high", 1.0))
    cut(A, STEMS, t1, 0)
    hold(B, STEMS, b(ts), b(te), 0)
    ramp(B, STEMS, b(te), b(te) + 0.005, 0, 1)
    A.fx_lock = ts
    B.fx_b_hold = (b(ts), b(te))
    A.fx_report = {"fx": "backspin", "te": t1, "from": s0, "beats": nb, "landing": landing(B, _b_entry_bar(B, te))}


# ====================================================================================
# registration
# ====================================================================================

_V1 = mix.TECHNIQUES.get("loop_roll_v1") or mix.t_loop_roll
_ORIG_RESPECT = getattr(mix.respect_words, "_fx_orig", mix.respect_words)


def respect_words(A, B, ts, te, skip_a=False, pickup_beats=1.5):
    """mix.respect_words, but it leaves an FX transition's outgoing side alone (the FX already
    decided where A's words stop; lyric times no longer match a looped or slowed vocal) and keeps
    B's vocal shut until the FX says B may sing."""
    if getattr(A, "fx_lock", None) is not None and abs(A.fx_lock - ts) < 1e-3:
        skip_a = True
    _ORIG_RESPECT(A, B, ts, te, skip_a=skip_a, pickup_beats=pickup_beats)
    hb = getattr(B, "fx_b_hold", None)
    if hb is not None and getattr(A, "fx_lock", None) is not None and abs(A.fx_lock - ts) < 1e-3:
        B.g["vocals"][B.idx(hb[0]):B.idx(hb[1])] = 0


respect_words._fx_orig = _ORIG_RESPECT
mix.respect_words = respect_words

mix.TECHNIQUES.update({"loop_roll": t_loop_roll_v2, "loop_roll_v1": _V1, "echo_throw": t_echo_throw,
                       "reverb_wash": t_reverb_wash, "brake": t_brake, "backspin": t_backspin})
mix.DROPS.update({"loop_roll", "loop_roll_v1", "echo_throw", "reverb_wash", "brake", "backspin"})


# ====================================================================================
# planning helpers (pure readers of analysis/ lyrics/ stems/)
# ====================================================================================

class _Probe:
    """Just enough of a Track to run pick_word on an unstretched song (local = song seconds)."""

    def __init__(self, name, around_bar=None):
        import soundfile as sf
        self.name = name
        self.a = json.loads((ROOT / "analysis" / f"{name}.json").read_text())
        self.bar_len = 4 * self.a["beat_period"]
        self.first_db = self.a["first_downbeat"]
        self.c0, self.ratio = 0.0, 1.0
        self.stems = {s: sf.read(ROOT / "stems" / name / f"{s}.flac", dtype="float32", always_2d=True)[0]
                      for s in STEMS}
        self.n = min(len(v) for v in self.stems.values())

    def bar(self, k):
        return self.first_db + k * self.bar_len

    def idx(self, t):
        return int(np.clip(round(t * SR), 0, self.n))


def suggest(a_name, b_name, top=8):
    """Ranked loop roll spots: A's best word in the 2 bars before each phrase line (4 bar grid),
    B's big landings. Score = word score + landing bonus + drop swap bonus (A's own drop or
    section change sits at the exit: the roll replaces A's build)."""
    A, Bn = _Probe(a_name), b_name
    a = A.a
    rows = []
    landings = []
    bA = json.loads((ROOT / "analysis" / f"{Bn}.json").read_text())
    for s in bA["sections"]:
        L = landing(Bn, s["start_bar"])
        if L["big"]:
            landings.append((s["start_bar"], L))
    for h in json.loads((ROOT / "analysis" / "_hooks.json").read_text()).get(Bn, {}).get("bars", []):
        k = int(round(h))
        L = landing(Bn, k)
        if L["big"] and all(abs(k - x[0]) > 1 for x in landings):
            landings.append((k, L))
    a_secs = {s["start_bar"]: s for s in a["sections"]}
    for exit_bar in range(8, a["n_bars"] - 2, 2):
        c = pick_word(A, A.bar(exit_bar - 2) + 0.5 * A.bar_len / 4, 8)
        if not c or c["score"] < 2.5:
            continue
        drop_swap = exit_bar in a_secs and a_secs[exit_bar]["label"] == "high"
        rows.append((c["score"] + (1.5 if drop_swap else 0), exit_bar, c, drop_swap))
    rows.sort(key=lambda r: -r[0])
    out = []
    for sc, eb, c, ds in rows[:top]:
        out.append({"score": round(sc, 2), "a_exit_bar": eb, "word": c["w"], "word_bar": round((c["att"] - A.first_db) / A.bar_len, 2),
                    "why": c["why"] + (", drop swap (A's own drop is here)" if ds else ""),
                    "b_landings": [(k, L["jump_db"], L["hook"]) for k, L in landings[:6]]})
    return out


def _cli_pick(name, bar):
    A = _Probe(name)
    for c in pick_word(A, A.bar(float(bar)), 8, ranked=True)[:8]:
        print(f"{c['score']:6.2f}  '{c['w']}' attack bar {(c['att'] - A.first_db) / A.bar_len:7.2f}  "
              f"({c['why']}; {c['dist_beats']:.1f} beats before)")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "pick":
        _cli_pick(sys.argv[2], sys.argv[3])
    elif cmd == "suggest":
        for r in suggest(sys.argv[2], sys.argv[3]):
            print(json.dumps(r))
    elif cmd == "run":
        from autodj.skills.run_fx import main
        main(sys.argv[2:])
    else:
        print(__doc__)
