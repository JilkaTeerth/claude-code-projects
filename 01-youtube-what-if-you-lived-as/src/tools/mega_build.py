#!/usr/bin/env python3
"""Reusable megafilm episode builder: script -> image prompts -> fal frames + chapter cards.
Usage: mega_build.py <episode-folder> <anchor-key>
Anchors live in ANCHORS below (one per animal). Channel charming-doodle style.
VO / sync / assembly are separate steps (per episode, after frames)."""
import concurrent.futures as cf, json, os, re, sys, urllib.request
sys.path.insert(0, "tools")
import batch_images as B
from PIL import Image, ImageDraw, ImageFont

STYLE = ("Charming childlike hand-drawn doodle, warm storybook felt-tip marker style. Bold clean black outlines, "
 "flat solid fill colours, soft gentle shading, warm and a little tender. Simple hand-drawn scene of the "
 "animal's REAL habitat with gentle texture. Uncluttered, one clear subject, generous space. ")
AVOID = " Not photorealistic, not 3D, not a stock-photo look; hand-drawn and specific to this exact animal."
NOTEXT = " No text, letters, numbers or words anywhere in the image."

# Per-animal look anchors (real look + real habitat). Add one line per new episode.
ANCHORS = {
 "vaquita": "the subject is a small round grey vaquita porpoise with dark rings around its eyes and dark lips, in the warm murky green shallows of the northern Gulf of California",
 "hawksbill": "the subject is a hawksbill sea turtle with an amber, bronze and black patterned overlapping shell and a narrow pointed hawk-like beak and four flippers (as a hatchling, a tiny dark turtle the size of a bottle cap); habitats: a moonlit tropical nesting beach, the open blue sea with floating golden seaweed, and a colourful coral reef",
}

ABSTRACT = ["you did nothing to earn this","depends entirely on us","that, too, will matter",
            "it never did","rarest animal in the sea","strange, quiet miracle","never once been hunted",
            "up to us","you will never see","you will never meet","ask for so little","ask for nothing",
            "oldest, safest story","only thing that is","a bet placed","that is the whole point",
            "the question now is only"]

def scene_for(anchor, line):
    l = line.strip()
    if any(c in l.lower() for c in ABSTRACT):
        return f"a tender quiet portrait of {anchor}, looking gently toward the viewer"
    return f"{anchor}; {l}"

def build_prompt(anchor, line):
    return f"{STYLE}{scene_for(anchor, line)}{AVOID}{NOTEXT}"

def parse_script(path):
    """Return ordered items: ('card',(l1,l2)) | ('content', narration)."""
    items = []
    for ln in open(path).read().splitlines():
        m = re.match(r'^\[00:00\]\s*(.+)', ln)
        if not m: continue
        txt = m.group(1)
        card = re.search(r'"([^"]+·[^"]+)"', txt)
        if "← SPOKEN" in txt and card:
            l1, l2 = [s.strip() for s in card.group(1).split("·", 1)]
            items.append(("card", (l1, l2)))
        else:
            clean = re.sub(r'\s*←.*$', '', txt).replace("(hold on black) ", "").strip()
            items.append(("content", clean))
    return items

def gen_one(key, slug, prompt, seed, out):
    rid = B.fal_submit(key, prompt, seed)
    url = B.fal_wait(key, rid)
    urllib.request.urlretrieve(url, f"{out}/{slug}.png")
    return slug

def main():
    ep = sys.argv[1].rstrip("/")
    akey = sys.argv[2]
    anchor = ANCHORS[akey]
    out = f"{ep}/assets/frames"
    os.makedirs(out, exist_ok=True)
    key = next(l.split("=",1)[1].strip() for l in open(".env").read().splitlines() if l.startswith("FAL_KEY="))

    items = parse_script(f"{ep}/01_SCRIPT.md")
    # write prompt doc + records
    md = [f"# {ep.split('/')[-1]} — Image Prompts (channel doodle style, anchor={akey})",
          f"**Style:** `{STYLE}`", f"**Anchor:** {anchor}", "", "---"]
    records = []
    ci = ka = 0
    for kind, payload in items:
        if kind == "card":
            ka += 1
            md.append(f'- **CARD_{ka}** — chapter card: "{payload[0]} · {payload[1]}"')
            records.append((f"CARD_{ka}", "card", payload))
        else:
            ci += 1
            md.append(f"- **img_{ci:03d}** — {scene_for(anchor, payload)}.")
            records.append((f"img_{ci:03d}", "content", payload))
    open(f"{ep}/02_IMAGE_PROMPTS.md","w").write("\n".join(md)+"\n")
    json.dump(records, open(f"{ep}/assets/records.json","w"))
    content = [r for r in records if r[1]=="content"]
    cards = [r for r in records if r[1]=="card"]
    print(f"{ep}: {len(content)} content + {len(cards)} cards")

    for slug,_,(l1,l2) in cards:
        B.make_card_generic(l1, l2, f"{out}/{slug}.png") if hasattr(B,"make_card_generic") else _card(l1,l2,f"{out}/{slug}.png")
    print(f"cards: {len(cards)}")

    todo = [(s,payload) for s,_,payload in content if not os.path.exists(f"{out}/{s}.png")]
    done, failed = 0, []
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(gen_one, key, s, build_prompt(anchor, p), 5000+i*13, out): s for i,(s,p) in enumerate(todo)}
        for fut in cf.as_completed(futs):
            try: fut.result(); done += 1
            except Exception as e: failed.append(futs[fut]); print("  !!",futs[fut],e)
    print(f"content {done}/{len(todo)} | failed {failed}")

def _card(l1, l2, path):
    W,H=1024,576
    img=Image.new("RGB",(W,H),(28,42,54)); d=ImageDraw.Draw(img)
    for x in range(0,W,16): d.line([(x,0),(x-30,H)],fill=(34,50,64),width=1)
    d.rectangle([46,46,W-46,H-46],outline=(150,180,205),width=3)
    def fnt(s):
        for p in ["/System/Library/Fonts/Supplemental/Chalkboard.ttc","/System/Library/Fonts/Supplemental/Arial Bold.ttf"]:
            if os.path.exists(p): return ImageFont.truetype(p,s)
        return ImageFont.load_default()
    def ctr(t,f,y,c):
        b=d.textbbox((0,0),t,font=f); d.text(((W-(b[2]-b[0]))/2,y),t,font=f,fill=c)
    ctr(l1,fnt(52),210,(200,225,240)); ctr(l2,fnt(84),280,(255,255,255))
    img.save(path)

if __name__ == "__main__":
    main()
