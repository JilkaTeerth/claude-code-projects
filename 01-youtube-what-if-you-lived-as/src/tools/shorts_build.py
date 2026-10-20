#!/usr/bin/env python3
"""Generate a YouTube Short's vertical (9:16) images from beats.json + write VO-TTS.
Usage: shorts_build.py <short-folder>
Each beat's image is a HAND-AUTHORED scene (no slop). fal Flux schnell, vertical."""
import concurrent.futures as cf, json, os, sys, time, urllib.request
sys.path.insert(0, "tools")
import batch_images as B

STYLE = ("Charming warm hand-drawn doodle, storybook felt-tip marker style. Bold clean black outlines, "
 "flat solid fill colours, soft gentle shading, expressive and clear. A real drawn SCENE with things "
 "actually happening (action, objects, a moment) — never a single animal floating on a plain empty "
 "background. Composed VERTICALLY for a tall phone screen, key action centred and large; the scene FILLS "
 "the entire tall frame edge to edge with NO black bars, NO letterbox, NO borders. Warm, a little tender. ")
# Nano Banana Pro — richer painted storybook look ("better graphics")
STYLE_NANO = ("Warm, emotive children's-storybook illustration, hand-painted look with soft texture and gentle "
 "cinematic lighting, expressive and characterful, NOT photorealistic. A rich drawn SCENE with real action, "
 "depth and atmosphere, filling the whole tall 9:16 frame edge to edge, no borders. ")
AVOID = " Not photorealistic, not 3D, not a stock photo, not an empty background."
NOTEXT = " No readable text, letters, numbers or words in the image; show meaning through the drawing only."

def prompt_for(anchor, img, model="nano"):
    style = STYLE_NANO if model == "nano" else STYLE
    return f"{style}Vertical 9:16 scene: {img}. (Keep the animal consistent: {anchor}.){AVOID}{NOTEXT}"

def gen_one(key, slug, prompt, seed, out):  # flux schnell
    body = json.dumps({"prompt": prompt, "image_size": "portrait_16_9",
                       "num_inference_steps": 4, "seed": seed,
                       "enable_safety_checker": False}).encode()
    req = urllib.request.Request("https://queue.fal.run/fal-ai/flux/schnell", data=body,
                                 headers={"Authorization": f"Key {key}", "Content-Type": "application/json"})
    rid = json.loads(urllib.request.urlopen(req, timeout=60).read())["request_id"]
    url = B.fal_wait(key, rid)
    urllib.request.urlretrieve(url, f"{out}/{slug}.png")
    return slug

def _nb_wait(key, rid, tries=60):
    base = f"https://queue.fal.run/fal-ai/nano-banana-pro/requests/{rid}"
    for _ in range(tries):
        req = urllib.request.Request(f"{base}/status", headers={"Authorization": f"Key {key}"})
        if json.loads(urllib.request.urlopen(req, timeout=60).read()).get("status") == "COMPLETED": break
        time.sleep(3)
    req = urllib.request.Request(base, headers={"Authorization": f"Key {key}"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())["images"][0]["url"]

def gen_one_nano(key, slug, prompt, seed, out):  # nano banana pro
    body = json.dumps({"prompt": prompt, "aspect_ratio": "9:16", "num_images": 1}).encode()
    req = urllib.request.Request("https://queue.fal.run/fal-ai/nano-banana-pro", data=body,
                                 headers={"Authorization": f"Key {key}", "Content-Type": "application/json"})
    rid = json.loads(urllib.request.urlopen(req, timeout=60).read())["request_id"]
    url = _nb_wait(key, rid)
    urllib.request.urlretrieve(url, f"{out}/{slug}.png")
    return slug

def main():
    sd = sys.argv[1].rstrip("/")
    model = sys.argv[2] if len(sys.argv) > 2 else "nano"   # "nano" (Nano Banana Pro) or "flux"
    data = json.load(open(f"{sd}/beats.json"))
    anchor = data["anchor"]; beats = data["beats"]
    out = f"{sd}/assets/frames"; os.makedirs(out, exist_ok=True)
    key = next(l.split("=",1)[1].strip() for l in open(".env").read().splitlines() if l.startswith("FAL_KEY="))

    open(f"{sd}/VO-TTS.txt","w").write("\n".join(b["vo"] for b in beats)+"\n")
    records = [(f"img_{i+1:02d}", b["vo"], b["img"]) for i,b in enumerate(beats)]
    json.dump(records, open(f"{sd}/assets/records.json","w"))

    gen = gen_one_nano if model == "nano" else gen_one
    workers = 4 if model == "nano" else 8
    todo = [(f"img_{i+1:02d}", prompt_for(anchor, b["img"], model))
            for i,b in enumerate(beats) if not os.path.exists(f"{out}/img_{i+1:02d}.png")]
    print(f"{len(beats)} beats | model={model} | generating {len(todo)} vertical images")
    done, failed = 0, []
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(gen, key, s, p, 6000+i*17, out): s for i,(s,p) in enumerate(todo)}
        for fut in cf.as_completed(futs):
            try: fut.result(); done += 1; print(f"  [{done}/{len(todo)}] ok")
            except Exception as e: failed.append(futs[fut]); print("  !!",futs[fut],e)
    print(f"done {done}/{len(todo)} | failed {failed}")

if __name__ == "__main__":
    main()
