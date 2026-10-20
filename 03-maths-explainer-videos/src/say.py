"""say: text to speech on this laptop, no API, no limits.

  .venv/bin/python say.py "Hello there." --voice bm_george --out out/hello.wav
  .venv/bin/python say.py --file script.txt --voice af_heart --speed 0.95

Model: Kokoro-82M (Apache 2.0). Its weights download once into ./models, so everything this
project touches stays inside this folder. Delete the folder and it's all gone.
"""
import argparse, os, pathlib, re

HERE = pathlib.Path(__file__).resolve().parent
os.environ.setdefault("HF_HOME", str(HERE / "models"))          # keep the model in this folder
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

import numpy as np, soundfile as sf
from kokoro import KPipeline

RATE = 24000
# a = American, b = British; f / m = voice. Full list: huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md
VOICES = {"af_heart", "af_bella", "af_nicole", "am_michael", "am_fenrir", "am_puck",
          "bf_emma", "bf_isabella", "bm_george", "bm_fable", "bm_lewis"}

# Pacing marks a script can use: [pause] is a real breath, [beat] is a comic half-second.
MARKS = {"[pause]": 0.7, "[beat]": 0.35, "[long]": 1.2}
_PIPES = {}

def speak(text, voice="af_heart", speed=1.0):
    pipe = _PIPES.get(voice[0]) or _PIPES.setdefault(voice[0], KPipeline(lang_code=voice[0], repo_id="hexgrad/Kokoro-82M"))
    silence = lambda sec: np.zeros(int(RATE * sec), dtype=np.float32)
    parts = []
    for para in [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]:
        for chunk in re.split(r"(\[pause\]|\[beat\]|\[long\])", para):
            chunk = chunk.strip()
            if not chunk:
                continue
            if chunk in MARKS:
                parts.append(silence(MARKS[chunk])); continue
            for _, _, audio in pipe(chunk, voice=voice, speed=speed):
                parts.append(np.asarray(audio, dtype=np.float32))
        parts.append(silence(0.35))
    return np.concatenate(parts) if parts else np.zeros(1, dtype=np.float32)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("text", nargs="?")
    ap.add_argument("--file")
    ap.add_argument("--voice", default="af_heart", choices=sorted(VOICES))
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--out", default=str(HERE / "out" / "say.wav"))
    a = ap.parse_args()
    text = open(a.file).read() if a.file else a.text
    audio = speak(text, a.voice, a.speed)
    sf.write(a.out, audio, RATE)
    print(f"{a.out}  {len(audio) / RATE:.1f}s  voice={a.voice}")
