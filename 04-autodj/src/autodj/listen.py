"""The critic: sits through a rendered set and writes honest notes.

Claude can't hear, so this listens with measurements that map to what a person notices:
  - vocal exits: chopped mid-word? cut mid-line? what were the last words?
  - vocal entries: does the next singer start at the top of a line, or mid-sentence?
  - dead air: stretches with no vocal at all (pop needs a voice)
  - key clash: harmonic dissonance between the two songs while both play notes
  - low end: both kicks/basses up at once
  - energy: holes and spikes in short term loudness around each transition
  - per song: how long it plays, whether its title hook is actually heard

usage: python -m autodj.listen plans/set03_party.json   (after autodj.mix has rendered it)
"""
import json
import re
import sys
from pathlib import Path

import librosa
import numpy as np
import pyloudnorm as pyln
import soundfile as sf

from .analyze import SR
from .mix import STEMS, layout

ROOT = Path(__file__).resolve().parent.parent

# how harsh each interval (in semitones, 0..6) sounds when two pitch classes overlap
DISSONANCE = np.array([0.0, 1.0, 0.45, 0.15, 0.1, 0.05, 0.8])


def lyrics(t):
    p = ROOT / "lyrics" / f"{t.name}.json"
    if not p.exists():
        return None
    from .lyrics import clean_words
    lyr = json.loads(p.read_text())
    lyr["words"] = clean_words(lyr["words"])
    return lyr


def fader_edges(t, stem, t0, t1, rising):
    """Local time where a stem's fader crosses 0.5 (rising or falling) inside [t0, t1]."""
    i0, i1 = t.idx(t0), t.idx(t1)
    g = t.g[stem][i0:i1]
    if len(g) < 2:
        return None
    above = g > 0.5
    flips = np.nonzero(above[1:] != above[:-1])[0]
    for f in flips:
        if above[f + 1] == rising:
            return (i0 + f + 1) / SR
    return None


def words_between(lyr, a, b):
    return [w for w in lyr["words"] if w["end"] > a and w["start"] < b]


def describe_exit(t, t_cut_local):
    """What happens to t's vocal at the moment its fader drops."""
    lyr = lyrics(t)
    if not lyr:
        return "no lyrics available"
    tc = t.orig(t_cut_local)
    # a cut within ~80 ms of a word boundary is inaudible (and inside whisper's timing error)
    spanning = [w for w in lyr["words"] if w["start"] < tc - 0.05 and tc < w["end"] - 0.08]
    before = [w for w in lyr["words"] if w["end"] <= tc + 0.05][-6:]
    after = [w for w in lyr["words"] if w["start"] >= tc - 0.05][:4]
    line = next((l for l in lyr["lines"] if l["start"] < tc - 0.3 < l["end"] - 0.4), None)
    last = " ".join(w["w"] for w in before)
    nxt = " ".join(w["w"] for w in after)
    if spanning:
        verdict = f"CHOPS A WORD: '{spanning[0]['w']}'"
    elif line and after and after[0]["start"] - tc < 0.6:
        verdict = "cuts mid-line (the next word was about to come)"
    elif after and after[0]["start"] < tc - 0.02:
        verdict = "clips the start of the next word"
    else:
        verdict = "clean: lands between lines"
    return f"{verdict}. last words: \"...{last}\" | would have continued: \"{nxt}...\""


def describe_entry(t, t_in_local):
    lyr = lyrics(t)
    if not lyr:
        return "no lyrics available"
    ti = t.orig(t_in_local)
    spanning = [w for w in lyr["words"] if w["start"] < ti - 0.05 and ti < w["end"] - 0.08]
    line = next((l for l in lyr["lines"] if l["start"] < ti - 0.05 < l["end"]), None)
    first = " ".join(w["w"] for w in [w for w in lyr["words"] if w["start"] >= ti - 0.05][:7])
    prev = [w for w in words_between(lyr, line["start"], ti) if w["end"] <= ti + 0.05] if line else []
    # it only counts as mid-line if the skipped words were being sung right before the entry
    rest = [w for w in words_between(lyr, ti, line["end"])] if line else []
    # skipping a whole line (all its words end before the entry) is a clean line boundary
    missed = " ".join(w["w"] for w in prev) if prev and rest and ti - prev[-1]["end"] < 1.0 else ""
    if spanning:
        verdict = f"ENTERS MID-WORD on '{spanning[0]['w']}'"
    elif line and missed:
        verdict = f"enters mid-line (skips \"{missed}\")"
    else:
        verdict = "clean: starts at the top of a line"
    return f"{verdict}. first words: \"{first}...\""


def chroma_of(t, stems, a, b):
    i0, i1 = t.idx(a), t.idx(b)
    if i1 - i0 < SR:
        return None
    x = sum(t.stems[s][i0:i1] * t.g[s][i0:i1, None] for s in stems).mean(axis=1)
    if np.abs(x).max() < 1e-4:
        return None
    c = librosa.feature.chroma_cqt(y=x, sr=SR, hop_length=4096).mean(axis=1)
    return c / (c.sum() + 1e-9)


def clash_score(ca, cb):
    score = 0.0
    for i in range(12):
        for j in range(12):
            d = min((i - j) % 12, (j - i) % 12)
            score += ca[i] * cb[j] * DISSONANCE[d]
    return score


def harmonic_clash(A, B, ts, te):
    """Dissonance of A's and B's notes while both are audible, vs each song with itself."""
    a, b = A.local, B.local
    ca = chroma_of(A, ["vocals", "other"], a(ts), a(te))
    cb = chroma_of(B, ["vocals", "other"], b(ts), b(te))
    if ca is None or cb is None:
        return None
    cross = clash_score(ca, cb)
    self_ref = (clash_score(ca, ca) + clash_score(cb, cb)) / 2
    return round(cross / (self_ref + 1e-9), 2)  # ~1.0 = as consonant as each song alone


def vocal_presence(tracks, t0, t1, step):
    """Per step: summed (vocal fader x vocal map) over all tracks."""
    out = []
    t = t0
    while t < t1:
        v = 0.0
        for T in tracks.values():
            lt = T.local(t)
            if lt < 0 or lt >= T.n / SR:
                continue
            k = int(np.floor((lt - T.first_db) / T.bar_len))
            g = T.g["vocals"][T.idx(lt)]
            v += g * T.vocal_level(k)
        out.append(v)
        t += step
    return np.array(out)


def short_term_lufs(mix, t0, t1, win=3.0, hop=0.5):
    meter = pyln.Meter(SR, block_size=0.4)
    vals = []
    t = t0
    while t + win <= t1:
        seg = mix[int(t * SR):int((t + win) * SR)]
        vals.append(meter.integrated_loudness(seg) if len(seg) > SR else -70)
        t += hop
    return np.array(vals)


def fmt(s):
    return f"{int(s // 60):02d}:{int(s % 60):02d}"


def title_words(track_id):
    title = track_id.split(" - ", 1)[-1]
    title = re.sub(r"\(.*?\)", "", title)
    return [w for w in re.findall(r"[a-z']+", title.lower()) if len(w) > 2]


def listen(plan_path):
    plan, tracks, events = layout(plan_path)
    name = Path(plan_path).stem
    mix, _ = sf.read(ROOT / "mixes" / f"{name}.wav", dtype="float32")
    notes = [f"# Listening notes: {plan.get('title', name)}", ""]
    problems = 0

    for k, (tr, A, B, ts, te) in enumerate(events):
        tech = tr["technique"]
        notes.append(f"## {k + 1}. {fmt(ts)} {A.id} -> {B.id}  [{tech}, {tr['bars']} bars]")
        issues = []

        # vocal exit / entry
        a_cut = fader_edges(A, "vocals", A.local(ts - A.bar_len), A.local(te + A.bar_len), rising=False)
        if a_cut is not None and tech != "loop_roll":  # a roll replaces the audio, lyrics no longer apply
            d = describe_exit(A, a_cut)
            notes.append(f"- A vocal out at {fmt(A.offset + a_cut)}: {d}")
            if not d.startswith("clean"):
                issues.append("A vocal exit")
        b_in = fader_edges(B, "vocals", B.local(ts - 0.1), B.local(te + 2 * B.bar_len), rising=True)
        if b_in is None:
            b_in = B.local(ts) if tech in ("cut", "echo_out") else B.local(te)
        d = describe_entry(B, b_in)
        notes.append(f"- B vocal in at {fmt(B.offset + b_in)}: {d}")
        if not d.startswith("clean") and "no lyrics" not in d:
            issues.append("B vocal entry")

        # harmony
        hc = harmonic_clash(A, B, ts, te) if te - ts > 1 else None
        if hc is not None:
            verdict = "fine" if hc < 1.15 else ("a bit sour" if hc < 1.35 else "CLASHES")
            notes.append(f"- harmony while both play: {hc}x the dissonance of each song alone -> {verdict}")
            if hc >= 1.15:
                issues.append("key clash")

        # dead air around the transition
        step = A.bar_len / 4
        vp = vocal_presence(tracks, ts - 2 * A.bar_len, te + 2 * A.bar_len, step)
        run, worst = 0, 0
        for v in vp:
            run = run + 1 if v < 0.15 else 0
            worst = max(worst, run)
        if worst * step > 2 * A.bar_len:
            notes.append(f"- no vocal for {worst * step:.0f}s ({worst / 4:.0f} bars) around the switch")
            issues.append("dead air")

        # energy
        lu = short_term_lufs(mix, max(0, ts - 10), te + 10)
        if len(lu) > 4:
            pre = np.median(lu[:6])
            dip = pre - lu.min()
            jump = lu[-6:].mean() - pre
            notes.append(f"- energy: before {pre:.1f} LUFS, lowest {lu.min():.1f}, after {lu[-6:].mean():.1f}")
        # the pros' rule: energy never dips. 3 s loudness through the change must stay within
        # 2 LU of the quieter of A's last 8 bars and B's first 8 bars
        pre_a = short_term_lufs(mix, max(0, ts - 8 * A.bar_len), ts)
        post_b = short_term_lufs(mix, te + B.bar_len, te + 9 * B.bar_len)
        through = short_term_lufs(mix, max(0, ts - 1.5), te + B.bar_len + 1.5)
        if len(pre_a) and len(post_b) and len(through):
            floor = min(np.median(pre_a), np.median(post_b))
            hole = floor - through.min()
            notes.append(f"- energy floor {floor:.1f} LUFS, deepest point {through.min():.1f} ({hole:+.1f} LU below)")
            if hole > 2 and not tr.get("opts", {}).get("breakdown"):
                issues.append(f"energy dips {hole:.0f} LU")
            if abs(jump) > 4:
                issues.append(f"level {'jump' if jump > 0 else 'drop'} {abs(jump):.0f} dB")

        # low end
        ia = slice(A.idx(A.local(ts)), A.idx(A.local(te)))
        ib = slice(B.idx(B.local(ts)), B.idx(B.local(te)))
        n = min(ia.stop - ia.start, ib.stop - ib.start)
        if n > 0 and ((A.g["bass"][ia][:n] > 0.35) & (B.g["bass"][ib][:n] > 0.35)).mean() > 0.05:
            issues.append("two low ends")

        notes.append(f"- VERDICT: {'nah: ' + ', '.join(issues) if issues else 'works'}")
        notes.append("")
        problems += len(issues)

    # per song
    notes.append("## Songs")
    for s in plan["tracks"]:
        T = tracks[s["id"]]
        start, end = T.keep
        secs = end - start
        lyr = lyrics(T)
        heard = ""
        if lyr:
            # only words while the vocal fader is up
            ws = [w for w in lyr["words"]
                  if start <= (w["start"] - T.c0) / T.ratio <= end
                  and T.g["vocals"][T.idx((w["start"] - T.c0) / T.ratio)] > 0.5]
            heard = " ".join(w["w"].lower() for w in ws)
        hook = None
        if lyr:
            from .hooks import hook_candidates, words
            heard_set = set(re.findall(r"[a-z']+", heard))
            cands = [h for h, _ in hook_candidates(T.name) if h]
            if cands:
                hook = any(len(words(h["text"]) & heard_set) / len(words(h["text"])) > 0.75 for h in cands)
        flag = ""
        if secs < 40:
            flag += " TOO SHORT"
        if secs > 150:
            flag += " too long"
        if hook is False:
            flag += " HOOK (chorus) NEVER HEARD"
        notes.append(f"- {s['id']}: plays {secs:.0f}s{flag}")
        if flag:
            problems += 1

    notes.append("")
    notes.append(f"**{problems} problems flagged.**")
    out = ROOT / "mixes" / f"{name}.notes.md"
    out.write_text("\n".join(notes) + "\n")
    print("\n".join(notes))
    return problems


if __name__ == "__main__":
    listen(sys.argv[1])
