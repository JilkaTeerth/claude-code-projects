#!/usr/bin/env python3
"""
genimg.py — fal.ai image-generation bridge for the YouTube pipeline.

Replaces Palmier Pro's dead generate_image. Parses an episode's
02_IMAGE_PROMPTS.md, prepends the style header + consistency anchor to every
frame, generates each image on fal.ai (default: nano-banana-2), and writes PNGs
into <episode>/images/. Palmier then just import_media's that folder.

Usage:
  python3 pipeline/genimg.py videos/ep006-cordyceps-ant              # generate all missing
  python3 pipeline/genimg.py videos/ep006-cordyceps-ant --only img_001
  python3 pipeline/genimg.py videos/ep006-cordyceps-ant --only img_001,img_002,CARD_1
  python3 pipeline/genimg.py videos/ep006-cordyceps-ant --dry-run    # print prompts, no API calls
  python3 pipeline/genimg.py videos/ep006-cordyceps-ant --force      # regenerate even if file exists
  python3 pipeline/genimg.py videos/ep006-cordyceps-ant --aspect 1:1 --model fal-ai/nano-banana-2

Key: reads FAL_KEY from the environment or from <repo>/.env (FAL_KEY=...).
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import os
import re
import sys
import time
from pathlib import Path

# ---- config defaults ---------------------------------------------------------
DEFAULT_MODEL = "fal-ai/nano-banana-2"
DEFAULT_ASPECT = "16:9"          # YouTube frames; your playground test was 1:1
DEFAULT_CONCURRENCY = 4          # parallel fal calls
COST_PER_IMAGE = 0.08            # nano-banana-2, for the running $$ tally
MAX_RETRIES = 3

# matches:  - **img_001 [00:00]** — description....
#           - **CARD_1** — description....
PROMPT_RE = re.compile(r"^\s*-\s*\*\*(?P<id>img_\d+|CARD_\d+)\b[^*]*\*\*\s*(?:—|-)\s*(?P<desc>.+?)\s*$")


def load_env_key(repo_root: Path) -> str | None:
    if os.environ.get("FAL_KEY"):
        return os.environ["FAL_KEY"]
    env = repo_root / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line.startswith("FAL_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def parse_prompt_file(path: Path) -> tuple[str, str, list[tuple[str, str]]]:
    """Return (style_header, consistency_anchor, [(id, description), ...])."""
    text = path.read_text()

    # Style header: the backtick-quoted block right after the "Style header" label.
    style = ""
    m = re.search(r"Style header[^\n]*\n`{1,3}([^`]+)`{1,3}", text)
    if m:
        style = " ".join(m.group(1).split())

    # Consistency anchor: the bold-labelled paragraph line.
    anchor = ""
    m = re.search(r"\*\*Consistency anchor[^\n]*", text)
    if m:
        anchor = " ".join(re.sub(r"\*\*", "", m.group(0)).split())

    prompts: list[tuple[str, str]] = []
    for line in text.splitlines():
        pm = PROMPT_RE.match(line)
        if pm:
            desc = pm.group("desc").rstrip(".")
            prompts.append((pm.group("id"), desc))
    return style, anchor, prompts


def build_prompt(prefix: str, desc: str) -> str:
    return f"{prefix.strip()} FRAME: {desc.strip()}."


def generate_one(fal_client, model: str, aspect: str, prompt: str, out: Path) -> tuple[bool, str]:
    import urllib.request
    args = {"prompt": prompt, "num_images": 1, "aspect_ratio": aspect, "output_format": "png"}
    last_err = ""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = fal_client.subscribe(model, arguments=args, with_logs=False)
            images = result.get("images") or result.get("data", {}).get("images") or []
            if not images:
                last_err = f"no images in response: {str(result)[:200]}"
            else:
                url = images[0]["url"]
                urllib.request.urlretrieve(url, out)
                return True, ""
        except Exception as e:  # noqa: BLE001 — surface any fal/network error, then retry
            last_err = f"{type(e).__name__}: {e}"
        time.sleep(2 * attempt)
    return False, last_err


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("episode", help="path to episode folder (contains 02_IMAGE_PROMPTS.md)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--aspect", default=DEFAULT_ASPECT)
    ap.add_argument("--only", default="", help="comma-separated ids to generate (e.g. img_001,CARD_1)")
    ap.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    ap.add_argument("--prefix-file", default="", help="text file whose contents replace the parsed style+anchor prefix")
    ap.add_argument("--force", action="store_true", help="regenerate even if the PNG exists")
    ap.add_argument("--dry-run", action="store_true", help="print prompts, make no API calls")
    args = ap.parse_args()

    ep = Path(args.episode).expanduser().resolve()
    prompt_file = ep / "02_IMAGE_PROMPTS.md"
    if not prompt_file.exists():
        print(f"✗ no 02_IMAGE_PROMPTS.md in {ep}", file=sys.stderr)
        return 1

    repo_root = Path(__file__).resolve().parent.parent
    style, anchor, prompts = parse_prompt_file(prompt_file)
    if not prompts:
        print("✗ parsed 0 prompts — check the file format", file=sys.stderr)
        return 1

    if args.prefix_file:
        prefix = Path(args.prefix_file).expanduser().read_text().strip()
    else:
        prefix = " ".join(p for p in (style, anchor) if p)

    only = {s.strip() for s in args.only.split(",") if s.strip()}
    if only:
        prompts = [(i, d) for (i, d) in prompts if i in only]

    out_dir = ep / "images"
    out_dir.mkdir(exist_ok=True)

    print(f"Episode : {ep.name}")
    print(f"Model   : {args.model}  aspect {args.aspect}")
    print(f"Style   : {'yes' if style else 'MISSING'}   Anchor: {'yes' if anchor else 'MISSING'}")
    print(f"Frames  : {len(prompts)}  → {out_dir}")
    print("-" * 60)

    todo = []
    for pid, desc in prompts:
        out = out_dir / f"{pid}.png"
        if out.exists() and not args.force:
            print(f"· {pid}  (exists, skip)")
            continue
        todo.append((pid, build_prompt(prefix, desc), out))

    if args.dry_run:
        for pid, prompt, _ in todo:
            print(f"\n=== {pid} ===\n{prompt}")
        print(f"\n[dry-run] {len(todo)} images would cost ~${len(todo)*COST_PER_IMAGE:.2f}")
        return 0

    if not todo:
        print("Nothing to generate — all frames already present.")
        return 0

    key = load_env_key(repo_root)
    if not key:
        print("✗ FAL_KEY not found (env or .env). Add it and rerun.", file=sys.stderr)
        return 2
    os.environ["FAL_KEY"] = key
    import fal_client  # imported after key is set

    print(f"Generating {len(todo)} images (~${len(todo)*COST_PER_IMAGE:.2f}) ...\n")
    ok = fail = 0
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futs = {pool.submit(generate_one, fal_client, args.model, args.aspect, p, o): pid
                for pid, p, o in todo}
        for fut in cf.as_completed(futs):
            pid = futs[fut]
            success, err = fut.result()
            if success:
                ok += 1
                print(f"✓ {pid}   [{ok+fail}/{len(todo)}]")
            else:
                fail += 1
                print(f"✗ {pid}   {err}")

    print("-" * 60)
    print(f"Done: {ok} ok, {fail} failed in {time.time()-t0:.0f}s  ~${ok*COST_PER_IMAGE:.2f}")
    return 0 if fail == 0 else 3


if __name__ == "__main__":
    raise SystemExit(main())
