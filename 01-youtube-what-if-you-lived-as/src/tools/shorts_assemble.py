#!/usr/bin/env python3
"""Assemble a YouTube Short: vertical 1080x1920, word-synced scenes, VO + music, bold text overlays.
Usage: shorts_assemble.py <short-folder> <vo.mp3> <music.mp3> <out.mp4>"""
import json, re, subprocess, sys, os
from PIL import Image, ImageDraw, ImageFont

FFMPEG="/opt/homebrew/bin/ffmpeg"; FFPROBE="/opt/homebrew/bin/ffprobe"; FPS=30
FONT="/System/Library/Fonts/Supplemental/Impact.ttf"
if not os.path.exists(FONT): FONT="/System/Library/Fonts/Supplemental/Arial Bold.ttf"

def dur(p): return float(subprocess.check_output([FFPROBE,"-v","error","-show_entries","format=duration","-of","csv=p=0",p]).strip())
def words(t): return re.findall(r"[A-Za-z0-9']+", t)

def text_png(path, text, y, size, fill=(255,255,255)):
    """Transparent 1080x1920 overlay with centered stroked text at vertical position y."""
    img=Image.new("RGBA",(1080,1920),(0,0,0,0)); d=ImageDraw.Draw(img)
    f=ImageFont.truetype(FONT,size)
    b=d.textbbox((0,0),text,font=f,stroke_width=max(6,size//10))
    d.text(((1080-(b[2]-b[0]))/2 - b[0], y), text, font=f, fill=fill,
           stroke_width=max(6,size//10), stroke_fill=(0,0,0))
    img.save(path)

def main():
    sd,vo,music,out = sys.argv[1].rstrip("/"),sys.argv[2],sys.argv[3],sys.argv[4]
    data=json.load(open(f"{sd}/beats.json"))
    records=json.load(open(f"{sd}/assets/records.json"))
    segs=json.load(open(f"{sd}/assets/segments.json"))
    beats=[l for l in open(f"{sd}/VO-TTS.txt").read().splitlines() if l.strip()]
    vo_len=dur(vo); N=len(records)
    assert N==len(beats), f"{N} vs {len(beats)}"

    gw=[]
    for text,s,e in segs:
        ws=words(text); n=max(len(ws),1)
        for i,_ in enumerate(ws): gw.append(s+(e-s)*(i/n))
    starts,cur=[],0
    for b in beats:
        starts.append(gw[cur] if cur<len(gw) else vo_len); cur+=len(words(b))
    durs=[(starts[i+1] if i+1<N else vo_len)-starts[i] for i in range(N)]
    durs=[max(d,1/FPS) for d in durs]

    # build text overlay PNGs (PIL) — drawtext isn't in this ffmpeg build
    hook=data.get("hook_text",""); stat=data.get("stat_text","")
    hook_end=starts[2] if N>2 else 3.5
    stat_start=starts[7] if N>7 else vo_len*0.6
    overlays=[]  # (png_path, enable_expr)
    if hook:
        p=os.path.abspath(f"{sd}/assets/ov_hook.png"); text_png(p,hook,230,100,(255,255,255))
        overlays.append((p,f"between(t,0,{hook_end:.2f})"))
    if stat:
        p=os.path.abspath(f"{sd}/assets/ov_stat.png"); text_png(p,stat,1380,150,(255,235,60))
        overlays.append((p,f"gte(t,{stat_start:.2f})"))

    ins=[]
    for i,(slug,_,_) in enumerate(records):
        ins+=["-loop","1","-t",f"{durs[i]:.3f}","-i",os.path.abspath(f"{sd}/assets/frames/{slug}.png")]
    ins+=["-i",vo,"-stream_loop","-1","-i",music]
    vo_i,mus_i=N,N+1
    for p,_ in overlays:
        ins+=["-loop","1","-i",p]

    fc=""
    for i in range(N):
        fc+=f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30[v{i}];"
    fc+="".join(f"[v{i}]" for i in range(N))+f"concat=n={N}:v=1:a=0[vc];"
    cur="vc"
    for k,(p,en) in enumerate(overlays):
        oi=N+2+k
        fc+=f"[{oi}:v]scale=1080:1920,setsar=1[o{k}];[{cur}][o{k}]overlay=0:0:enable='{en}'[ov{k}];"
        cur=f"ov{k}"
    fc+=f"[{cur}]format=yuv420p[v];"
    fc+=f"[{mus_i}:a]volume=0.13[m];[{vo_i}:a][m]amix=inputs=2:duration=first:dropout_transition=0[a]"

    cmd=[FFMPEG,"-y"]+ins+["-filter_complex",fc,"-map","[v]","-map","[a]",
        "-c:v","libx264","-preset","medium","-crf","20","-pix_fmt","yuv420p",
        "-r","30","-c:a","aac","-b:a","192k","-shortest",out]
    print(f"beats {N} | vo {vo_len:.1f}s | last start {starts[-1]:.1f}s | hook<{hook_end:.1f}s stat>{stat_start:.1f}s")
    subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL,stderr=open(f"{sd}/assets/ffmpeg.log","w"))
    print("wrote",out,f"({dur(out):.1f}s, vertical)")

if __name__=="__main__":
    main()
