"""Render + critique plans with the blends skill loaded.

usage: .venv/bin/python -W ignore -m autodj.skills.run_blends plans/skill_blends_01.json [...] [--diag] [--no-render]
Prints the critic's verdicts, the energy rule numbers per transition, and (--diag) a per deck
loudness table (A, B, sum in 1.5 s steps) through each overlap.
"""
import re
import sys
from pathlib import Path

import numpy as np
import pyloudnorm as pyln

import autodj.skills.blends  # noqa: F401  (registers techniques + tempo maps)
from autodj import mix
from autodj.listen import listen

ROOT = Path(__file__).resolve().parents[2]


def diag(plan):
    plan_d, tracks, events = mix.layout(plan)
    m = pyln.Meter(mix.SR, block_size=0.4)
    cache = {}

    def ren(t):
        if t.id not in cache:
            cache[t.id] = mix.render_track(t)
        return cache[t.id]

    def L(x):
        v = m.integrated_loudness(x) if len(x) > mix.SR else -70
        return -70 if not np.isfinite(v) else v
    for k, (tr, A, B, ts, te) in enumerate(events):
        ya, yb = ren(A), ren(B)
        print(f"#{k + 1} {tr['technique']} ts={ts:.1f} te={te:.1f} bar={A.bar_len:.2f}s")
        t = ts - 4
        while t < te + 6:
            def seg(T, y):
                i = T.idx(T.local(t))
                return y[i:i + int(1.5 * mix.SR)] if i < len(y) else np.zeros((10, 2))
            a, b = seg(A, ya), seg(B, yb)
            n = min(len(a), len(b))
            print(f"  {t - ts:+5.1f}s  A {L(a):6.1f}  B {L(b):6.1f}  sum {L(a[:n] + b[:n]):6.1f}")
            t += 1.5


def main(args):
    plans = [a for a in args if not a.startswith("--")]
    summary = []
    for p in plans:
        print(f"\n######## {p}")
        if "--no-render" not in args:
            mix.build(p)
        problems = listen(p)
        notes = (ROOT / "mixes" / f"{Path(p).stem}.notes.md").read_text()
        for blk in notes.split("\n## ")[1:]:
            if blk.startswith("Songs"):
                continue
            head = blk.splitlines()[0]
            fl = re.search(r"energy floor (-?[\d.]+) LUFS, deepest point (-?[\d.]+) \(([+-][\d.]+) LU", blk)
            hc = re.search(r"harmony while both play: ([\d.]+)x", blk)
            vd = re.search(r"VERDICT: (.*)", blk)
            summary.append((Path(p).stem, head[:90], fl.group(3) if fl else "?", hc.group(1) if hc else "-",
                            vd.group(1) if vd else "?"))
        if "--diag" in args:
            diag(p)
        print(f"{p}: {problems} problems")
    print("\n==== summary (hole = LU below the energy floor; > 2 fails) ====")
    for s in summary:
        print(f"{s[0]:<28} hole {s[2]:>5}  harm {s[3]:>5}  {s[4]}\n    {s[1]}")


if __name__ == "__main__":
    main(sys.argv[1:])
