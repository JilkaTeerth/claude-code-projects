#!/usr/bin/env python3
"""Assemble one megafilm episode into an MP4 with ffmpeg.
Reads: <ep>/assets/records.json (ordered slugs), <ep>/assets/segments.json (VO transcript),
       <ep>/VO-TTS.txt (53 beat texts), the VO mp3 and music mp3.
Word-syncs each frame to the VO, builds a concat slideshow, mixes VO + looped music @0.13, exports 1080p.
Usage: assemble_ep.py <episode-folder> <vo.mp3> <music.mp3> <out.mp4>
"""
import json, re, subprocess, sys, os

FFMPEG = "/opt/homebrew/bin/ffmpeg"
FFPROBE = "/opt/homebrew/bin/ffprobe"
FPS = 30

def dur(path):
    return float(subprocess.check_output([FFPROBE,"-v","error","-show_entries","format=duration","-of","csv=p=0",path]).strip())

def words(t): return re.findall(r"[A-Za-z0-9']+", t)

def main():
    ep, vo, music, out = sys.argv[1].rstrip("/"), sys.argv[2], sys.argv[3], sys.argv[4]
    records = json.load(open(f"{ep}/assets/records.json"))
    segs = json.load(open(f"{ep}/assets/segments.json"))
    beats = [l for l in open(f"{ep}/VO-TTS.txt").read().splitlines() if l.strip()]
    vo_len = dur(vo)
    assert len(records) == len(beats), f"records {len(records)} != beats {len(beats)}"

    # global word->time by interpolating within each transcript segment
    gwords = []
    for text, s, e in segs:
        ws = words(text); n = max(len(ws),1)
        for i,_ in enumerate(ws):
            gwords.append(s + (e-s)*(i/n))

    # each beat's start = time of its first word (walk pointer by beat word counts)
    starts, cur = [], 0
    for b in beats:
        starts.append(gwords[cur] if cur < len(gwords) else vo_len)
        cur += len(words(b))

    # frame durations: beat i runs to beat i+1 start; last to vo end
    N = len(records)
    durs = []
    for i in range(N):
        st = starts[i]; en = starts[i+1] if i+1 < len(starts) else vo_len
        durs.append(max(en-st, 1/FPS))

    # concat FILTER (reliable timing): each image looped for its exact duration
    ins = []
    for i,(slug,_,_) in enumerate(records):
        ins += ["-loop","1","-t",f"{durs[i]:.3f}","-i",os.path.abspath(f"{ep}/assets/frames/{slug}.png")]
    ins += ["-i",vo,"-stream_loop","-1","-i",music]
    vo_i, mus_i = N, N+1
    fc = ""
    for i in range(N):
        fc += (f"[{i}:v]scale=1920:1080:force_original_aspect_ratio=decrease,"
               f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=white,setsar=1,fps=30[v{i}];")
    fc += "".join(f"[v{i}]" for i in range(N)) + f"concat=n={N}:v=1:a=0[v];"
    fc += f"[{mus_i}:a]volume=0.13[m];[{vo_i}:a][m]amix=inputs=2:duration=first:dropout_transition=0[a]"
    cmd = [FFMPEG,"-y"] + ins + ["-filter_complex",fc,
        "-map","[v]","-map","[a]",
        "-c:v","libx264","-preset","medium","-crf","20","-pix_fmt","yuv420p",
        "-c:a","aac","-b:a","192k","-shortest",out]
    print(f"beats {len(beats)} | vo {vo_len:.1f}s | last beat start {starts[-1]:.1f}s | N={N}")
    subprocess.run(cmd, check=True,
                   stdout=subprocess.DEVNULL, stderr=open(f"{ep}/assets/ffmpeg.log","w"))
    print("wrote", out, f"({dur(out):.1f}s)")

if __name__ == "__main__":
    main()
