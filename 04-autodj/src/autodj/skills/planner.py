"""Plan a set automatically: order the songs for an energy arc, then pick for every pair
where A leaves, where B lands and how they meet. Output is a plan JSON mix.py renders as is.

Rules (STRUCTURE.md has the sources):
  - every song plays at least a verse and a chorus (75 to 150 s, aim ~110 s): no 30 s medleys
  - A leaves after chorus 1 or chorus 2 (never before or inside a chorus), on a phrase line,
    never mid-line: no sung line may span the exit
  - B lands on something recognisable (chorus, drop, verse 1, pre-chorus) at the top of a line
  - technique family from tempo zone + key: eq_blend when both are in one tempo zone and the
    keys are Camelot neighbours; out_by_one when the keys are 2 apart; slam / cut across
    tempo zones or clashing keys; one loop_roll per set at most, only on a strong word
  - songs are read on the corrected grid (analysis/structure/fixed/*.json)

usage:
  python -m autodj.skills.planner plan OUT.json song_stem ... [--keep-order] [--title T]
  python -m autodj.skills.planner set05 OUT.json        # set05's songs, order optimised
  python -m autodj.skills.planner pick OUT.json K must_stem ...   # choose K songs incl. these
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

from .structure import CACHE, ROOT, load_structure, load_words, tokens

PRETTY = {
    "Usher_DJ_Got_Us_Fallin_In_Love": "Usher - DJ Got Us Fallin' In Love",
    "Katy_Perry_Last_Friday_Night": "Katy Perry - Last Friday Night",
    "Katy_Perry_Hot_N_Cold": "Katy Perry - Hot N Cold",
    "Rihanna_We_Found_Love": "Rihanna - We Found Love",
    "Zedd_Clarity": "Zedd - Clarity",
    "Pitbull_Give_Me_Everything": "Pitbull - Give Me Everything",
    "Justin_Bieber_Beauty_And_A_Beat": "Justin Bieber - Beauty And A Beat",
    "Calvin_Harris_Feel_So_Close": "Calvin Harris - Feel So Close",
    "The_Black_Eyed_Peas_I_Gotta_Feeling": "Black Eyed Peas - I Gotta Feeling",
    "Swedish_House_Mafia_Dont_You_Worry_Child": "Swedish House Mafia - Don't You Worry Child",
    "CHRYSTAL_The_Days_Notion_Remix": "CHRYSTAL - The Days (Notion Remix)",
    "Rihanna_Disturbia_Blair_Muir_Remix": "Rihanna - Disturbia (Blair Muir Remix)",
    "jigitz_Charlotte_Plank_car_crash": "jigitz, Charlotte Plank - car crash",
    "The_Killers_Mr_Brightside": "The Killers - Mr. Brightside",
    "Maroon_5_Payphone": "Maroon 5 - Payphone",
    "Bad_Bunny_Titi_Me_Pregunto": "Bad Bunny - Titi Me Pregunto",
}
SET05 = ["Usher_DJ_Got_Us_Fallin_In_Love", "Katy_Perry_Last_Friday_Night", "Rihanna_We_Found_Love",
         "Zedd_Clarity", "Pitbull_Give_Me_Everything", "Justin_Bieber_Beauty_And_A_Beat",
         "Calvin_Harris_Feel_So_Close", "The_Black_Eyed_Peas_I_Gotta_Feeling",
         "Swedish_House_Mafia_Dont_You_Worry_Child", "CHRYSTAL_The_Days_Notion_Remix",
         "Rihanna_Disturbia_Blair_Muir_Remix", "jigitz_Charlotte_Plank_car_crash", "The_Killers_Mr_Brightside"]

PLAY_MIN, PLAY_AIM, PLAY_MAX = 75.0, 110.0, 150.0
ZONE_SPREAD = 1.085  # songs whose tempos are within 8.5 % share one play tempo (max stretch ~ +-4 to 7 %)


# ---------------------------------------------------------------- song model

class Song:
    def __init__(self, stem):
        self.stem = stem
        self.id = PRETTY.get(stem, stem.replace("_", " "))
        self.S, self.V = load_structure(stem)
        fixed = CACHE / "fixed" / f"{stem}.json"
        self.analysis_path = str(fixed.relative_to(ROOT))
        self.a = json.loads(fixed.read_text())
        self.bpm = self.a["bpm"]
        self.camelot = self.a["camelot"]
        self.n = self.a["n_bars"]
        self.bp = self.a["beat_period"]
        self.f = self.a["first_downbeat"]
        self.sections = self.S["sections"]
        self.lines = self.S["lines"]
        self.bounds = sorted(set(self.S["phrase_bounds"]))
        self.good = np.zeros(self.n + 2, dtype=bool)
        for lo, hi in self.S.get("good_ranges") or [self.S["usable_bars"]]:
            self.good[lo:hi + 1] = True
        words, wl = load_words(stem)
        self.words = words
        self.wlines = wl
        self.vocal = np.array(self.a.get("vocal_bars", [0] * self.n))
        self.energy = self._energy()

    def bar_t(self, k):
        return self.f + 4 * k * self.bp

    def bar_of(self, t):
        return (t - self.f) / (4 * self.bp)

    def _energy(self):
        """How hard the song hits: tempo, how much of it is full on (drums near max), and
        how much of its length sits in loud sections."""
        full = np.mean([s["drums_db"] > -6 for s in self.sections for _ in range(s["bars"])])
        loud = np.mean([s["energy_db"] > -3 for s in self.sections for _ in range(s["bars"])])
        return {"bpm": self.bpm, "full": float(full), "loud": float(loud)}

    def section_at(self, k):
        for s in self.sections:
            if s["start"] <= k < s["end"]:
                return s
        return None

    # ---- lyric cleanliness on a bar line
    def line_across(self, k, before=0.1, after=0.15):
        """A sung line (or whisper segment) that is in progress across bar k: exiting or
        entering there cuts it mid-line. Small tolerances: a pickup or a held last syllable is ok."""
        t = self.bar_t(k)
        bar = 4 * self.bp
        for l in self.lines:
            if l["start"] < t - before * bar and l["end"] > t + after * bar:
                return l
        for l in self.wlines:
            if l["start"] < t - 0.3 and l["end"] - 0.4 > t and len(tokens(l["text"])) >= 3:
                # whisper segment boundaries are what the critic reads too
                inner = [w for w in self.words if l["start"] <= w["start"] < l["end"]]
                if any(w["start"] < t - 0.05 for w in inner) and any(w["start"] > t + 0.05 for w in inner):
                    return {"text": l["text"], "start": l["start"], "end": l["end"]}
        return None

    def exit_clean(self, k):
        """Leaving at bar k is clean if nothing new starts around the bar line (a pickup into
        the next line would be cut after one word) and the word before it ends a line."""
        t = self.bar_t(k)
        prev = [w for w in self.words if w["start"] < t - 1.2 * self.bp]
        for i, w in enumerate(self.words):
            if t - 1.2 * self.bp <= w["start"] < t + 0.5:
                nxt = self.words[i + 1]["start"] if i + 1 < len(self.words) else 1e9
                if not (w["end"] <= t + 0.1 and nxt > t + 0.6):
                    return False, w["w"]
        if prev:
            j = len(prev) - 1
            nxt = self.words[j + 1]["start"] if j + 1 < len(self.words) else 1e9
            if prev[-1]["end"] > t + 0.15 * 4 * self.bp:
                return False, prev[-1]["w"]  # a held word still sounding well past the bar
        return True, None

    def vocal_out(self, k, max_beats=4.0):
        """If a new line starts on (or just before) bar k, A's voice can still leave cleanly
        by cutting it at the end of the previous line: returns how many beats before the bar
        (mix.py opts.vocal_out_beats), or None."""
        t = self.bar_t(k)
        offenders = [i for i, w in enumerate(self.words) if t - 1.2 * self.bp <= w["start"] < t + 0.5]
        if not offenders:
            return 0.0
        i = offenders[0]
        if i == 0:
            return None
        prev = self.words[i - 1]
        if self.words[i]["start"] - prev["end"] < 0.2:
            return None  # the offending word continues a line already running: no gap to cut in
        beats = (t - prev["end"] - 0.06) / self.bp
        return round(beats, 2) if 0 < beats <= max_beats else None

    def next_word_after(self, k):
        t = self.bar_t(k)
        return next((w for w in self.words if w["start"] >= t - 0.05), None)

    def last_words_before(self, k, n=6):
        t = self.bar_t(k)
        ws = [w for w in self.words if w["end"] <= t + 0.1][-n:]
        return " ".join(w["w"] for w in ws)

    def first_words_from(self, k, n=7, pickup_beats=1.6):
        t = self.bar_t(k) - pickup_beats * self.bp
        ws = [w for w in self.words if w["start"] >= t][:n]
        return " ".join(w["w"] for w in ws)

    def line_starts_at(self, k):
        """A line begins at bar k (on the one or a pickup up to 1.6 beats before), within half a bar."""
        t = self.bar_t(k)
        return any(-1.6 * self.bp <= l["start"] - t <= 2 * self.bp for l in self.lines)

    def sung(self, k0, k1):
        k0, k1 = max(0, k0), min(len(self.vocal), k1)
        return float(np.mean(self.vocal[k0:k1] > 0.35)) if k1 > k0 else 0.0


# ---------------------------------------------------------------- candidate entries / exits

ENTRY_VALUE = {"chorus": 1.0, "drop": 0.85, "verse": 0.7, "pre-chorus": 0.65, "post-chorus": 0.5,
               "build": 0.45, "intro": 0.3, "bridge": 0.3, "breakdown": 0.15, "instrumental": 0.3}


def entries(song):
    """Bars where the song can land (become the song you hear), with a value and a note."""
    out = []
    seen_label = {}
    for s in song.sections:
        lab = s["label"]
        seen_label[lab] = seen_label.get(lab, 0) + 1
        if lab in ("talk", "outro"):
            continue
        k = s["start"]
        if not song.good[k] or k >= song.n - 16:
            continue
        v = ENTRY_VALUE.get(lab, 0.2)
        if lab == "verse" and seen_label[lab] == 1:
            v = 0.85  # verse 1: the song as everyone knows it starts
        if lab == "chorus" and seen_label[lab] > 2:
            v = 0.7
        across = song.line_across(k)
        if across:
            v -= 0.8
        sung_now = song.sung(k, k + 2) > 0.4
        if sung_now and not song.line_starts_at(k):
            v -= 0.3
        out.append({"bar": k, "value": round(v, 2), "section": s["name"], "label": lab,
                    "drums_db": s["drums_db"], "energy_db": s["energy_db"],
                    "mid_line": bool(across), "sung": sung_now})
    return out


def exits(song):
    """Bars A can be gone by: the end of a chorus (or the post-chorus / drop that follows it),
    on a phrase line, with no line sung across it."""
    out = []
    chorus_no = 0
    secs = song.sections
    for i, s in enumerate(secs):
        if s["label"] != "chorus":
            continue
        chorus_no += 1
        cands = [(s["end"], f"after {s['name']}")]
        if i + 1 < len(secs) and secs[i + 1]["label"] in ("post-chorus", "drop"):
            cands.append((secs[i + 1]["end"], f"after {s['name']} + its {secs[i + 1]['label']}"))
        # long choruses (16+ bars, repeated hook): also the inner phrase line after the first half
        if s["bars"] >= 16:
            cands.append((s["start"] + 8 * (s["bars"] // 16), f"after the first half of {s['name']}"))
        for k, note in cands:
            if k > song.n - 2 or not song.good[min(k, song.n)]:
                continue
            v = {1: 0.8, 2: 1.0}.get(chorus_no, 0.75)
            if "first half" in note:
                v -= 0.25
            across = song.line_across(k)
            clean, word = song.exit_clean(k)
            vo = None if clean else song.vocal_out(k)
            out.append({"bar": k, "value": round(v, 2), "note": note, "chorus_no": chorus_no,
                        "mid_line": bool(across), "clean": bool(clean and not across), "vo_beats": vo})
    return out


# ---------------------------------------------------------------- keys, tempo zones

def camelot_parse(c):
    return int(c[:-1]), c[-1]


def camelot_dist(c1, c2):
    n1, m1 = camelot_parse(c1)
    n2, m2 = camelot_parse(c2)
    d = min((n1 - n2) % 12, (n2 - n1) % 12)
    return d if m1 == m2 else d + 1  # relative major/minor (same number) = 1 step


def shift_camelot(c, semis):
    """Camelot code after pitch shifting by semitones (+1 semitone = +7 on the wheel)."""
    n, m = camelot_parse(c)
    return f"{(n - 1 + 7 * semis) % 12 + 1}{m}"


def zones(songs_in_order, zid=None):
    """Play tempo per song: contiguous runs of the same global tempo zone share one tempo
    (the run's median), so no song is stretched more than ~4 to 7 %."""
    zid = zid or zone_ids(songs_in_order)
    runs, cur = [], []
    for s in songs_in_order:
        if cur and zid[s.stem] != zid[cur[-1].stem]:
            runs.append(cur)
            cur = []
        cur.append(s)
    if cur:
        runs.append(cur)
    play = {}
    for z in runs:
        t = float(np.median([x.bpm for x in z]))
        for x in z:
            play[x.stem] = int(round(t))
    return play


def zone_ids(songs):
    """Global tempo zones over a song pool (sorted by tempo), for the order optimiser."""
    order = sorted(songs, key=lambda s: s.bpm)
    zid, z, lo = {}, 0, None
    for s in order:
        if lo is None:
            lo = s.bpm
        elif s.bpm / lo > ZONE_SPREAD:
            z += 1
            lo = s.bpm
        zid[s.stem] = z
    return zid


# ---------------------------------------------------------------- order optimiser

def song_energy(songs):
    """0..1 energy rank: 55 % tempo, 25 % full-on share, 20 % loud share (z scores)."""
    def z(x):
        x = np.array(x, dtype=float)
        return (x - x.mean()) / (x.std() + 1e-9)
    e = 0.55 * z([s.bpm for s in songs]) + 0.25 * z([s.energy["full"] for s in songs]) + \
        0.2 * z([s.energy["loud"] for s in songs])
    r = e.argsort().argsort() / max(1, len(songs) - 1)
    return {s.stem: float(v) for s, v in zip(songs, r)}


def arc_target(pos, n):
    """Warm up, climb to the peak at ~75 % of the set, land a little lower."""
    t = pos / max(1, n - 1)
    return 0.2 + 0.8 * t / 0.75 if t <= 0.75 else 1.0 - 0.4 * (t - 0.75)


def pair_cost(A, B, zid, pos, n):
    za, zb = zid[A.stem], zid[B.stem]
    dk = camelot_dist(A.camelot, B.camelot)
    if za == zb:
        key = {0: 0.0, 1: 0.1}.get(dk, 0.5 if dk == 2 else 1.0)
        tempo = 0.0
    else:
        key = 0.4 * ({0: 0.0, 1: 0.1}.get(dk, 0.5 if dk == 2 else 1.0))  # no harmonic overlap across zones
        step = zb - za
        tempo = 0.35 if step == 1 else (0.7 if step > 1 else (0.8 if pos >= n - 2 else 1.2))
    return key + tempo


def optimise_order(songs, k=None, required=(), first=None, w_arc=2.0):
    """Exact DP over subsets: the order (and, with k, the choice of songs) that minimises
    arc error + key and tempo costs. 16 songs: 65k subsets, fine."""
    n_all = len(songs)
    k = k or n_all
    idx = {s.stem: i for i, s in enumerate(songs)}
    zid = zone_ids(songs)
    en = song_energy(songs)
    req = 0
    for r in required:
        req |= 1 << idx[r]
    INF = 1e9
    best = {}
    for i, s in enumerate(songs):
        if first and s.stem != first:
            continue
        best[(1 << i, i)] = (w_arc * (en[s.stem] - arc_target(0, k)) ** 2, None)
    frontier = list(best.keys())
    for pos in range(1, k):
        nxt = {}
        for (mask, last) in frontier:
            c0 = best[(mask, last)][0]
            for j in range(n_all):
                if mask >> j & 1:
                    continue
                c = c0 + pair_cost(songs[last], songs[j], zid, pos, k) + \
                    w_arc * (en[songs[j].stem] - arc_target(pos, k)) ** 2
                key = (mask | 1 << j, j)
                if c < nxt.get(key, (INF,))[0]:
                    nxt[key] = (c, (mask, last))
        best.update(nxt)
        frontier = list(nxt.keys())
    finals = [(best[s][0], s) for s in frontier if (s[0] & req) == req]
    if not finals:
        raise ValueError("no order satisfies the constraints")
    cost, state = min(finals)
    path = []
    while state:
        path.append(state[1])
        state = best[state][1]
    return [songs[i] for i in reversed(path)], cost, en, zid


# ---------------------------------------------------------------- transition choice

def strong_last_word(A, exit_bar):
    """The word A ends on before exit_bar, if it is a good loop roll source: a hook or title
    word, held >= 0.3 s, ending within ~1.5 beats of the exit."""
    t = A.bar_t(exit_bar)
    ws = [w for w in A.words if w["end"] <= t + 0.1 and w["end"] >= t - 1.5 * A.bp]
    if not ws:
        return None, 0.0
    w = ws[-1]
    word = re.sub(r"[^a-z']", "", w["w"].lower())
    title = set(re.findall(r"[a-z']+", A.id.split(" - ", 1)[-1].lower()))
    hooky = any(word in tokens(l["text"]) for l in A.lines if l.get("hook"))
    held = w["end"] - w["start"]
    score = (1.0 if word in title else 0) + (0.6 if hooky else 0) + min(held, 0.8) - (0.5 if len(word) < 3 else 0)
    return w["w"], round(score, 2)


def choose_technique(A, B, play, ex, en_b, key_b):
    """Family by tempo zone + key, then bars. Returns (technique, bars, opts, reason)."""
    same_zone = play[A.stem] == play[B.stem]
    dk = camelot_dist(A.camelot_play, key_b)
    big = en_b["label"] in ("chorus", "drop", "verse") and en_b["drums_db"] > -12
    if same_zone and dk <= 1 and en_b["bar"] >= 8:
        bars = 8
        a_inst = A.sung(ex["bar"] - 16, ex["bar"]) < 0.2
        b_inst = B.sung(en_b["bar"] - 16, en_b["bar"]) < 0.2
        if a_inst and b_inst and en_b["bar"] >= 16:
            bars = 16
        return "eq_blend", bars, {}, f"same tempo zone ({play[A.stem]}), keys {A.camelot_play}->{key_b} " \
                                     f"{'match' if dk == 0 else 'are neighbours'}: {bars} bar EQ blend, lows swap halfway"
    if same_zone and dk == 2 and en_b["bar"] >= 4:
        return "out_by_one", 4, {}, f"keys {A.camelot_play}->{key_b} are 2 apart: B creeps in quietly for " \
                                    f"4 bars, A is out by the one"
    if same_zone and en_b["bar"] >= 4 and big:
        return "out_by_one", 4, {"b_silent": True}, f"keys {A.camelot_play}->{key_b} clash: no harmonic " \
                                                    f"overlap, A's EQ rolls off and B hits on the one"
    if not same_zone:
        why = f"tempo zone {play[A.stem]} -> {play[B.stem]} bpm: no beat overlap"
    else:
        why = f"keys {A.camelot_play}->{key_b} clash"
    return "slam", 2, {}, f"{why}: resonant filter climb on A, echo throw, B lands full"


def plan_pair_options(A, B, play, key_b):
    """All (exit, entry, technique) options for one pair, scored."""
    opts = []
    for ex in exits(A):
        for en in entries(B):
            tech, bars, o, why = choose_technique(A, B, play, ex, en, key_b)
            o = dict(o)
            sc = ex["value"] + en["value"]
            # never mid-line: a clean exit, or (eq_blend only) A's voice leaves at the previous line end
            if not ex["clean"]:
                if tech == "eq_blend" and ex["vo_beats"] is not None:
                    o["vocal_out_beats"] = ex["vo_beats"]
                    sc -= 0.15
                else:
                    sc -= 1.0
            # pros: dead air kills pop. Blends need A singing into the exit and B singing soon after
            if tech == "eq_blend":
                if A.sung(ex["bar"] - 2, ex["bar"]) < 0.5:
                    sc -= 0.3
                if B.sung(en["bar"] - bars, en["bar"]) > 0.6:
                    sc -= 0.25  # B's own words get muted under A: a waste of B's vocal
            else:
                if en["label"] not in ("chorus", "drop", "verse") or en["drums_db"] < -12:
                    sc -= 0.6  # a slam must land on something big, or the energy falls through the floor
                if en["energy_db"] < -4:
                    sc -= 0.3
            if not B.sung(en["bar"], en["bar"] + 2) > 0.3:
                sc -= 0.15
            opts.append({"exit": ex, "entry": en, "technique": tech, "bars": bars, "opts": o,
                         "why_tech": why, "score": round(sc, 2)})
    return opts


def play_seconds(song, play_bpm, k0, k1):
    return (k1 - k0) * 4 * 60.0 / play_bpm


def duration_cost(sec):
    if sec < PLAY_MIN:
        return 0.04 * (PLAY_MIN - sec) + 1.0
    if sec > PLAY_MAX:
        return 0.02 * (sec - PLAY_MAX) + 0.5
    return 0.15 * abs(sec - PLAY_AIM) / 40


def first_starts(song):
    """Where the opener starts: the start of its intro / first verse on the grid."""
    c = []
    for s in song.sections:
        if s["label"] in ("intro", "verse", "pre-chorus", "chorus") and song.good[s["start"]]:
            c.append(s["start"])
        if s["label"] in ("verse", "chorus"):
            break
    return c or [0]


def last_ends(song):
    return [e["bar"] for e in exits(song) if e["value"] > 0]


def plan_set(stems, title="auto", keep_order=False, k=None, required=(), first=None):
    songs = [Song(s) for s in stems]
    if keep_order:
        order, cost, erank, zid = songs, None, song_energy(songs), zone_ids(songs)
    else:
        order, cost, erank, zid = optimise_order(songs, k=k, required=required, first=first)
    play = zones(order, zid)
    # keys after an optional 1 semitone shift (94 % of real DJ transpositions are 1 semitone)
    for s in order:
        s.semis = 0
        s.camelot_play = s.camelot
    for A, B in zip(order[:-1], order[1:]):
        if play[A.stem] == play[B.stem] and camelot_dist(A.camelot_play, B.camelot) >= 2:
            for semis in (1, -1):
                if camelot_dist(A.camelot_play, shift_camelot(B.camelot, semis)) <= 1:
                    B.semis = semis
                    B.camelot_play = shift_camelot(B.camelot, semis)
                    break

    # Viterbi over (entry, exit) per song: pair scores + each song's play length
    n = len(order)
    pair_opts = [plan_pair_options(order[i], order[i + 1], play, order[i + 1].camelot_play)
                 for i in range(n - 1)]
    # state for song i = its landing bar (entry); song 0's landing = its start bar
    starts = first_starts(order[0])
    INF = 1e9
    # V[i][land] = (score, back) ; land of song i, choosing pair option for (i-1, i)
    V = [{s: (0.0, None) for s in starts}]
    for i in range(n - 1):
        A, B = order[i], order[i + 1]
        nxt = {}
        for land_a, (sc_a, _) in V[i].items():
            for o in pair_opts[i]:
                ex = o["exit"]["bar"]
                if ex - land_a < 16:
                    continue
                sec = play_seconds(A, play[A.stem], land_a, ex)
                # a song must play a chorus between landing and exit
                has_chorus = any(s["label"] == "chorus" and s["start"] >= land_a - 1 and s["end"] <= ex + 1
                                 for s in A.sections)
                s = sc_a + o["score"] - duration_cost(sec) - (0 if has_chorus else 1.5)
                lb = o["entry"]["bar"]
                if s > nxt.get(lb, (-INF,))[0]:
                    nxt[lb] = (s, (land_a, o))
        if not nxt:
            raise ValueError(f"no workable transition {A.stem} -> {B.stem}")
        V.append(nxt)
    # last song: end after a chorus
    last = order[-1]
    best_end = None
    for land, (sc, _) in V[-1].items():
        for e in last_ends(last):
            if e - land < 16:
                continue
            s = sc - duration_cost(play_seconds(last, play[last.stem], land, e))
            if best_end is None or s > best_end[0]:
                best_end = (s, land, e)
    if best_end is None:
        land = max(V[-1], key=lambda x: V[-1][x][0])
        best_end = (V[-1][land][0], land, min(last.n - 4, land + 48))
    total, land, end_bar = best_end
    chosen = []
    for i in range(n - 1, 0, -1):
        _, back = V[i][land]
        land_a, o = back
        chosen.append(o)
        land = land_a
    chosen.reverse()
    start_bar = land

    # one loop roll per set, only on a strong word, only where we slam anyway
    roll_i, roll_sc = None, 1.2
    for i, o in enumerate(chosen):
        if o["technique"] == "slam":
            w, sc = strong_last_word(order[i], o["exit"]["bar"])
            if w and sc > roll_sc:
                roll_i, roll_sc, roll_w = i, sc, w
    if roll_i is not None:
        chosen[roll_i]["technique"] = "loop_roll"
        chosen[roll_i]["why_tech"] = f"tempo jump on a strong word: '{roll_w}' stutters (1, 1/2, 1/4 beat " \
                                     f"loops) and B slams in"

    # assemble the plan
    tracks = []
    for i, s in enumerate(order):
        t = {"id": s.id, "analysis": s.analysis_path, "play_bpm": play[s.stem]}
        if s.semis:
            t["pitch_semitones"] = s.semis
        if i == 0:
            t["start_bar"] = int(start_bar)
        if i == n - 1:
            t["end_bar"] = int(min(last.n - 1, end_bar + 4))
        tracks.append(t)
    transitions = []
    lands = [start_bar] + [o["entry"]["bar"] for o in chosen]
    for i, o in enumerate(chosen):
        A, B = order[i], order[i + 1]
        ex, en = o["exit"], o["entry"]
        tech, bars = o["technique"], o["bars"]
        drop = tech in ("slam", "loop_roll", "strip_drop")
        b_entry = en["bar"] if drop or tech == "cut" else en["bar"] - bars
        sec = play_seconds(A, play[A.stem], lands[i], ex["bar"])
        a_secs = [s["name"] for s in A.sections if s["start"] >= lands[i] - 1 and s["end"] <= ex["bar"] + 1
                  and s["label"] in ("verse", "pre-chorus", "chorus", "drop", "bridge")]
        why = (f"{A.id.split(' - ')[-1]} plays {', '.join(a_secs) or 'its run'} ({sec:.0f} s) and leaves {ex['note']} "
               f"(bar {ex['bar']}, line end: '...{A.last_words_before(ex['bar'])}'); "
               f"{o['why_tech']}; {B.id.split(' - ')[-1]} lands on {en['section']} (bar {en['bar']}): "
               f"'{B.first_words_from(en['bar'])}...'")
        if B.semis:
            why += f" [B pitched {B.semis:+d} semitone to {B.camelot_play}]"
        tr = {"from": A.id, "to": B.id, "technique": tech, "a_exit_bar": int(ex["bar"]),
              "b_entry_bar": int(b_entry), "bars": int(bars), "why": why}
        if o["opts"]:
            tr["opts"] = o["opts"]
        transitions.append(tr)
    plan = {"title": title, "made_by": "autodj.skills.planner (structure skill)",
            "order_cost": None if cost is None else round(cost, 2),
            "energy_rank": {s.id: round(erank[s.stem], 2) for s in order},
            "tracks": tracks, "transitions": transitions}
    return plan


def describe(plan):
    print(plan["title"])
    for t in plan["tracks"]:
        print(f"  {t['id']:<48} play {t['play_bpm']}{'  pitch %+d' % t['pitch_semitones'] if t.get('pitch_semitones') else ''}"
              f"  energy {plan['energy_rank'].get(t['id'])}")
    for tr in plan["transitions"]:
        print(f"  {tr['technique']:<11} {tr['bars']:>2} bars | {tr['from'][:30]} @ {tr['a_exit_bar']} -> "
              f"{tr['to'][:30]} @ {tr['b_entry_bar']}\n      {tr['why']}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    title = None
    if "--title" in args:
        i = args.index("--title")
        title = args[i + 1]
        del args[i:i + 2]
    keep = "--keep-order" in args
    args = [a for a in args if a != "--keep-order"]
    cmd, out = args[0], Path(args[1])
    if cmd == "set05":
        plan = plan_set(SET05, title=title or "Structure skill: set05 songs, auto planned", keep_order=keep,
                        first=None)
    elif cmd == "pick":
        k = int(args[2])
        must = args[3:]
        pool = sorted(PRETTY)
        plan = plan_set(pool, title=title or f"Structure skill: {k} songs incl. {', '.join(must)}",
                        k=k, required=must)
    else:
        plan = plan_set(args[2:], title=title or out.stem, keep_order=keep)
    out.write_text(json.dumps(plan, indent=1))
    describe(plan)
    print(f"wrote {out}")
