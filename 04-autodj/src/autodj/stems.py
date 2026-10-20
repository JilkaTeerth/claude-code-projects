"""Split each song into vocals / drums / bass / other with demucs, and map where the
vocals are, bar by bar, so transitions never put two singers on top of each other.

usage: python -m autodj.stems music/*.mp3
writes stems/<name>/{vocals,drums,bass,other}.flac and adds "vocal_bars" to analysis/<name>.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from demucs.apply import apply_model
from demucs.pretrained import get_model

from .analyze import SR, load

ROOT = Path(__file__).resolve().parent.parent
STEMS = ["drums", "bass", "other", "vocals"]


def separate(model, path, device):
    y = load(path).T.astype(np.float32)  # (2, n)
    wav = torch.from_numpy(y)
    ref = wav.mean(0)
    wav = (wav - ref.mean()) / (ref.std() + 1e-8)
    with torch.no_grad():
        out = apply_model(model, wav[None], device=device, split=True, overlap=0.25, progress=False)[0]
    out = out * (ref.std() + 1e-8) + ref.mean()
    return {name: out[i].cpu().numpy().T for i, name in enumerate(model.sources)}


def vocal_map(vocals, analysis):
    """Per bar vocal loudness relative to the song's own loud vocal parts: 0 = none, 1 = full."""
    mono = vocals.mean(axis=1)
    bar_len = 4 * analysis["beat_period"]
    first = analysis["first_downbeat"]
    levels = []
    for k in range(analysis["n_bars"]):
        a, b = int((first + k * bar_len) * SR), int((first + (k + 1) * bar_len) * SR)
        seg = mono[a:b]
        levels.append(float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0)
    levels = np.array(levels)
    ref = np.percentile(levels, 90) + 1e-9
    return [round(float(min(1.0, v / ref)), 2) for v in levels]


def main(paths):
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    model = get_model("htdemucs")
    model.to(device).eval()
    for p in paths:
        name = Path(p).stem
        out_dir = ROOT / "stems" / name
        if not (out_dir / "vocals.flac").exists():
            stems = separate(model, p, device)
            out_dir.mkdir(parents=True, exist_ok=True)
            for s, audio in stems.items():
                sf.write(out_dir / f"{s}.flac", audio, SR)
        vocals, _ = sf.read(out_dir / "vocals.flac")
        a_path = ROOT / "analysis" / f"{name}.json"
        a = json.loads(a_path.read_text())
        a["vocal_bars"] = vocal_map(vocals, a)
        a_path.write_text(json.dumps(a, indent=1))
        sung = "".join("#" if v > 0.35 else ("." if v > 0.12 else " ") for v in a["vocal_bars"])
        print(f"{name}\n  |{sung}|", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
