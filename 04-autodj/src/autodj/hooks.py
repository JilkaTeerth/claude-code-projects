"""Find each song's hook: the line that repeats the most (the chorus), with the bars
where every repeat sits. Robust to Whisper mishearing because a chorus is misheard
the same way each time.

usage: python -m autodj.hooks [name_filter]
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def words(text):
    return set(re.findall(r"[a-z']+", text.lower()))


def most_repeated(pool, lines):
    best, best_hits = None, []
    for l in pool:
        wl = words(l["text"])
        hits = [m for m in lines if len(wl & words(m["text"])) / len(wl | words(m["text"])) >= 0.5]
        if len(hits) > len(best_hits):
            best, best_hits = l, hits
    return best, best_hits


def hook_candidates(stem):
    """The chorus as the most repeated line, plus the best line that sings the title.
    Either one being heard counts as the hook being played."""
    lyr = json.loads((ROOT / "lyrics" / f"{stem}.json").read_text())
    lines = [l for l in lyr["lines"] if len(words(l["text"])) >= 3]
    prefixes = [t[:5].lower() for t in stem.split("_") if len(t) >= 5 and t.lower() not in
                ("remix", "notion", "official", "video", "muir", "blair")]
    titled = [l for l in lyr["lines"] if any(p in l["text"].lower() for p in prefixes)]
    out = []
    rep = most_repeated(lines, lines)
    if rep[0]:
        out.append(rep)
    if titled:
        out.append(most_repeated(titled, lyr["lines"]))
    return out


def find_hook(stem):
    c = hook_candidates(stem)
    return c[0] if c else (None, [])


def bar_of(a, t):
    return (t - a["first_downbeat"]) / (4 * a["beat_period"])


if __name__ == "__main__":
    filt = sys.argv[1].lower() if len(sys.argv) > 1 else ""
    out = {}
    for p in sorted((ROOT / "lyrics").glob("*.json")):
        if filt not in p.stem.lower():
            continue
        a = json.loads((ROOT / "analysis" / f"{p.stem}.json").read_text())
        hook, hits = find_hook(p.stem)
        if not hook:
            continue
        spots = [round(bar_of(a, h["start"]), 1) for h in hits]
        out[p.stem] = {"hook": hook["text"], "bars": spots}
        print(f"{p.stem}: \"{hook['text'][:70]}\" x{len(hits)} at bars {spots}")
    (ROOT / "analysis" / "_hooks.json").write_text(json.dumps(out, indent=1))
