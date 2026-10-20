"""Build, critique and measure FX transitions.

usage: .venv/bin/python -W ignore -m autodj.skills.run_fx plans/skill_fx_*.json

For every plan: imports autodj.skills.fx (registers the techniques), renders with
autodj.mix.build (-> mixes/<plan>.mp3, the audition clip), runs the critic autodj.listen.listen,
then measures each FX transition:
  - loudness (400 ms momentary LUFS) per beat through the move: A before, the move's low and
    high, B after, and the step at the landing
  - for loop rolls: every slot's onset in the rendered mix vs its grid time (ms), the looped
    word, its length in beats, whether the 1 beat loop holds the whole word
  - B's first onset vs the one (ms)
Writes mixes/<plan>.fx.json.
"""
import json
import sys
from pathlib import Path

import librosa
import numpy as np
import pyloudnorm as pyln

import autodj.skills.fx  # noqa: F401  (registers techniques)
from autodj import mix
from autodj.mix import SR

ROOT = mix.ROOT


def momentary(y, t0, t1, step):
    m = pyln.Meter(SR, block_size=0.4)
    out = []
    t = t0
    while t < t1:
        seg = y[int(max(0, t) * SR):int((t + 0.4) * SR)]
        v = m.integrated_loudness(seg) if len(seg) >= int(0.4 * SR) else -70
        out.append(round(float(v) if np.isfinite(v) else -70.0, 1))
        t += step
    return out


def onsets(y, t0, t1):
    seg = y[int(t0 * SR):int(t1 * SR)].mean(axis=1)
    env = librosa.onset.onset_strength(y=seg, sr=SR, hop_length=128)
    fr = librosa.onset.onset_detect(onset_envelope=env, sr=SR, hop_length=128, backtrack=False, units="frames")
    return t0 + fr * 128 / SR


def measure(y, tr, A, B, ts, te):
    rep = dict(getattr(A, "fx_report", {}) or {})
    beat = A.bar_len / 4
    off = A.offset
    out = {"technique": tr["technique"], "mix_ts": round(ts, 2), "mix_te": round(te, 2)}
    loc = rep.get("roll_start", rep.get("swell_from", rep.get("from")))
    start = off + loc if loc is not None else ts
    curve = momentary(y, start - 8 * beat, te + 8 * beat, beat)
    pre = curve[:8]
    during = curve[8:8 + max(1, int(round((te - start) / beat)))]
    post = curve[-8:]
    out["lufs_per_beat"] = curve
    out["lufs_A_before"] = float(np.median(pre))
    out["lufs_move_min"] = float(min(during))
    out["lufs_move_max"] = float(max(during))
    out["lufs_move_last_beat"] = float(during[-1])
    out["lufs_B_after"] = float(np.median(post))
    out["landing_step_db"] = round(float(np.median(post[:4])) - float(np.median(during[-2:])), 1)
    out["move_rises"] = bool(np.polyfit(np.arange(len(during)), during, 1)[0] > 0) if len(during) > 2 else None
    # B on the one
    on = onsets(y, te - 0.15, te + 0.3)
    out["B_first_onset_ms"] = round(float((on[np.argmin(np.abs(on - te))] - te) * 1000), 1) if len(on) else None
    if tr["technique"] == "loop_roll_v1" and not rep:
        # v1 has no report: rebuild its slot grid (half 1 beat, quarter 1/2, quarter 1/4)
        tb = int(round((te - ts) / beat))
        slots, p = [], A.local(ts)
        for L, n in [(1.0, tb // 2), (0.5, tb // 4 * 2), (0.25, tb // 4 * 4)]:
            for _ in range(n):
                slots.append((p, L, L * beat))
                p += L * beat
        rep = {"fx": "loop_roll", "slots": slots, "roll_start": A.local(ts), "word": "(v1: beat before)",
               "word_beats": 1.0, "attack_local": A.local(ts) - beat * tr.get("opts", {}).get("source_beats_back", 1),
               "dominance_db": None, "schedule": "v1", "src": "all", "a_music": "loop", "b_under": False, "b_pickup": False}
    if rep.get("fx") == "loop_roll":
        on = onsets(y, off + rep["roll_start"] - 0.1, te + 0.05)
        devs = []
        for p, L, d in rep["slots"]:
            g = off + p
            if len(on):
                k = np.argmin(np.abs(on - g))
                if abs(on[k] - g) < 0.06:
                    devs.append((on[k] - g) * 1000)
        out["slots"] = len(rep["slots"])
        out["slot_onsets_found"] = len(devs)
        out["slot_onset_dev_ms_median"] = round(float(np.median(np.abs(devs))), 1) if devs else None
        out["slot_onset_dev_ms_max"] = round(float(np.max(np.abs(devs))), 1) if devs else None
        out["word"] = rep["word"]
        out["word_beats"] = rep["word_beats"]
        out["word_whole_in_1beat_loop"] = rep["word_beats"] <= 1.02
        out["word_on_grid_16ths"] = round(float(((rep["attack_local"] - A.first_db) / (A.bar_len / 16)) % 1), 2)
        out["dominance_db"] = rep["dominance_db"]
        out["schedule"] = rep["schedule"]
        out["src"], out["a_music"], out["b_under"] = rep["src"], rep["a_music"], rep["b_under"]
        out["b_pickup"] = rep["b_pickup"]
        out["mix_word_at"] = round(off + rep["attack_local"], 2)
        out["mix_roll_start"] = round(off + rep["roll_start"], 2)
    for k in ("word", "delay_beats", "feedback", "hp_hz"):
        if k in rep and k not in out:
            out[k] = rep[k]
    out["landing"] = rep.get("landing")
    return out


def main(paths):
    from autodj.listen import listen
    allrep = {}
    for p in paths:
        name = Path(p).stem
        print(f"\n===== {name}", flush=True)
        y, events = mix.build(p)
        problems = listen(p)
        reps = [measure(y, *ev) for ev in events]
        for r in reps:
            r["critic_problems"] = problems
            short = {k: v for k, v in r.items() if k != "lufs_per_beat"}
            print(json.dumps(short, default=float))
            print("  lufs/beat:", r["lufs_per_beat"])
        (ROOT / "mixes" / f"{name}.fx.json").write_text(json.dumps(reps, indent=1, default=float))
        allrep[name] = reps
    return allrep


if __name__ == "__main__":
    main(sys.argv[1:])
