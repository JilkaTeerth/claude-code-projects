"""Blends skill: EQ blends that keep the energy flat, and tempo arcs.

Import this module before autodj.mix.layout/build runs; it registers:

  technique "adaptive_blend"   the eq_blend recipe, but A only gives way as fast as B can fill.
                               Per bar band energy (mid, hi, vocal, low) is measured from the
                               stems; A's mid and hi EQ curves are solved so the sum follows a
                               smooth line from A's level to B's level. The bass swap lands on
                               the first 2 bar line where B's low end is really there.
  technique "long_blend"       adaptive_blend with house defaults (16+ bars, slow top down
                               entry, swap at the middle phrase line). For instrumental sides.
  technique "tempo_blend"      alias of adaptive_blend, for overlaps that sit between two tempo
                               arcs (documentation clarity only).

  track option "tempo_map"     [[bar, bpm], ...] in the song's own bar numbers. The song is
                               stretched with a time varying ratio (Rubber Band R2, per sample
                               stretch factor), bpm is linear in bars between points and flat
                               outside. Lets 120 -> 128 or 110 -> 128 happen as a ride, not a
                               stop. Overlaps must sit in flat parts of the maps (both songs at
                               the same constant tempo while they play together).

The track option works by replacing autodj.mix.Track with a subclass that behaves exactly like
the original when "tempo_map" is absent, and autodj.mix.load_words with a version that maps
lyric times through the tempo map. The lead can fold both into mix.py later.
"""
import json

import numpy as np
import pedalboard as pb
from scipy.signal import butter, sosfilt

from autodj import mix
from autodj.mix import ROOT, SR, STEMS, cut, ramp, vocal_echo

_BaseTrack = mix.Track if not getattr(mix.Track, "_blends_arc", False) else mix.Track.__mro__[1]

# rough K weighting per band (LUFS weights highs ~+4 dB, rolls off the deep low end)
W = {"low": 0.7, "mid": 1.0, "hi": 2.5}
HI_SOS = butter(4, 2500, "high", fs=SR, output="sos")


# ====================================================================================
# tempo arcs
# ====================================================================================

def bpm_at(tmap, k):
    """Play bpm at (fractional) original bar k for a tempo map [[bar, bpm], ...]."""
    bars = [p[0] for p in tmap]
    bpms = [p[1] for p in tmap]
    return np.interp(k, bars, bpms)


class ArcTrack(_BaseTrack):
    """Track with an optional time varying tempo ("tempo_map" in the plan's track spec)."""
    _blends_arc = True

    def __init__(self, spec, bar_from, bar_to):
        tmap = spec.get("tempo_map")
        if not tmap:
            super().__init__(spec, bar_from, bar_to)
            return
        tmap = sorted([list(p) for p in tmap])
        a = json.loads((ROOT / spec["analysis"]).read_text())
        flat = dict(spec)
        flat["play_bpm"] = a["bpm"]  # load at native speed (pitch shift, if any, still applied)
        super().__init__(flat, bar_from, bar_to)
        self.tempo_map = tmap
        native = a["bpm"]
        orig_bar = 4 * a["beat_period"]
        first = a["first_downbeat"]
        n_in = self.n
        x_orig = self.c0 + np.arange(n_in) / SR
        r = bpm_at(tmap, (x_orig - first) / orig_bar) / native  # >1 = faster
        for s in STEMS:
            self.stems[s] = np.ascontiguousarray(
                pb.time_stretch(self.stems[s].T, SR, stretch_factor=r.astype(np.float64),
                                high_quality=False).T, dtype=np.float32)
        self._kick = np.ascontiguousarray(
            pb.time_stretch(self._kick.T, SR, stretch_factor=r.astype(np.float64), high_quality=False).T,
            dtype=np.float32)
        # local seconds of every input sample: integral of 1/ratio (measured on a click track:
        # within 2 ms of where Rubber Band R2 actually puts the beat over a 6.7% ramp)
        self._tl = np.concatenate([[0.0], np.cumsum(1.0 / r)]) / SR
        self._xo = self.c0 + np.arange(n_in + 1) / SR
        self.n = min(min(len(v) for v in self.stems.values()), len(self._kick))
        for s in STEMS:
            self.stems[s] = self.stems[s][: self.n]
        self._kick = self._kick[: self.n]
        self.refresh()
        self._native_bar = orig_bar
        self._first = first
        end_bpm = tmap[-1][1]
        self.play_bpm = end_bpm
        self.ratio = end_bpm / native  # only used by code that assumes one ratio (approximate)
        self.bar_len = orig_bar * native / end_bpm  # the exit tempo: what an outgoing blend uses
        k_end = tmap[-1][0]
        self.first_db = self.bar(k_end) - k_end * self.bar_len  # exact from the last map point on
        self.g = {s: np.zeros(self.n, dtype=np.float32) for s in STEMS}
        self.eq = {b: np.ones(self.n, dtype=np.float32) for b in ("mid", "hi")}
        if hasattr(self, "_kick_env"):
            del self._kick_env

    # --- time maps ---
    def local_of(self, t_orig):
        if not hasattr(self, "_tl"):
            return (np.asarray(t_orig) - self.c0) / self.ratio
        return np.interp(t_orig, self._xo, self._tl)

    def orig(self, t_local):
        if not hasattr(self, "_tl"):
            return super().orig(t_local)
        return float(np.interp(t_local, self._tl, self._xo))

    def bar(self, k):
        if not hasattr(self, "_tl"):
            return super().bar(k)
        return float(self.local_of(self._first + k * self._native_bar))

    def bar_len_at(self, k):
        return self.bar(k + 1) - self.bar(k)

    def locked_bar(self, k, span=8):
        if not hasattr(self, "_tl"):
            return super().locked_bar(k, span)
        # same kick re-lock as the base class, but beats follow the tempo map
        import librosa
        if not hasattr(self, "_kick_env"):
            self._kick_env = librosa.onset.onset_strength(y=self._kick.mean(axis=1), sr=SR, hop_length=64)
        env, t0 = self._kick_env, self.bar(k)
        beats = np.array([self.bar(k + i / 4) for i in range(span * 4)]) - t0
        seg = env[max(0, int(t0 * SR / 64)):int((t0 + beats[-1] + self.bar_len) * SR / 64)]
        if len(seg) < 10 or seg.std() < 1e-6:
            return t0
        seg = (seg - seg.mean()) / seg.std()
        best, best_shift = -9.0, 0.0
        for shift in np.arange(-0.08, 0.0801, 0.002):
            fr = np.round((beats + shift) * SR / 64).astype(int)
            fr = fr[(fr >= 0) & (fr < len(seg))]
            sc = seg[fr].mean()
            if sc > best:
                best, best_shift = sc, shift
        self.locks = getattr(self, "locks", []) + [(k, round(best_shift * 1000), round(best, 2))]
        return t0 + best_shift if best > 1.2 else t0


_orig_load_words = mix.load_words.__wrapped__ if hasattr(mix.load_words, "__wrapped__") else mix.load_words


def load_words(t):
    """mix.load_words, but lyric times go through the tempo map when a track has one."""
    if not hasattr(t, "_tl"):
        return _orig_load_words(t)
    p = ROOT / "lyrics" / f"{t.name}.json"
    if not p.exists():
        return []
    from autodj.lyrics import clean_words
    ws = clean_words(json.loads(p.read_text())["words"])
    return [{"s": float(t.local_of(w["start"])), "e": float(t.local_of(w["end"]))} for w in ws]


load_words.__wrapped__ = _orig_load_words


# ====================================================================================
# band energy measurement
# ====================================================================================

def _frames(t, l0, l1, hop):
    """Per frame mean square energy of each band of each stem group, local window [l0, l1)."""
    i0, i1 = t.idx(max(0.0, l0)), t.idx(l1)
    h = max(1, int(hop * SR))
    nf = max(1, (i1 - i0) // h)

    def ms(x):
        x = x[: nf * h]
        if len(x) < nf * h:
            x = np.pad(x, ((0, nf * h - len(x)), (0, 0)))
        return (x.astype(np.float64) ** 2).mean(axis=1).reshape(nf, h).mean(axis=1)

    inst = t.stems["drums"][i0:i1] + t.stems["other"][i0:i1]
    voc = t.stems["vocals"][i0:i1]
    ihi = sosfilt(HI_SOS, inst, axis=0)
    vhi = sosfilt(HI_SOS, voc, axis=0)
    e = {"imid": ms(inst - ihi), "ihi": ms(ihi), "vmid": ms(voc - vhi), "vhi": ms(vhi),
         "low": ms(t.stems["bass"][i0:i1])}
    return e, i0, h, nf


def _smooth(x, n):
    if n <= 1:
        return x
    k = np.ones(n) / n
    pad = np.pad(x, (n // 2, n - 1 - n // 2), mode="edge")
    return np.convolve(pad, k, mode="valid")


def _vidx(t, timeline_s):
    return np.clip(np.round((np.asarray(timeline_s) - t.offset) * SR).astype(int), 0, t.n - 1)


def db10(x):
    return 10 * np.log10(np.maximum(x, 1e-12))


# ====================================================================================
# the adaptive blend
# ====================================================================================

def choose_swap(A, B, ts, te, o, eA, eB, fr_t):
    """Swap the low end on the first 2 bar line (from the middle on) where B's low end is
    within `swap_db` of A's, i.e. B is "kicking in" (Club Ready: swapping into an intro with
    nothing happening is an anticlimax). Falls back to the end of the overlap."""
    L = te - ts
    if "swap_at" in o:
        return ts + L * o["swap_at"]
    bar = A.bar_len
    bars = int(round(L / bar))
    tol = o.get("swap_db", 6.0)
    start = max(2, bars // 2) if bars >= 4 else bars // 2
    cands = list(range(start, bars, 2 if bars >= 4 else 1))
    for k in cands:
        t0, t1 = ts + k * bar, ts + min(bars, k + 2) * bar
        m = (fr_t >= t0) & (fr_t < t1)
        mA = (fr_t >= ts) & (fr_t < ts + k * bar)
        if not m.any() or not mA.any():
            continue
        if db10(eB["low"][m].mean()) >= db10(eA["low"][mA].mean()) - tol:
            return t0
    return te


def t_adaptive_blend(A, B, ts, te, bars, o):
    """Energy matched EQ blend. B comes in top down on a fixed recipe (fader up over the
    first quarter, mids -12 dB opening to 0, hats at 0, low end at the swap, vocal on the
    phrase line). A's mid and hi knobs are SOLVED, bar by bar, so that each band of the sum
    follows a straight dB line from A's level to B's level: A only gives up a band as fast as
    B fills it. A quiet intro therefore keeps A almost full until the last beat (Spotify's
    "one song is always at full level"), a full chorus makes A step aside quickly.

    opts: swap_at (fraction, else chosen from the low end), swap_db (6), b_in (0.25 of the
    overlap), b_mid_db (-12), a_out_beats (2: A's last fade), max_lift_db (3: how far B's
    music may be pushed while A leaves), vocal_out_beats, vocal_echo (True)."""
    L = te - ts
    a, b = A.local, B.local
    beat = A.bar_len / 4
    hop = beat / 2
    pad = 2 * A.bar_len
    q = lambda f: ts + L * f

    # ---- measure both songs over the window (timeline frames) ----
    eA, ia0, h, nfA = _frames(A, a(ts - pad), a(te + pad), hop)
    eB, ib0, _, nfB = _frames(B, b(ts - pad), b(te + pad), hop)
    nf = min(nfA, nfB)
    for e in (eA, eB):
        for k in e:
            e[k] = e[k][:nf]
    fr_t = ts - pad + (np.arange(nf) + 0.5) * hop  # timeline seconds of frame centres
    # (frames start where the window was clipped at 0; correct for clipping)
    fr_tA = A.offset + (ia0 + (np.arange(nf) + 0.5) * h) / SR
    fr_tB = B.offset + (ib0 + (np.arange(nf) + 0.5) * h) / SR
    # resample B's frames onto A's frame times (they differ only if a window was clipped)
    if abs(fr_tA[0] - fr_tB[0]) > 1e-3:
        for k in eB:
            eB[k] = np.interp(fr_tA, fr_tB, eB[k])
    fr_t = fr_tA

    swap = choose_swap(A, B, ts, te, o, eA, eB, fr_t)

    # ---- B's recipe (fixed) ----
    b_in = o.get("b_in", 0.25)
    b_mid0 = o.get("b_mid_db", -12.0)
    ramp(B, ["drums", "other"], b(ts), b(q(b_in)), 0, 1, law="power")
    if o.get("b_music_late"):
        # keys that rub: B's melody waits for the swap (drums have no key), the solver then
        # keeps A's music up longer because B can't fill the mids without it
        B.g["other"][B.idx(b(ts)):B.idx(b(te - 2 * beat))] = 0
        ramp(B, ["other"], b(te - 2 * beat), b(te), 0, 1, law="power")
    i_ts, i_sw, i_m, i_te = B.idx(b(ts)), B.idx(b(swap)), B.idx(b(q(0.75))), B.idx(b(te))
    mid_db = np.full(B.n, 0.0)
    mid_db[i_ts:i_m] = np.linspace(b_mid0, 0.0, max(0, i_m - i_ts))
    B.eq["mid"][i_ts:i_te] = 10 ** (mid_db[i_ts:i_te] / 20)
    B.eq["mid"][i_te:B.idx(B.keep[1])] = 1.0
    B.g["bass"][i_ts:i_sw] = 0
    ramp(B, ["bass"], b(swap), b(swap) + 0.025, 0, 1)
    B.g["vocals"][i_ts:i_te] = 0
    ramp(B, ["vocals"], b(te), b(te) + mix.SNAP, 0, 1)

    # ---- A's vocal and low end (fixed) ----
    v_out = te - beat * o.get("vocal_out_beats", 0)
    if o.get("vocal_echo", True):
        vocal_echo(A, a(v_out))
    cut(A, ["vocals"], a(v_out), 0)
    if swap < te:
        cut(A, ["bass"], a(swap), 0)

    # ---- gains as seen by each frame ----
    fiA = _vidx(A, fr_t)
    fiB = _vidx(B, fr_t)
    gBi = (B.g["drums"][fiB] ** 2 + B.g["other"][fiB] ** 2) / 2  # B's music fader(s)
    gBm = B.eq["mid"][np.clip(fiB, 0, B.n - 1)] ** 2
    gBv = B.g["vocals"][np.clip(fiB, 0, B.n - 1)] ** 2
    gBl = B.g["bass"][np.clip(fiB, 0, B.n - 1)] ** 2
    gAv = A.g["vocals"][np.clip(fiA, 0, A.n - 1)] ** 2
    gAl = A.g["bass"][np.clip(fiA, 0, A.n - 1)] ** 2
    for arr in (gBi, gBm, gBv, gBl):
        arr[fr_t < ts] = 0  # B is not playing yet
    sm = max(1, int(round(A.bar_len / hop)))  # one bar smoothing: no beat by beat pumping
    S = {k: _smooth(v, sm) for k, v in eA.items()}
    T = {k: _smooth(v, sm) for k, v in eB.items()}

    # B's level after the overlap (its body, vocal on): where the line should arrive
    post = (fr_t >= te + B.bar_len * 0.5) & (fr_t < te + pad)
    pre = (fr_t >= ts - pad) & (fr_t < ts)

    x = np.clip((fr_t - ts) / L, 0, 1)
    gA = {}
    contrib_B, contrib_Afix = {}, {}
    for band, ik, vk in (("mid", "imid", "vmid"), ("hi", "ihi", "vhi")):
        A_full = S[ik] + S[vk]
        B_post = (T[ik][post] + T[vk][post]).mean() if post.any() else (T[ik] + T[vk])[-sm:].mean()
        tgt_db = (1 - x) * db10(A_full) + x * db10(np.full_like(A_full, B_post))
        tgt = 10 ** (tgt_db / 10)
        # never ask for more than A alone could give at that moment (A can't go above unity)
        tgt = np.minimum(tgt, np.maximum(A_full, B_post))
        bm = gBm if band == "mid" else 1.0
        Bc = gBi * bm * T[ik] + gBv * T[vk]
        Afix = gAv * S[vk]
        g2 = (tgt - Bc - Afix) / np.maximum(S[ik], 1e-12)
        g = np.sqrt(np.clip(g2, 0, 1))
        g[fr_t < ts] = 1.0
        g = np.maximum.accumulate(g[::-1])[::-1]  # never comes back up: keep the larger value
        gA[band] = g
        contrib_B[band], contrib_Afix[band] = Bc, Afix

    # ---- write A's EQ curves, then A's last fade (equal power) ----
    i0, i1 = A.idx(a(ts)), A.idx(a(te))
    tt = A.offset + np.arange(i0, i1) / SR
    for band in ("mid", "hi"):
        A.eq[band][i0:i1] = np.interp(tt, fr_t, gA[band]).astype(np.float32)
        A.eq[band][i1:A.idx(A.keep[1])] = 0.0
    fade = beat * o.get("a_out_beats", 2)
    ramp(A, ["drums", "other"], a(te - fade), a(te), 1, 0, law="power")
    if swap >= te:
        ramp(A, ["bass"], a(te - beat), a(te), 1, 0, law="power")
        ramp(B, ["bass"], b(te - beat), b(te), 0, 1, law="power")
        B.g["bass"][B.idx(b(te)):B.idx(B.keep[1])] = 1.0

    # ---- B lift: if the line still sags while A leaves, push B's music up to max_lift_db,
    # then hand back to unity over the bar after the phrase line (B's vocal arrives there) ----
    lift_db = o.get("max_lift_db", 3.0)
    if lift_db > 0:
        mA = A.eq["mid"][np.clip(fiA, 0, A.n - 1)] ** 2
        hA = A.eq["hi"][np.clip(fiA, 0, A.n - 1)] ** 2
        fA = A.g["drums"][np.clip(fiA, 0, A.n - 1)] ** 2
        tot = (W["mid"] * (contrib_B["mid"] + contrib_Afix["mid"] + fA * mA * S["imid"])
               + W["hi"] * (contrib_B["hi"] + contrib_Afix["hi"] + fA * hA * S["ihi"])
               + W["low"] * (gAl * S["low"] + gBl * T["low"]))
        A_tot = W["mid"] * (S["imid"] + S["vmid"]) + W["hi"] * (S["ihi"] + S["vhi"]) + W["low"] * S["low"]
        B_tot = W["mid"] * (T["imid"] + T["vmid"]) + W["hi"] * (T["ihi"] + T["vhi"]) + W["low"] * T["low"]
        floor = min(A_tot[pre].mean() if pre.any() else A_tot.mean(),
                    B_tot[post].mean() if post.any() else B_tot.mean())
        win = (fr_t >= te - 2 * A.bar_len) & (fr_t < te)
        short = floor / np.maximum(tot, 1e-12)
        need = db10(short[win].max()) if win.any() else 0.0
        # only push if we'd sag more than ~1 dB below the floor
        if need > 1.0:
            lift = min(lift_db, need)
            gl = 10 ** (lift / 20)
            l0 = max(te - 2 * A.bar_len, q(b_in) + beat)
            ramp(B, ["drums", "other"], b(l0), b(te - beat), 1, gl)
            ramp(B, ["drums", "other"], b(te), b(te + B.bar_len), gl, 1)
            A.blend_info = {"lift_db": round(float(lift), 1)}
    info = getattr(A, "blend_info", {})
    info.update({"swap_bar": round(float((swap - ts) / A.bar_len), 2),
                 "a_mid_end_db": round(float(db10(gA["mid"][fr_t < te - fade][-1] ** 2)), 1)
                 if (fr_t < te - fade).any() else None,
                 "a_hi_end_db": round(float(db10(gA["hi"][fr_t < te - fade][-1] ** 2)), 1)
                 if (fr_t < te - fade).any() else None})
    A.blend_info = info
    print(f"  adaptive_blend {A.id[:24]} -> {B.id[:24]}: {info}", flush=True)


def t_long_blend(A, B, ts, te, bars, o):
    """House style long blend (16 to 32 bars, both sides instrumental or A's vocal done):
    slower entry (B's fader over the first 3/8), mids start lower, swap on the middle phrase
    line unless B's low end isn't there yet."""
    o = dict(o)
    o.setdefault("b_in", 0.375)
    o.setdefault("b_mid_db", -15.0)
    o.setdefault("a_out_beats", 4)
    t_adaptive_blend(A, B, ts, te, bars, o)


# ====================================================================================
# planning helpers
# ====================================================================================

def tempo_plan(bpm_a, bpm_b, a_exit_bar, bars, b_entry_bar, ramp_bars=16):
    """Suggest tempo maps for a blend between a song at bpm_a and one at bpm_b (R7 extended).
    Returns (a_tempo_map, b_tempo_map, blend_bpm). Gaps under 2.5%: B is played at A's tempo
    and no ramp (or returns to native over ramp_bars after). 2.5 to 9%: A rides up (or down)
    to B's tempo over ramp_bars before the overlap. 9 to 18%: split the gap: A rides half way,
    the overlap sits at the middle tempo, B rides the rest after the overlap."""
    gap = abs(bpm_b / bpm_a - 1)
    ov0 = a_exit_bar - bars
    if gap < 0.025:
        return None, [[b_entry_bar + bars, bpm_a], [b_entry_bar + bars + ramp_bars, bpm_b]], bpm_a
    if gap < 0.09:
        return [[ov0 - ramp_bars, bpm_a], [ov0, bpm_b]], None, bpm_b
    mid = round((bpm_a * bpm_b) ** 0.5, 2)
    return ([[ov0 - ramp_bars, bpm_a], [ov0, mid]],
            [[b_entry_bar + bars, mid], [b_entry_bar + bars + ramp_bars, bpm_b]], mid)


# ---- register ----
mix.Track = ArcTrack
mix.load_words = load_words
mix.TECHNIQUES.update({"adaptive_blend": t_adaptive_blend, "long_blend": t_long_blend,
                       "tempo_blend": t_adaptive_blend})
