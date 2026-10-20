"""explain: the explainer-video pipeline. Cheap tests first, the expensive render last.

  explain.py review <slug>              score the script against RUBRIC.md (no audio, no video)
  explain.py voice  <slug> [--beats hook,reveal] [--voices af_heart,af_bella] [--speeds 0.85,0.9]
                                        voice a few beats several ways, report real words a minute
  explain.py board  <slug>              render one still per Board* scene in board.py, one contact sheet
  explain.py build  <slug>              voice every beat, render scene.py's Video, deliver the mp4

A video lives in explainers/<slug>/: script.json (beats: id, tags, say, see), board.py, scene.py.
Run with the project's Python:  ../.venv/bin/python explain.py review dimension-theorem-v2
"""
import argparse, json, os, pathlib, re, shutil, subprocess, sys, tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
PY = ROOT / ".venv" / "bin" / "python"
MANIM = ROOT / ".venv" / "bin" / "manim"
TEX = pathlib.Path.home() / "Library/TinyTeX/bin/universal-darwin"
WPM_AT_1 = 147            # words a minute at speed 1.0 for pause-marked scripts (measured 2026-10-07, v2 hook: 126 wpm of speech at 0.86)
MARKS = {"[pause]": 0.7, "[beat]": 0.35, "[long]": 1.2}
TARGET = (115, 130)

def load(slug):
    d = HERE / slug
    return d, json.load(open(d / "script.json"))

def words(text):
    return len(re.sub(r"\[(pause|beat|long)\]", " ", text).split())

def pauses(text):
    return sum(text.count(k) * v for k, v in MARKS.items())

def projected(beat, speed):
    return words(beat["say"]) / (WPM_AT_1 * speed / 60) + pauses(beat["say"]) + 0.35

# ------------------------------------------------------------------ review
def review(slug):
    d, s = load(slug)
    beats, speed = s["beats"], s.get("speed", 0.9)
    jar = [j.lower() for j in s.get("jargon", [])]
    measured = json.load(open(d / "audio" / "durations.json")) if (d / "audio" / "durations.json").exists() else {}
    dur = {b["id"]: measured.get(b["id"]) or projected(b, speed) for b in beats}
    total, tw = sum(dur.values()), sum(words(b["say"]) for b in beats)
    wpm = tw / total * 60
    text = lambda b: re.sub(r"\[(pause|beat|long)\]", " ", b["say"])
    hook = [b for b in beats if "hook" in b.get("tags", [])]
    t, first_jar = 0.0, None
    for b in beats:
        if first_jar is None and any(re.search(rf"\b{re.escape(j)}", text(b).lower()) for j in jar):
            first_jar = t
        t += dur[b["id"]]
    sents = [x for b in beats for x in re.split(r"[.!?]+", text(b)) if x.strip()]
    avg_sent = sum(len(x.split()) for x in sents) / max(1, len(sents))
    qs = sum(text(b).count("?") for b in beats)
    marks = sum(sum(b["say"].count(k) for k in MARKS) for b in beats) / len(beats)
    # something new on screen every <= 8s: each sentence of "see" counts as one visual event
    events = lambda b: max(1, len([x for x in re.split(r"[.!?]+", b.get("see", "")) if x.strip()]))
    long_beats = [f"{b['id']} ({dur[b['id']] / events(b):.0f}s per event)" for b in beats if dur[b["id"]] / events(b) > 8]
    hook_words = set(w.lower() for b in hook for w in re.findall(r"[a-zA-Z]{4,}", text(b)))
    last = text(beats[-1]).lower()
    checks = [
        ("Pace", TARGET[0] <= wpm <= TARGET[1], f"{wpm:.0f} wpm {'measured' if measured else 'projected'} (want {TARGET[0]} to {TARGET[1]})"),
        ("Hook is jargon-free", bool(hook) and not any(re.search(rf"\b{re.escape(j)}", text(b).lower()) for b in hook for j in jar), f"{len(hook)} hook beat(s)"),
        ("Jargon arrives late", first_jar is None or first_jar >= min(45, 0.25 * total), f"first maths word at {first_jar or 0:.0f}s of {total:.0f}s (want >= {min(45, 0.25 * total):.0f}s)"),
        ("Story beat present", bool(hook), "tag a beat 'hook'"),
        ("Questions", qs >= 3, f"{qs} questions"),
        ("Short sentences", avg_sent <= 12, f"{avg_sent:.1f} words a sentence"),
        ("Pauses", marks >= 1, f"{marks:.1f} marks a beat"),
        ("Visual change", not long_beats and all(b.get("see") for b in beats), f"slow beats: {long_beats or 'none, new visual every 8s or less'}"),
        ("Exam payoff", any("exam" in b.get("tags", []) for b in beats), "tag a beat 'exam'"),
        ("Callback", any(w in last for w in hook_words), "last beat should echo the hook"),
    ]
    gates = sum(ok for _, ok, _ in checks)
    print(f"\n{s['title']}  ·  {len(beats)} beats  ·  {tw} words  ·  {total:.0f}s ({total/60:.1f} min)  ·  voice {s.get('voice')} @ {speed}\n")
    print("  HYGIENE GATES (his preferences, not quality)")
    for name, ok, note in checks:
        print(f"  {'pass' if ok else 'FAIL'}  {name:<22} {note}")
    print(f"  {gates}/10 gates\n")
    quality(d)
    for b in beats:
        print(f"  {b['id']:<10} {dur[b['id']]:5.1f}s  {words(b['say']):3}w  {','.join(b.get('tags', []))}")
    return gates

# ------------------------------------------------------------------ judged quality
WEIGHTS = {"A": 0.25, "B": 0.20, "C": 0.10, "D": 0.15, "E": 0.10, "F": 0.10, "G": 0.10}
NAMES = {"A": "Reasoning (why)", "B": "Accuracy", "C": "Motivation", "D": "Visual craft (mute)",
         "E": "Connections", "F": "Engagement (Teerth)", "G": "Exam usefulness"}
BENCH = {"A": 7, "B": 9, "C": 9, "D": 9, "E": 9, "F": 6, "G": 2}   # 3b1b ch.7, rubric v3 (benchmarks/3b1b-ch7.md)

def totals(sc):
    """Weighted and equal-weight totals, computed here only (a hand total was wrong once: 7.85 vs 7.50).
    'unscored' criteria drop out and the remaining weights are renormalised."""
    got = {k: v for k, v in sc.items() if isinstance(v, (int, float))}
    w = sum(WEIGHTS[k] for k in got)
    return sum(WEIGHTS[k] * got[k] for k in got) / w, sum(got.values()) / len(got)

def quality(d):
    f = d / "scores.json"
    if not f.exists():
        print("  QUALITY: not judged yet. Write scores.json (rubric v3): every score cites [T], [F] or [P].\n"); return None
    raw = json.load(open(f))
    sc = {k: raw[k][0] for k in WEIGHTS}
    bad = [k for k in WEIGHTS if isinstance(sc[k], (int, float)) and not re.search(r"\[(T|F|P)\]", raw[k][1]) and "capped" not in raw[k][1]]
    wt, eq = totals(sc); bw, be = totals(BENCH)
    print(f"  QUALITY (rubric v3, judged)                       benchmark 3b1b ch.7")
    for k in WEIGHTS:
        print(f"  {k} {NAMES[k]:<23} {str(sc[k]):>8}/10   3b1b {BENCH[k]:>2}   {raw[k][1]}")
    print(f"\n  weighted {wt:.2f} ({wt - bw:+.2f} vs 3b1b {bw:.2f})    equal weights {eq:.2f} ({eq - be:+.2f})")
    if (wt > bw) != (eq > be):
        print("  WARNING: the ranking against 3b1b flips with the weights. The result is fragile.")
    if bad:
        print(f"  WARNING: no evidence tag on {bad}. Rule 1: no source, no score.")
    print()
    return wt

# ------------------------------------------------------------------ voice tests
def voice(slug, beat_ids, voices, speeds):
    sys.path.insert(0, str(ROOT))
    import say, soundfile as sf
    d, s = load(slug)
    out = d / "tests"; out.mkdir(exist_ok=True)
    pick = [b for b in s["beats"] if not beat_ids or b["id"] in beat_ids]
    text = "\n\n".join(b["say"] for b in pick)
    for v in voices:
        for sp in speeds:
            a = say.speak(text, v, sp)
            f = out / f"voice_{'+'.join(b['id'] for b in pick)}_{v}_{sp}.wav"
            sf.write(f, a, say.RATE)
            secs = len(a) / say.RATE
            print(f"  {f.name:<60} {secs:5.1f}s  {words(text) / secs * 60:4.0f} wpm")

# ------------------------------------------------------------------ storyboard
def board(slug):
    d, _ = load(slug)
    src = (d / "board.py").read_text()
    names = re.findall(r"^class (Board\w*)\(", src, re.M)
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="board-"))
    env = {**os.environ, "PATH": f"{TEX}:{os.environ['PATH']}"}
    stills = []
    for n in names:
        r = subprocess.run([str(MANIM), "-s", "-r", "960,540", "--media_dir", str(tmp), "-v", "ERROR",
                            "--disable_caching", "board.py", n], cwd=d, env=env, capture_output=True, text=True)
        png = next(tmp.rglob(f"{n}*.png"), None)
        if r.returncode or not png:
            print(f"  FAIL {n}\n{r.stderr[-800:]}"); continue
        stills.append(png); print(f"  ok   {n}")
    out = d / "tests"; out.mkdir(exist_ok=True)
    if stills:
        cols = 2
        while len(stills) % cols:
            stills.append(stills[-1])
        rows = [stills[i:i + cols] for i in range(0, len(stills), cols)]
        inputs = sum([["-i", str(p)] for p in stills], [])
        fc = ";".join(f"{''.join(f'[{r*cols+c}]' for c in range(cols))}hstack=inputs={cols}[r{r}]" for r in range(len(rows)))
        fc += f";{''.join(f'[r{r}]' for r in range(len(rows)))}vstack=inputs={len(rows)}" if len(rows) > 1 else ""
        if len(rows) == 1:
            fc = fc.replace("[r0]", "")
        subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", fc, str(out / "board.png")], check=True)
        print(f"\n  {out / 'board.png'}")
    shutil.rmtree(tmp, ignore_errors=True)

# ------------------------------------------------------------------ full build
def build(slug):
    sys.path.insert(0, str(ROOT))
    import say, soundfile as sf
    d, s = load(slug)
    (d / "audio").mkdir(exist_ok=True)
    dur = {}
    for b in s["beats"]:
        a = say.speak(b["say"], s.get("voice", "af_heart"), s.get("speed", 0.9))
        sf.write(d / "audio" / f"{b['id']}.wav", a, say.RATE)
        dur[b["id"]] = round(len(a) / say.RATE, 2)
    json.dump(dur, open(d / "audio" / "durations.json", "w"), indent=1)
    review(slug)
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="build-"))
    env = {**os.environ, "PATH": f"{TEX}:{os.environ['PATH']}"}
    subprocess.run([str(MANIM), "-r", "1920,1080", "--fps", "30", "--media_dir", str(tmp), "-v", "ERROR",
                    "--progress_bar", "none", "scene.py", "Video"], cwd=d, env=env, check=True)
    mp4 = next(tmp.rglob("Video.mp4"))
    dest = pathlib.Path(os.path.expanduser(s["deliver"]))
    if (d / "mux.py").exists():               # build our own soundtrack (Manim's mixer once dropped 50s of voice)
        subprocess.run([str(PY), "mux.py", str(mp4), str(dest)], cwd=d, check=True)
    else:
        shutil.copy(mp4, dest)
    # never deliver unchecked audio: the audio must run as long as the video
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,duration", "-of", "csv=p=0", str(dest)],
                           capture_output=True, text=True).stdout
    lens = dict(line.split(",") for line in probe.split())
    assert abs(float(lens["audio"]) - float(lens["video"])) < 2, f"audio/video length mismatch: {lens}"
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n  delivered {dest}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["review", "voice", "board", "build"])
    ap.add_argument("slug")
    ap.add_argument("--beats", default="")
    ap.add_argument("--voices", default="af_heart")
    ap.add_argument("--speeds", default="0.88")
    a = ap.parse_args()
    if a.cmd == "review": review(a.slug)
    elif a.cmd == "voice": voice(a.slug, [x for x in a.beats.split(",") if x], a.voices.split(","), [float(x) for x in a.speeds.split(",")])
    elif a.cmd == "board": board(a.slug)
    else: build(a.slug)
