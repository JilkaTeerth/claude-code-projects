#!/usr/bin/env python3
"""Batch-generate ep009 frames on fal Flux schnell in the locked 'tardigrade' doodle style.

Reads scene descriptions from an episode's 02_IMAGE_PROMPTS.md, wraps each in the
locked style template, generates every content frame, composites the chapter title
cards locally (PIL, for crisp text), and writes a review contact sheet.

  .venv/bin/python batch_images.py <episode-folder>
"""

import concurrent.futures as cf
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FAL_MODEL = "fal-ai/flux/schnell"
W, H = 1024, 576

# ---- LOCKED STYLE TEMPLATE (the winning tardigrade formula, textured + soothing) ----
STYLE = (
    "Charming childlike hand-drawn doodle in a warm storybook felt-tip marker style. "
    "Bold clean black hand-drawn outlines, flat solid fill colors, only soft gentle shading. "
    "Soothing warm earthy palette: soft pink, warm brown, cream, muted amber. "
    "Calm, cozy and friendly — never scary, never realistic, never photographic. "
    "The background is a simple hand-drawn scene with gentle soothing texture — soft cross-hatched "
    "earth, a warm ambient underground glow, subtle paper grain — atmospheric yet still crude and childlike. "
    "Uncluttered, generous negative space, one clear subject. "
)
CHAR = (
    " The naked mole rat is drawn simple and endearing: a rounded soft-pink body, two big square buck "
    "teeth at the front, small friendly round eyes, little stick legs, a thin tail — silly and cute, "
    "drawn the same simple way every frame."
)
AVOID = " Not realistic, not wrinkled, not furry, not creepy or uncanny; no gore, no dense scribbles, no glossy 3D."
NOTEXT = (" IMPORTANT: absolutely NO text, NO letters, NO numbers, NO words, NO captions or writing anywhere "
          "in the image — a purely visual wordless doodle.")


def clean_scene(s: str) -> str:
    """Strip explicit text/label requests so Flux draws wordless frames (it can't spell)."""
    s = re.sub(r"'[^']*'", "§", s)
    s = re.sub(r",?\s*(with )?(a |an |the )?(big |small |bold |faint |crude )*(hand-)?(scrawled |scrawl |written |hand-lettered |labell?ed )*§\s*(text |scrawl |scrawled |note |label |labell?ed |sign |hint |reading |written |box |says?|saying )*(above( it)?|beside it|below( it)?|over it|on top|under(neath)?( it| the \w+)?|between them)?", " ", s)
    s = re.sub(r"\b(scrawled|labell?ed|hand-lettered)\b", "", s)
    s = re.sub(r",?\s*(a |an )?(big |small |little )?(note|hint|label|caption)\b", "", s)
    s = re.sub(r"\s*[,;]\s*(and\s+)?(?=[,;]|$)", " ", s)
    return re.sub(r"\s+", " ", s).strip(" ,;.")


def build_prompt(scene: str) -> str:
    return f"{STYLE}Scene: {clean_scene(scene)}{CHAR}{AVOID}{NOTEXT}"


def parse_prompts(md: str):
    """Return ordered list of dicts: {slug, ts, kind, scene/card}."""
    items = []
    for line in md.splitlines():
        m = re.match(r"- \*\*(img_\d+) \[(\d{2}:\d{2})\]\*\* — (.+)", line)
        if m:
            items.append({"slug": m.group(1), "ts": m.group(2), "kind": "img", "scene": m.group(3).rstrip(".")})
            continue
        c = re.match(r'- \*\*(CARD_\d+) \[(\d{2}:\d{2})\]\*\* — .*?"([^"]+)" over "([^"]+)"', line)
        if c:
            items.append({"slug": c.group(1), "ts": c.group(2), "kind": "card",
                          "line1": c.group(3), "line2": c.group(4)})
    return items


def fal_submit(key, prompt, seed):
    body = json.dumps({"prompt": prompt, "image_size": "landscape_16_9",
                       "num_inference_steps": 4, "seed": seed,
                       "enable_safety_checker": False}).encode()
    req = urllib.request.Request(f"https://queue.fal.run/{FAL_MODEL}", data=body,
                                 headers={"Authorization": f"Key {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["request_id"]


def fal_wait(key, rid, tries=40):
    base = f"https://queue.fal.run/fal-ai/flux/requests/{rid}"
    for _ in range(tries):
        req = urllib.request.Request(f"{base}/status", headers={"Authorization": f"Key {key}"})
        with urllib.request.urlopen(req, timeout=60) as r:
            if json.load(r)["status"] == "COMPLETED":
                break
        time.sleep(1.5)
    req = urllib.request.Request(base, headers={"Authorization": f"Key {key}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["images"][0]["url"]


def gen_one(key, item, seed, out_dir):
    prompt = build_prompt(item["scene"])
    rid = fal_submit(key, prompt, seed)
    url = fal_wait(key, rid)
    dest = out_dir / f"{item['slug']}.png"
    urllib.request.urlretrieve(url, dest)
    return item["slug"]


def make_card(item, out_dir):
    """Composite a chapter title card locally for crisp text over a warm textured bg."""
    img = Image.new("RGB", (W, H), (74, 52, 38))
    d = ImageDraw.Draw(img)
    # gentle hand-drawn hatch texture
    for x in range(0, W, 14):
        d.line([(x, 0), (x - 40, H)], fill=(84, 60, 44), width=1)
    d.rectangle([50, 50, W - 50, H - 50], outline=(150, 120, 95), width=4)

    def font(sz):
        for p in ["/System/Library/Fonts/Supplemental/Chalkboard.ttc",
                  "/System/Library/Fonts/Supplemental/MarkerFelt.ttc",
                  "/System/Library/Fonts/Supplemental/Arial Bold.ttf"]:
            if os.path.exists(p):
                return ImageFont.truetype(p, sz)
        return ImageFont.load_default()

    def centered(text, f, y, fill):
        b = d.textbbox((0, 0), text, font=f)
        d.text(((W - (b[2] - b[0])) / 2, y), text, font=f, fill=fill)

    centered(item["line1"], font(60), 200, (235, 225, 210))
    centered(item["line2"], font(96), 275, (255, 255, 255))
    img.save(out_dir / f"{item['slug']}.png")
    return item["slug"]


def contact_sheet(items, out_dir, path, cols=6):
    thumbs = [i["slug"] for i in items]
    tw, th = 300, 169
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * (th + 22)), (245, 245, 245))
    d = ImageDraw.Draw(sheet)
    try:
        f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 14)
    except Exception:
        f = ImageFont.load_default()
    for k, slug in enumerate(thumbs):
        p = out_dir / f"{slug}.png"
        if not p.exists():
            continue
        im = Image.open(p).resize((tw, th))
        x, y = (k % cols) * tw, (k // cols) * (th + 22)
        sheet.paste(im, (x, y))
        d.text((x + 4, y + th + 3), slug, font=f, fill=(20, 20, 20))
    sheet.save(path)


def main():
    ep_dir = Path(sys.argv[1]).expanduser().resolve()
    root = Path(__file__).parent.parent
    key = None
    for line in (root / ".env").read_text().splitlines():
        if line.startswith("FAL_KEY="):
            key = line.split("=", 1)[1].strip()
    assert key, "FAL_KEY not found in .env"

    items = parse_prompts((ep_dir / "02_IMAGE_PROMPTS.md").read_text())
    out_dir = ep_dir / "assets" / "frames"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"{len(items)} beats → {out_dir}")

    content = [i for i in items if i["kind"] == "img"]
    cards = [i for i in items if i["kind"] == "card"]

    # cards locally (instant, crisp text)
    for c in cards:
        make_card(c, out_dir)
    print(f"cards composited: {len(cards)}")

    # content frames concurrently
    done, failed = 0, []
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(gen_one, key, it, 2000 + idx * 13, out_dir): it
                for idx, it in enumerate(content)}
        for fut in cf.as_completed(futs):
            it = futs[fut]
            try:
                fut.result()
                done += 1
                print(f"  [{done}/{len(content)}] {it['slug']} ✓")
            except Exception as e:
                failed.append(it["slug"])
                print(f"  !! {it['slug']} failed: {e}")

    sheet = ep_dir / "assets" / "CONTACT_SHEET.png"
    contact_sheet(items, out_dir, sheet)
    print(f"\ndone: {done}/{len(content)} content + {len(cards)} cards")
    if failed:
        print("FAILED:", failed)
    print("contact sheet:", sheet)


if __name__ == "__main__":
    main()
