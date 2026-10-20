"""Build the soundtrack from audio/timeline.json (exact start time of every clip) and put it on the video.
Usage: ../../.venv/bin/python mux.py <silent-or-any video.mp4> <out.mp4>"""
import json, subprocess, sys, pathlib
import numpy as np, soundfile as sf
HERE = pathlib.Path(__file__).resolve().parent
R = 48000
tl = json.load(open(HERE / "audio" / "timeline.json"))
out = np.zeros(int((tl["total"] + 1) * R), dtype=np.float32)
for t, path, gain in tl["sounds"]:
    a, r = sf.read(path, dtype="float32", always_2d=True)
    a = a.mean(axis=1)
    if r != R:                                    # simple linear resample (narration 24k, sfx 44.1k)
        x = np.linspace(0, len(a) - 1, int(len(a) * R / r))
        a = np.interp(x, np.arange(len(a)), a).astype(np.float32)
    a *= 10 ** (gain / 20)
    i = int(t * R); out[i:i + len(a)] += a[: max(0, len(out) - i)]
peak = np.max(np.abs(out))
if peak > 0.98:
    out *= 0.98 / peak
wav = HERE / "audio" / "_soundtrack.wav"
sf.write(wav, out, R)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", sys.argv[1], "-i", str(wav), "-map", "0:v", "-map", "1:a",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", sys.argv[2]], check=True)
wav.unlink()
print("muxed", sys.argv[2], f"{len(tl['sounds'])} sounds, {tl['total']:.1f}s")
