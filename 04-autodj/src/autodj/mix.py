"""Hands: render a mixplan.json into one continuous mix, stem by stem.

Every song is split into vocals / drums / bass / other (autodj.stems). Each stem has
its own fader, like the stem buttons on a DJ controller. Songs are time stretched
to their play_bpm, laid on a shared timeline downbeat to downbeat, and each
transition choreographs the stems on phrase lines. Hard rule: two lead vocals
never play at once.

usage: python -m autodj.mix plans/set02.json
"""
import json
import subprocess
import sys
from pathlib import Path

import librosa
import numpy as np
import pedalboard as pb
import pyloudnorm as pyln
import soundfile as sf
from scipy.signal import butter, sosfilt, sosfiltfilt

from .analyze import SR

ROOT = Path(__file__).resolve().parent.parent
STEMS = ["vocals", "drums", "bass", "other"]
INST = ["drums", "bass", "other"]
LOW_HZ = 150  # below this everything rides the bass fader
SNAP = 0.03  # seconds for a "hard" cut, short enough to sound instant, long enough not to click


class Track:
    def __init__(self, spec, bar_from, bar_to):
        self.id = spec["id"]
        self.a = json.loads((ROOT / spec["analysis"]).read_text())
        self.name = Path(self.a["file"]).stem
        self.play_bpm = spec.get("play_bpm", self.a["bpm"])
        self.ratio = self.play_bpm / self.a["bpm"]
        orig_bar = 4 * self.a["beat_period"]
        first = self.a["first_downbeat"]

        # only load the part of the song we use (+ margin for loops and echo tails)
        c0 = max(0.0, first + (bar_from - 8) * orig_bar)
        c1 = min(self.a["duration"], first + (bar_to + 12) * orig_bar)
        f0, f1 = int(c0 * SR), int(c1 * SR)
        self.c0 = c0  # original song seconds at local sample 0
        stem_dir = ROOT / "stems" / self.name
        self.has_stems = (stem_dir / "vocals.flac").exists()
        raw = {}
        if self.has_stems:
            for s in STEMS:
                raw[s], _ = sf.read(stem_dir / f"{s}.flac", start=f0, stop=f1, dtype="float32", always_2d=True)
        else:
            from .analyze import load
            full = load(self.a["file"]).astype(np.float32)[f0:f1]
            raw = {s: np.zeros_like(full) for s in STEMS}
            raw["other"] = full
        semis = spec.get("pitch_semitones", 0)
        self.stems = {}
        for s in STEMS:
            x = raw[s]
            if abs(self.ratio - 1) > 1e-4 or semis:
                # R3 (high_quality=True) drifts ~30 ms per minute; R2 holds the beat grid
                x = pb.time_stretch(x.T, SR, stretch_factor=self.ratio,
                                    pitch_shift_in_semitones=semis, high_quality=False).T
            self.stems[s] = np.ascontiguousarray(x, dtype=np.float32)
        self.n = min(len(v) for v in self.stems.values())
        for s in STEMS:
            self.stems[s] = self.stems[s][: self.n]
        # the "bass" fader carries the whole low end (bass stem + kick + sub from the
        # drum and synth stems), like a controller's low EQ. Otherwise an incoming
        # song's kick and sub sneak in under the outgoing bass and boom.
        lp = butter(4, LOW_HZ, "low", fs=SR, output="sos")
        self._kick = sosfiltfilt(lp, self.stems["drums"], axis=0).astype(np.float32)
        low_other = sosfiltfilt(lp, self.stems["other"], axis=0).astype(np.float32)
        self.stems["drums"] -= self._kick
        self.stems["other"] -= low_other
        self.stems["bass"] += self._kick + low_other
        self.refresh()

        self.bar_len = orig_bar / self.ratio
        self.first_db = (first - c0) / self.ratio
        self.offset = 0.0
        self.g = {s: np.zeros(self.n, dtype=np.float32) for s in STEMS}
        # controller EQ on the instruments: mid (150 Hz to 2.5 kHz) and hi (> 2.5 kHz) knobs,
        # linear gain. Low is the "bass" fader. Vocals stay out of the EQ (the vocal fader rules).
        self.eq = {b: np.ones(self.n, dtype=np.float32) for b in ("mid", "hi")}
        self.sweeps, self.echoes, self.fx = [], [], []  # fx: (local place, audio)
        self.keep = (0.0, 0.0)
        self.vocal_bars = self.a.get("vocal_bars")

    def refresh(self):
        self.audio = sum(self.stems[s] for s in STEMS)

    def scale(self, gain):
        self._kick *= gain
        for s in STEMS:
            self.stems[s] *= gain
        self.refresh()

    def bar(self, k):
        return self.first_db + k * self.bar_len

    def local(self, t):
        return t - self.offset

    def orig(self, t_local):
        """Original song seconds for a local (stretched) time."""
        return self.c0 + t_local * self.ratio

    def idx(self, t_local):
        return int(np.clip(round(t_local * SR), 0, self.n))

    def vocal_level(self, k):
        if not self.vocal_bars or k < 0 or k >= len(self.vocal_bars):
            return 0.0
        return self.vocal_bars[k]

    def locked_bar(self, k, span=8):
        """Bar k's downbeat re-locked onto this song's own kick drum (from the drum stem).
        One grid per song drifts 40 to 70 ms on real tracks; this pulls it back."""
        if not hasattr(self, "_kick_env"):
            low = self._kick.mean(axis=1) if self.has_stems else \
                sosfiltfilt(butter(4, 150, "low", fs=SR, output="sos"), self.audio.mean(axis=1))
            self._kick_env = librosa.onset.onset_strength(y=low, sr=SR, hop_length=64)
        env, beat, t0 = self._kick_env, self.bar_len / 4, self.bar(k)
        seg = env[max(0, int(t0 * SR / 64)):int((t0 + span * self.bar_len) * SR / 64)]
        if len(seg) < 10 or seg.std() < 1e-6:
            return t0
        seg = (seg - seg.mean()) / seg.std()
        best, best_shift = -9.0, 0.0
        for shift in np.arange(-0.08, 0.0801, 0.002):  # wider catches 16th note hats
            fr = np.round((np.arange(span * 4) * beat + shift) * SR / 64).astype(int)
            fr = fr[(fr >= 0) & (fr < len(seg))]
            sc = seg[fr].mean()
            if sc > best:
                best, best_shift = sc, shift
        self.locks = getattr(self, "locks", []) + [(k, round(best_shift * 1000), round(best, 2))]
        return t0 + best_shift if best > 1.2 else t0


# ---------- automation helpers (times are local to the track) ----------

def ramp(t, stems, t0, t1, v0, v1, law="cos"):
    """Ramp from v0 to v1 between t0 and t1, then hold v1 to the end of the window.
    law="power": equal power (sin/cos) so a crossfade between two songs has no 3 dB hole."""
    i0, i1, end = t.idx(t0), t.idx(t1), t.idx(t.keep[1])
    for s in stems:
        if i1 > i0:
            x = np.linspace(0, 1, i1 - i0)
            if law == "power":
                c = np.sin(np.pi / 2 * x) if v1 > v0 else 1 - np.cos(np.pi / 2 * x)
            else:
                c = 0.5 - 0.5 * np.cos(np.pi * x)
            t.g[s][i0:i1] = v0 + (v1 - v0) * c
        t.g[s][i1:end] = v1


def db(x):
    return 0.0 if x <= -60 else 10 ** (x / 20)


def eq(t, band, t0, t1, db0, db1):
    """Turn an EQ knob ("mid" or "hi") from db0 to db1 between t0 and t1 (linear in dB),
    then hold to the end of the window. -inf = kill."""
    i0, i1, end = t.idx(t0), t.idx(t1), t.idx(t.keep[1])
    lo0, lo1 = max(db0, -60), max(db1, -60)
    if i1 > i0:
        curve = np.linspace(lo0, lo1, i1 - i0)
        t.eq[band][i0:i1] = np.where(curve <= -60, 0, 10 ** (curve / 20))
    t.eq[band][i1:end] = db(db1)


def hold(t, stems, t0, t1, v):
    for s in stems:
        t.g[s][t.idx(t0):t.idx(t1)] = v


def cut(t, stems, at, to):
    """Near instant move to `to` at local time `at`."""
    frm = 1.0 - to
    ramp(t, stems, at - SNAP if to == 0 else at, at if to == 0 else at + SNAP, frm, to)


def vocal_echo(t, at, beats=1.0):
    """Throw the last word of the vocal into a tempo synced delay tail."""
    beat = t.bar_len / 4
    t.echoes.append({"src": ["vocals"], "s0": at - beat * beats, "s1": at, "place": at,
                     "tail": 4 * t.bar_len, "beat": beat, "hp": 200})


def loop_region(t, src_bar, loop_bars, from_t, to_t, stems=INST):
    """Replace stems from `from_t` to `to_t` with a seamless repeat of bars
    [src_bar, src_bar + loop_bars), like hitting loop on a controller."""
    a, b = t.idx(t.locked_bar(src_bar, span=max(2, loop_bars))), None
    b = a + int(round(loop_bars * t.bar_len * SR))
    i0, i1 = t.idx(from_t), t.idx(to_t)
    L = b - a
    xf = int(0.006 * SR)
    for s in stems:
        src = t.stems[s][a:b].copy()
        pos = i0
        while pos < i1:
            n = min(L, i1 - pos, t.n - pos)
            if n <= 0:
                break
            chunk = src[:n].copy()
            if pos > i0 and n > xf:
                fade = np.linspace(0, 1, xf, dtype=np.float32)[:, None]
                chunk[:xf] = chunk[:xf] * fade + t.stems[s][pos:pos + xf] * (1 - fade)
            t.stems[s][pos:pos + n] = chunk
            pos += n
    t.stems["vocals"][i0:i1] = 0
    t.refresh()


# ---------- transition techniques ----------
# A = outgoing, B = incoming; ts/te are timeline seconds of the overlap.

def t_stem_swap(A, B, ts, te, bars, o):
    """The bread and butter controller blend, done with stems.
    A's vocal ends (with an echo on its last word) as the overlap starts.
    B's drums ride in, bass swaps on the half way phrase, B's melody comes up,
    A's drums leave, and B's vocal is only allowed in once A is gone."""
    L = te - ts
    a, b = A.local, B.local
    mid = ts + L * o.get("swap_at", 0.5)
    beat = A.bar_len / 4
    if o.get("vocal_echo", True):
        vocal_echo(A, a(ts))
    cut(A, ["vocals"], a(ts), 0)
    hold(B, ["vocals", "bass", "other"], b(ts), b(mid), 0)
    ramp(B, ["drums"], b(ts), b(ts + L * 0.25), 0, 1)
    cut(A, ["bass"], a(mid), 0)
    ramp(B, ["bass"], b(mid), b(mid) + beat * 0.5, 0, 1)
    ramp(B, ["other"], b(mid), b(ts + L * 0.75), 0, 1)
    ramp(A, ["other"], a(mid), a(ts + L * 0.75), 1, 0)
    ramp(A, ["drums"], a(ts + L * 0.75), a(te), 1, 0)
    hold(B, ["vocals"], b(ts), b(te), 0)
    ramp(B, ["vocals"], b(te), b(te) + SNAP, 0, 1)


def t_loop_bridge(A, B, ts, te, bars, o):
    """A's last instrumental bars loop under the whole overlap (no vocals), then stem swap.
    Use when A's song has no instrumental gap where you want to leave."""
    lb = o.get("loop_bars", 2)
    src_bar = o.get("loop_from_bar")
    if src_bar is None:
        # default: the bars right before the overlap
        src_bar = round((A.local(ts) - A.first_db) / A.bar_len) - lb
    loop_region(A, src_bar, lb, A.local(ts), A.local(te) + 0.1)
    t_stem_swap(A, B, ts, te, bars, o)


def t_acapella_over(A, B, ts, te, bars, o):
    """B's vocal comes in over A's instrumental; on the last downbeat the beats swap
    (the "drop"). Needs keys within one Camelot step."""
    a, b = A.local, B.local
    if o.get("vocal_echo", True):
        vocal_echo(A, a(ts))
    cut(A, ["vocals"], a(ts), 0)
    hold(B, INST, b(ts), b(te), 0)
    ramp(B, ["vocals"], b(ts), b(ts) + SNAP, 0, 1)
    build = o.get("build_bars", 4) * A.bar_len
    if build:
        A.sweeps.append((a(te) - build, a(te), 30.0, 600.0))
    cut(A, INST, a(te), 0)
    ramp(B, INST, b(te), b(te) + SNAP, 0, 1)


def t_filter_blend(A, B, ts, te, bars, o):
    """A's vocal ends, A gets a rising high pass and fades; B's instrumental comes up,
    its bass lands on the last beat, its vocal after."""
    a, b = A.local, B.local
    beat = B.bar_len / 4
    if o.get("vocal_echo", True):
        vocal_echo(A, a(ts))
    cut(A, ["vocals"], a(ts), 0)
    A.sweeps.append((a(ts), a(te), 30.0, o.get("max_hz", 1500.0)))
    ramp(A, INST, a(ts + (te - ts) * 0.6), a(te), 1, 0)
    hold(B, ["vocals", "bass"], b(ts), b(te), 0)
    ramp(B, ["drums", "other"], b(ts), b(ts + (te - ts) * 0.5), 0, 1)
    ramp(B, ["bass"], b(te) - beat, b(te), 0, 1)
    ramp(B, ["vocals"], b(te), b(te) + SNAP, 0, 1)


def t_echo_out(A, B, ts, te, bars, o):
    """A's last beat (or just its vocal) repeats into a fading delay while B drops clean."""
    a, b = A.local, B.local
    beat = A.bar_len / 4
    src = o.get("source", "all")
    A.echoes.append({"src": STEMS if src == "all" else [src], "s0": a(ts) - beat * o.get("send_beats", 1),
                     "s1": a(ts), "place": a(ts), "tail": te - ts + 2 * A.bar_len, "beat": beat, "hp": 250})
    cut(A, STEMS, a(ts), 0)
    ramp(B, STEMS, b(ts), b(ts) + 0.005, 0, 1)


def t_cut(A, B, ts, te, bars, o):
    """Hard cut on the one, optionally echoing A's last vocal word over B's first bar."""
    if o.get("vocal_echo", False):
        vocal_echo(A, A.local(ts))
    cut(A, STEMS, A.local(ts), 0)
    ramp(B, STEMS, B.local(ts), B.local(ts) + 0.005, 0, 1)


def riser(seconds, level=0.12):
    """White noise sweep that climbs in pitch and volume into the drop."""
    n = int(seconds * SR)
    rng = np.random.default_rng(7)
    noise = rng.standard_normal((n, 2)).astype(np.float64)
    out = np.zeros_like(noise)
    block, zi = 512, None
    for j in range(0, n, block):
        frac = j / max(1, n)
        sos = butter(2, 300 * (8000 / 300) ** frac, "high", fs=SR, output="sos")
        if zi is None:
            zi = np.zeros((sos.shape[0], 2, 2))
        out[j:j + block], zi = sosfilt(sos, noise[j:j + block], axis=0, zi=zi)
    env = np.linspace(0, 1, n) ** 2.5
    return (out / (np.abs(out).max() + 1e-9) * env[:, None] * level).astype(np.float32)


def t_vocal_carry(A, B, ts, te, bars, o):
    """The pop blend: A keeps singing while the beat changes underneath.
    B's drums and melody (no low end) slide in under A's last vocal line, the low end
    swaps in one hit halfway, A's beat leaves, A's vocal finishes on B's beat and
    echoes on its last word, and B's own vocal starts on the next phrase."""
    L = te - ts
    a, b = A.local, B.local
    mid = ts + L * o.get("swap_at", 0.5)
    beat = A.bar_len / 4
    hold(B, ["vocals", "bass"], b(ts), b(mid), 0)
    ramp(B, ["drums", "other"], b(ts), b(ts + L * 0.25), 0, 1)
    cut(A, ["bass"], a(mid), 0)
    ramp(B, ["bass"], b(mid), b(mid) + beat * 0.25, 0, 1)
    ramp(A, ["drums"], a(mid), a(mid) + 2 * beat, 1, 0)
    ramp(A, ["other"], a(mid), a(ts + L * 0.75), 1, 0)
    hold(B, ["vocals"], b(ts), b(te), 0)
    # wordplay: A's vocal can leave a little early on its last word so B's pickup answers it
    v_out = te - beat * o.get("vocal_out_beats", 0)
    if o.get("vocal_echo", True):
        vocal_echo(A, a(v_out))
    cut(A, ["vocals"], a(v_out), 0)
    ramp(B, ["vocals"], b(te), b(te) + SNAP, 0, 1)


def t_drum_swap(A, B, ts, te, bars, o):
    """Key clash safe blend: only B's drums come in under A (drums have no key), the low
    end swaps halfway, A's drums leave, and B's melody and vocal arrive together on the
    phrase as A's music and vocal leave. Energy never dips and no two keys overlap."""
    L = te - ts
    a, b = A.local, B.local
    mid = ts + L * o.get("swap_at", 0.5)
    beat = A.bar_len / 4
    hold(B, ["vocals", "other", "bass"], b(ts), b(mid), 0)
    hold(B, ["vocals", "other"], b(mid), b(te), 0)
    ramp(B, ["drums"], b(ts), b(ts + L * 0.25), 0, 1)
    cut(A, ["bass"], a(mid), 0)
    ramp(B, ["bass"], b(mid), b(mid) + beat * 0.25, 0, 1)
    ramp(A, ["drums"], a(mid), a(mid) + 2 * beat, 1, 0)
    A.sweeps.append((a(mid), a(te), 40.0, o.get("max_hz", 350.0)))  # A music thins out
    v_out = te - beat * o.get("vocal_out_beats", 0)
    if o.get("vocal_echo", True):
        vocal_echo(A, a(v_out))
    cut(A, ["vocals"], a(v_out), 0)
    cut(A, ["other"], a(te), 0)
    ramp(B, ["vocals", "other"], b(te), b(te) + SNAP, 0, 1)


def t_eq_blend(A, B, ts, te, bars, o):
    """The default, done like a DJ on a 3 band EQ (STUDY.md R1). Spotify's smooth crossfade
    + centre bass swap, plus the one voice rule.
    B: fader up (equal power) over the first quarter, hats leading (mids -12 dB, lows killed).
    A: highs start to leave. Halfway: lows swap in one move. Then A's mids and highs fall,
    B's mids open, A's drums leave by 7/8 and A's fader closes over the last eighth.
    A's vocal finishes its line; B's vocal starts on the phrase line."""
    L = te - ts
    a, b = A.local, B.local
    beat = A.bar_len / 4
    mid = ts + L * o.get("swap_at", 0.5)
    q = lambda f: ts + L * f
    hold(B, ["vocals", "bass"], b(ts), b(mid), 0)
    ramp(B, ["drums", "other"], b(ts), b(q(0.25)), 0, 1, law="power")
    eq(B, "mid", b(ts), b(mid), -12, -6)
    eq(B, "mid", b(mid), b(q(0.875)), -6, 0)
    eq(A, "hi", a(q(0.25)), a(mid), 0, -6)
    cut(A, ["bass"], a(mid), 0)
    ramp(B, ["bass"], b(mid), b(mid) + 0.025, 0, 1)
    # pros keep some warmth in the old song: partial cuts, not mutes (deeper if B is already full)
    eq(A, "mid", a(mid), a(q(0.875)), 0, o.get("a_mid_db", -6))
    eq(A, "hi", a(mid), a(q(0.875)), -6, o.get("a_hi_db", -14))
    ramp(A, ["drums"], a(q(0.75)), a(q(0.875)), 1, 0)
    ramp(A, ["other"], a(q(0.875)), a(te), 1, 0, law="power")
    hold(B, ["vocals"], b(ts), b(te), 0)
    v_out = te - beat * o.get("vocal_out_beats", 0)
    if o.get("vocal_echo", True):
        vocal_echo(A, a(v_out))
    cut(A, ["vocals"], a(v_out), 0)
    ramp(B, ["vocals"], b(te), b(te) + SNAP, 0, 1)


def t_out_by_one(A, B, ts, te, bars, o):
    """Vocal heavy pop (STUDY.md R2): B's beat and music creep in quietly under A (no lows,
    no vocal), A keeps its warmth and mids until the last beat, then A is out and B is in
    on the one, all at once. If the keys clash, B stays silent until the one."""
    L = te - ts
    a, b = A.local, B.local
    beat = A.bar_len / 4
    h = ts + L / 2
    hold(B, ["vocals", "bass"], b(ts), b(te), 0)
    if o.get("b_silent"):
        hold(B, ["drums", "other"], b(ts), b(te), 0)
    else:
        ramp(B, ["drums", "other"], b(ts), b(ts) + beat, 0, db(-10))
        ramp(B, ["other"], b(h), b(te), db(-10), db(-4))
    ramp(A, ["bass"], a(h), a(te), 1, 0.5)
    eq(A, "hi", a(h), a(te), 0, -8)
    if o.get("vocal_echo", True):
        vocal_echo(A, a(te), beats=0.5)
    cut(A, STEMS, a(te), 0)
    for st in STEMS:
        ramp(B, [st], b(te), b(te) + 0.03, B.g[st][B.idx(b(te)) - 1], 1)


def t_slam(A, B, ts, te, bars, o):
    """Replaces the strip down (STUDY.md R3): A stays full while a resonant high pass climbs,
    its lows ease off on the last bar, its last beat is thrown into a high passed echo, and
    B lands full on its big part. No drums out, no gap."""
    a, b = A.local, B.local
    beat = A.bar_len / 4
    A.sweeps.append((a(ts), a(te), 20.0, o.get("max_hz", 200.0), "high", 1.5))
    ramp(A, ["bass"], a(te - 2 * beat), a(te), 1, 0.6)
    if o.get("riser", True):
        A.fx.append((a(te - 4 * beat), riser(4 * beat, 0.06)))
    A.echoes.append({"src": ["vocals", "other", "drums"], "s0": a(te - beat), "s1": a(te), "place": a(te),
                     "tail": 4 * beat, "beat": beat * 2, "hp": 350})
    cut(A, STEMS, a(te), 0)
    hold(B, STEMS, b(ts), b(te), 0)
    ramp(B, STEMS, b(te), b(te) + 0.005, 0, 1)


def t_strip_drop(A, B, ts, te, bars, o):
    """A strips down (drums out, then the low end), a filter and riser build, a beat of
    near silence, then B drops in full on its hook. No harmonic or beat overlap, so it
    works across any key or tempo."""
    L = te - ts
    a, b = A.local, B.local
    beat = A.bar_len / 4
    mid = ts + L / 2
    cut(A, ["drums"], a(ts), 0)
    cut(A, ["bass"], a(mid), 0)
    A.sweeps.append((a(mid), a(te), 40.0, o.get("max_hz", 900.0)))
    A.fx.append((a(mid), riser(L / 2)))
    gap = beat * o.get("gap_beats", 1)
    # wordplay: A's vocal can leave early on its last word so B's pickup answers it
    v_out = te - beat * o["vocal_out_beats"] if "vocal_out_beats" in o else te - gap
    if o.get("vocal_echo", True):
        vocal_echo(A, a(v_out))
    cut(A, ["vocals"], a(v_out), 0)
    cut(A, STEMS, a(te - gap), 0)
    hold(B, STEMS, b(ts), b(te), 0)
    ramp(B, STEMS, b(te), b(te) + 0.005, 0, 1)


def t_loop_roll(A, B, ts, te, bars, o):
    """A's last beat (ideally its last word) loops: whole beats, then halves, then
    quarters, low end gone, filter and riser climbing; B slams in on the one."""
    a, b = A.local, B.local
    beat = A.bar_len / 4
    src0 = a(ts) - beat * o.get("source_beats_back", 1)
    i_src = A.idx(src0)
    # schedule: half the roll in 1 beat loops, a quarter in 1/2, a quarter in 1/4
    total_beats = int(round((te - ts) / beat))
    plan = [(1.0, total_beats // 2), (0.5, total_beats // 4 * 2), (0.25, total_beats // 4 * 4)]
    pos = A.idx(a(ts))
    xf = int(0.003 * SR)
    for length, reps in plan:
        n = int(round(length * beat * SR))
        for _ in range(reps):
            for s in STEMS:
                chunk = A.stems[s][i_src:i_src + n].copy()
                if len(chunk) > 2 * xf:
                    chunk[:xf] *= np.linspace(0, 1, xf, dtype=np.float32)[:, None]
                    chunk[-xf:] *= np.linspace(1, 0, xf, dtype=np.float32)[:, None]
                m = min(len(chunk), A.n - pos)
                A.stems[s][pos:pos + m] = chunk[:m]
            pos += n
    A.refresh()
    cut(A, ["bass"], a(ts), 0)
    A.sweeps.append((a(ts), a(te), 100.0, o.get("max_hz", 1800.0), "high", 1.4))
    ramp(A, ["vocals", "drums", "other"], a(ts), a(te), 1, db(2))  # the roll climbs, never fades
    A.fx.append((a(ts), riser(te - ts, 0.08)))
    cut(A, STEMS, a(te), 0)
    hold(B, STEMS, b(ts), b(te), 0)
    if o.get("b_under"):
        # B's build plays underneath, low end killed, a low pass opening up into the drop
        ramp(B, ["drums", "other"], b(ts), b(ts) + beat, 0, o.get("b_under_level", 0.7))
        B.sweeps.append((b(ts), b(te), 400.0, 12000.0, "low", 1.2))
    ramp(B, STEMS, b(te), b(te) + 0.005, 0, 1)


# ---------- lyric aware vocal edges ----------

def load_words(t):
    p = ROOT / "lyrics" / f"{t.name}.json"
    if not p.exists():
        return []
    from .lyrics import clean_words
    return [{"s": (w["start"] - t.c0) / t.ratio, "e": (w["end"] - t.c0) / t.ratio}
            for w in clean_words(json.loads(p.read_text())["words"])]


def vocal_edge(t, t0, t1, rising):
    i0, i1 = t.idx(t0), t.idx(t1)
    g = t.g["vocals"][i0:i1]
    if len(g) < 2:
        return None
    above = g > 0.5
    for f in np.nonzero(above[1:] != above[:-1])[0]:
        if above[f + 1] == rising:
            return (i0 + f + 1) / SR
    return None


def respect_words(A, B, ts, te, skip_a=False, pickup_beats=1.5):
    """Never chop a word, never stack two singers.
    The outgoing singer finishes the word they are on; the incoming singer opens early
    enough to catch a pickup that starts before the bar. If the held word would run into
    the pickup, the held word is cut just before it and thrown into an echo instead."""
    beat = A.bar_len / 4
    wa, wb = load_words(A), load_words(B)
    cut_t = vocal_edge(A, A.local(ts - A.bar_len), A.local(te + A.bar_len), rising=False)
    in_t = vocal_edge(B, B.local(ts - 0.1), B.local(te + 2 * B.bar_len), rising=True)

    # where the incoming singer really starts (timeline seconds)
    b_start = None
    if wb and in_t is not None:
        cands = [i for i, w in enumerate(wb) if w["e"] > in_t + 0.03 and w["s"] > in_t - pickup_beats * beat]
        if cands:
            i = cands[0]
            w = wb[i]
            gap_before = w["s"] - wb[i - 1]["e"] if i > 0 else 9
            if w["s"] < in_t and (gap_before > 0.25 or w["e"] > in_t + 0.03):
                # a pickup that begins a line, or a word already underway: start on it
                b_start = B.offset + max(w["s"] - 0.04, wb[i - 1]["e"] + 0.01 if i > 0 else 0)
            else:
                b_start = B.offset + max(in_t, w["s"] - 0.04)

    # how long the outgoing singer needs to finish the current word
    if wa and cut_t is not None and not skip_a:
        end = A.offset + cut_t
        k = next((k for k, w in enumerate(wa) if w["s"] < cut_t - 0.03 < w["e"]), None)
        if k is not None and wa[k]["e"] - cut_t < 2 * beat:
            # finish the word, but stop short of the next one if the line runs straight on
            nxt = wa[k + 1]["s"] - 0.03 if k + 1 < len(wa) else 1e9
            end = A.offset + min(wa[k]["e"] + 0.06, nxt)
        clash = b_start is not None and end > b_start - 0.05
        if clash:
            end = b_start - 0.05
            vocal_echo(A, A.local(end), beats=0.5)
        e_loc = A.local(end)
        if e_loc > cut_t:
            A.g["vocals"][A.idx(cut_t - 0.1):A.idx(e_loc)] = 1.0
        n = A.idx(e_loc + 0.06) - A.idx(e_loc)
        A.g["vocals"][A.idx(e_loc):A.idx(e_loc) + n] = np.linspace(1, 0, n)
        A.g["vocals"][A.idx(e_loc) + n:A.idx(A.keep[1])] = 0

    if b_start is not None and in_t is not None:
        s_loc = B.local(b_start)
        n = B.idx(in_t) - B.idx(s_loc)
        if n > 0:
            B.g["vocals"][B.idx(s_loc):B.idx(in_t)] = np.linspace(0.6, 1, n)


DROPS = {"strip_drop", "loop_roll", "slam"}  # B is silent until the overlap ends; b_entry_bar = where B lands


TECHNIQUES = {"stem_swap": t_stem_swap, "loop_bridge": t_loop_bridge, "acapella_over": t_acapella_over,
              "filter_blend": t_filter_blend, "echo_out": t_echo_out, "cut": t_cut,
              "bass_swap": t_stem_swap, "vocal_carry": t_vocal_carry,
              "strip_drop": t_strip_drop, "loop_roll": t_loop_roll, "drum_swap": t_drum_swap,
              "eq_blend": t_eq_blend, "out_by_one": t_out_by_one, "slam": t_slam}


# ---------- rendering ----------

def biquad(fc, kind, q):
    """RBJ cookbook biquad as one sos row: a DJ filter with a little resonance."""
    w = 2 * np.pi * min(fc, SR * 0.45) / SR
    al, cw = np.sin(w) / (2 * q), np.cos(w)
    if kind == "high":
        b = [(1 + cw) / 2, -(1 + cw), (1 + cw) / 2]
    else:
        b = [(1 - cw) / 2, 1 - cw, (1 - cw) / 2]
    a = [1 + al, -2 * cw, 1 - al]
    return np.array([[b[0] / a[0], b[1] / a[0], b[2] / a[0], 1.0, a[1] / a[0], a[2] / a[0]]])


EQ_HI = butter(4, 2500, "high", fs=SR, output="sos")


def render_track(t):
    inst = (t.stems["drums"] * t.g["drums"][:, None] + t.stems["other"] * t.g["other"][:, None]).astype(np.float64)
    if (t.eq["mid"] != 1).any() or (t.eq["hi"] != 1).any():
        hi = sosfiltfilt(EQ_HI, inst, axis=0)
        inst = (inst - hi) * t.eq["mid"][:, None] + hi * t.eq["hi"][:, None]
    out = inst + (t.stems["vocals"] * t.g["vocals"][:, None] + t.stems["bass"] * t.g["bass"][:, None])
    for sw in t.sweeps:
        s0, s1, f0, f1 = sw[:4]
        kind = sw[4] if len(sw) > 4 else "high"
        q = sw[5] if len(sw) > 5 else 0.707
        i0, i1 = t.idx(s0), t.idx(s1)
        block, zi = 512, None
        for j in range(i0, i1, block):
            fc = f0 * (f1 / f0) ** ((j - i0) / max(1, i1 - i0))
            sos = biquad(fc, kind, q)
            if zi is None:
                zi = np.zeros((sos.shape[0], 2, out.shape[1]))
            out[j:j + block], zi = sosfilt(sos, out[j:j + block], axis=0, zi=zi)
    for place, audio in t.fx:
        i = t.idx(place)
        n = min(len(audio), t.n - i)
        if n > 0:
            out[i:i + n] += audio[:n]
    for e in t.echoes:
        src = sum(t.stems[s][t.idx(e["s0"]):t.idx(e["s1"])] for s in e["src"])
        buf = np.zeros((len(src) + int(e["tail"] * SR), 2), dtype=np.float32)
        buf[:len(src)] = src
        fx = pb.Pedalboard([pb.HighpassFilter(e["hp"]),
                            pb.Delay(delay_seconds=e["beat"] / 2, feedback=0.55, mix=1.0)])
        wet = fx(buf.T, SR).T[len(src):]
        wet *= np.linspace(1, 0, len(wet))[:, None] ** 1.5
        i = t.idx(e["place"])
        n = min(len(wet), t.n - i)
        if n > 0:
            out[i:i + n] += wet[:n]
    return out


def windows(plan):
    """First and last bar each track needs, so we only load that part."""
    w = {}
    tracks = plan["tracks"]
    for i, s in enumerate(tracks):
        lo = s.get("start_bar", 0) if i == 0 else None
        hi = s.get("end_bar") if i == len(tracks) - 1 else None
        w[s["id"]] = [lo, hi]
    for tr in plan["transitions"]:
        w[tr["to"]][0] = tr["b_entry_bar"]
        w[tr["from"]][1] = tr["a_exit_bar"] + 4
    return w


def build(plan_path):
    plan, tracks, events, mix = layout_and_render(plan_path)
    return finish(plan_path, plan, tracks, events, mix)


def layout(plan_path):
    """Load tracks, place them on the timeline and write all automation. No rendering."""
    plan = json.loads(Path(plan_path).read_text())
    order = [s["id"] for s in plan["tracks"]]
    win = windows(plan)
    tracks = {}
    for s in plan["tracks"]:
        lo, hi = win[s["id"]]
        a = json.loads((ROOT / s["analysis"]).read_text())
        tracks[s["id"]] = Track(s, lo or 0, hi or a["n_bars"])
        print(f"  loaded {s['id']}{'' if tracks[s['id']].has_stems else '  (NO STEMS: vocals cannot be cut)'}",
              flush=True)
    trans = plan["transitions"]

    first = tracks[order[0]]
    first.offset = -first.locked_bar(plan["tracks"][0].get("start_bar", 0))
    first.keep = (first.local(0), first.n / SR)
    events = []
    for tr in trans:
        A, B = tracks[tr["from"]], tracks[tr["to"]]
        bars = tr["bars"]
        ts = A.offset + A.locked_bar(tr["a_exit_bar"] - bars)
        te = ts + bars * A.bar_len
        if tr["technique"] in DROPS:
            B.offset = te - B.locked_bar(tr["b_entry_bar"])
        else:
            B.offset = ts - B.locked_bar(tr["b_entry_bar"])
        A.keep = (A.keep[0], A.local(te + 3 * A.bar_len))
        B.keep = (B.local(ts), B.n / SR)
        events.append((tr, A, B, ts, te))

    # loudness: match the played part of each song, then ride each incoming song
    # part way to the level of what it replaces
    meter = pyln.Meter(SR)
    for t in tracks.values():
        seg = t.audio[t.idx(t.keep[0]):t.idx(t.keep[1])]
        if len(seg) > 3 * SR:
            t.scale(10 ** ((-14.0 - meter.integrated_loudness(seg)) / 20))

    def loud(t, a, b):
        seg = t.audio[t.idx(t.local(a)):t.idx(t.local(b))]
        return meter.integrated_loudness(seg) if len(seg) > SR else None
    for tr, A, B, ts, te in events:
        la, lb = loud(A, ts - 8, ts), loud(B, te, te + 8)
        if la is not None and lb is not None and np.isfinite(la) and np.isfinite(lb):
            B.scale(10 ** (np.clip((la - lb) * 0.7, -3, 3) / 20))

    for t in tracks.values():
        hold(t, STEMS, *t.keep, 1.0)
    last = tracks[order[-1]]
    end_bar = plan["tracks"][-1].get("end_bar")
    if end_bar:
        fade_s = last.bar(end_bar)
        last.keep = (last.keep[0], fade_s)
        ramp(last, STEMS, fade_s - 4 * last.bar_len, fade_s, 1.0, 0.0)
        hold(last, STEMS, fade_s, last.n / SR, 0)

    for tr, A, B, ts, te in events:
        TECHNIQUES[tr["technique"]](A, B, ts, te, tr["bars"], tr.get("opts", {}))
        respect_words(A, B, ts, te, skip_a=tr["technique"] == "loop_roll",
                      pickup_beats=tr.get("opts", {}).get("pickup_beats", 1.5))
    # a track's gains end with its window
    for t in tracks.values():
        hold(t, STEMS, t.keep[1], t.n / SR, 0)
    return plan, tracks, events


def layout_and_render(plan_path):
    plan, tracks, events = layout(plan_path)

    total = max(t.offset + t.n / SR for t in tracks.values())
    total = min(total, max(t.offset + t.keep[1] for t in tracks.values()) + 8)
    mix = np.zeros((int(total * SR), 2))
    for t in tracks.values():
        rendered = render_track(t)
        i0 = int(round(t.offset * SR))
        s0 = max(0, -i0)
        n = min(len(rendered) - s0, len(mix) - max(0, i0))
        if n > 0:
            mix[max(0, i0):max(0, i0) + n] += rendered[s0:s0 + n]

    master = pb.Pedalboard([pb.Limiter(threshold_db=-1.0, release_ms=120)])
    mix = master(mix.T.astype(np.float32), SR).T * 10 ** (-1.0 / 20)  # -1 dBFS ceiling, MP3 safe
    nz = np.nonzero(np.abs(mix).max(axis=1) > 1e-4)[0]
    mix = mix[: nz[-1] + SR // 2] if len(nz) else mix

    return plan, tracks, events, mix


def finish(plan_path, plan, tracks, events, mix):
    order = [s["id"] for s in plan["tracks"]]
    first = tracks[order[0]]
    name = Path(plan_path).stem
    out_dir = ROOT / "mixes"
    out_dir.mkdir(exist_ok=True)
    wav = out_dir / f"{name}.wav"
    sf.write(wav, mix, SR)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-b:a", "320k",
                    str(wav.with_suffix(".mp3"))], check=True)

    lines = [f"# {plan.get('title', name)}", ""]
    fmt = lambda s: f"{int(s // 60):02d}:{int(s % 60):02d}"
    lines.append(f"{fmt(0)}  {first.id}  ({first.a['bpm']} -> {first.play_bpm} bpm, {first.a['camelot']})")
    for tr, A, B, ts, te in events:
        lines.append(f"{fmt(ts)}  {B.id}  ({B.a['bpm']} -> {B.play_bpm} bpm, {B.a['camelot']})  "
                     f"[{tr['technique']}, {tr['bars']} bars]")
        if tr.get("why"):
            lines.append(f"        {tr['why']}")
    (out_dir / f"{name}.tracklist.md").write_text("\n".join(lines) + "\n")

    for t in tracks.values():
        for k, ms, sc in getattr(t, "locks", []):
            print(f"  lock {t.id[:30]:<30} bar {k:>3}: {ms:>4} ms (kick {sc}{', used' if sc > 1.2 else ', grid kept'})")
    print(f"wrote {wav} ({len(mix) / SR:.1f}s) + mp3 + tracklist")
    from .judge import judge, print_report
    report = judge(mix, events, name)
    print_report(report)
    (out_dir / f"{name}.judge.json").write_text(json.dumps(report, indent=1))
    return mix, events


if __name__ == "__main__":
    build(sys.argv[1])
