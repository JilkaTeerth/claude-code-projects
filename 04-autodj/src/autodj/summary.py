"""Compact view of every analysed track, for the Brain (Claude) to plan a set from.

Per song: tempo, key, sections, and a bar by bar vocal map on the phrase grid:
  # singing   . faint / chops   (space) instrumental   | phrase line (every 8 bars)
usage: python -m autodj.summary [name_filter]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
filt = next((a.lower() for a in sys.argv[1:] if not a.startswith("--")), "")

for p in sorted((ROOT / "analysis").glob("*.json")):
    if filt not in p.stem.lower():
        continue
    a = json.loads(p.read_text())
    if a["file"].endswith(".wav"):
        continue
    secs = " | ".join(f"{s['start_bar']}-{s['end_bar']} {s['energy_db']:.0f}dB" for s in a["sections"])
    print(f"{p.stem}: {a['bpm']} bpm {a['camelot']} ({a['key']}), {a['n_bars']} bars, "
          f"phrases start on bar {a.get('phrase_offset', 0)} mod 4\n  sections: {secs}")
    v = a.get("vocal_bars")
    if v:
        off = a.get("phrase_offset", 0)
        for row in range(0, len(v), 64):
            cells = ""
            for k in range(row, min(row + 64, len(v))):
                if (k - off) % 8 == 0:
                    cells += "|"
                cells += "#" if v[k] > 0.35 else ("." if v[k] > 0.12 else " ")
            print(f"  {row:>4} {cells}")
    print()


def lyric_sheet(stem):
    """Each transcribed line with the bars it spans, so exits land on line ends."""
    a = json.loads((ROOT / "analysis" / f"{stem}.json").read_text())
    p = ROOT / "lyrics" / f"{stem}.json"
    if not p.exists():
        return
    bar_len, first = 4 * a["beat_period"], a["first_downbeat"]
    print(f"  lyrics ({stem}):")
    for l in json.loads(p.read_text())["lines"]:
        b0 = (l["start"] - first) / bar_len
        b1 = (l["end"] - first) / bar_len
        print(f"    bar {b0:6.1f} -> {b1:6.1f}  {l["text"][:60]}")


if "--lyrics" in sys.argv:
    for p in sorted((ROOT / "lyrics").glob("*.json")):
        if filt.replace("--lyrics", "").strip() in p.stem.lower():
            lyric_sheet(p.stem)
