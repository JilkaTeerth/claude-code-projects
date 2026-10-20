"""Find lyric hand offs between songs: A's line ends on a word or phrase that B's line opens with.

e.g. Usher "...dance like it's the last night of your life" -> Katy "Last Friday night"
     Pitbull "...but I promise tonight" -> Bieber "Tonight I wanna show you"

The Brain uses these to plan wordplay transitions (max 2 or 3 a set): A exits right after
its line, B enters on the answering line.

usage: python -m autodj.wordplay [songA_filter songB_filter]
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STOP = set("""i a the and to of in on it is you me my your we our be so oh yeah ah uh
that this but for with just like cause 'cause its it's i'm im all now up down no yes
do don't dont got get can can't what when where who are was were will gonna wanna
baby hey ooh na la""".split())


def norm(w):
    return re.sub(r"[^a-z']", "", w.lower()).strip("'")


def load(stem):
    a = json.loads((ROOT / "analysis" / f"{stem}.json").read_text())
    lyr = json.loads((ROOT / "lyrics" / f"{stem}.json").read_text())
    bar_len, first = 4 * a["beat_period"], a["first_downbeat"]
    lines = []
    for l in lyr["lines"]:
        ws = [norm(w) for w in l["text"].split()]
        ws = [w for w in ws if w]
        if len(ws) < 2:
            continue
        lines.append({"text": l["text"], "words": ws,
                      "bar0": (l["start"] - first) / bar_len, "bar1": (l["end"] - first) / bar_len})
    return lines


def content(ws):
    return [w for w in ws if w not in STOP and len(w) > 2]


def handoffs(stem_a, stem_b, top=6):
    la, lb = load(stem_a), load(stem_b)
    hooks = json.loads((ROOT / "analysis" / "_hooks.json").read_text())
    hook_b = set(norm(w) for w in hooks.get(stem_b, {}).get("hook", "").split())
    out = []
    for x in la:
        tail = content(x["words"][-3:])
        if not tail:
            continue
        for y in lb:
            head = content(y["words"][:4])
            shared = [w for w in tail if w in head]
            if not shared:
                continue
            # phrase bonus: "last ... night" both sides
            score = sum(len(w) for w in shared) + 4 * (len(shared) - 1)
            if x["words"][-1] == y["words"][0] or x["words"][-1] in head[:1]:
                score += 4  # the very last word of A is the very first thing B says
            if hook_b and len(set(y["words"]) & hook_b) / len(hook_b) > 0.6:
                score += 3  # B answers with its hook
            out.append((score, shared, x, y))
    out.sort(key=lambda o: -o[0])
    seen, best = set(), []
    for o in out:
        key = (" ".join(o[1]), round(o[3]["bar0"]))
        if key in seen:
            continue
        seen.add(key)
        best.append(o)
    return best[:top]


def main(args):
    stems = sorted(p.stem for p in (ROOT / "lyrics").glob("*.json"))
    pairs = []
    if len(args) == 2:
        sa = [s for s in stems if args[0].lower() in s.lower()]
        sb = [s for s in stems if args[1].lower() in s.lower()]
        pairs = [(a, b) for a in sa for b in sb]
    else:
        pairs = [(a, b) for a in stems for b in stems if a != b]
    rows = []
    for a, b in pairs:
        for score, shared, x, y in handoffs(a, b, top=3 if len(args) != 2 else 10):
            rows.append((score, a, b, shared, x, y))
    rows.sort(key=lambda r: -r[0])
    for score, a, b, shared, x, y in rows[:60 if len(args) != 2 else 30]:
        print(f"{score:3d} [{' '.join(shared)}] {a[:28]} bar {x['bar1']:.1f} \"...{x['text'][-45:]}\""
              f"\n      -> {b[:28]} bar {y['bar0']:.1f} \"{y['text'][:50]}\"")


if __name__ == "__main__":
    main(sys.argv[1:])
