#!/usr/bin/env python3
"""Render the academy countdown leader, matched to the reference measurements.

Every constant in here was measured off 1280x720 frames of the source video
rather than guessed. See SPEC.md for where each number came from. The short
version:

    lamp        luma > 200 spans x 312..963 and y 88..685, black at the corners
    rings       only about 5 luma above their local background
    crosshair   black, 3px, dash-dot, full width and full height
    sweep       black, 3px, centre to past the frame edge, one turn a second
    numerals    ink box 286 x 420, so a condensed face, not Arial

Output is leader.mov: ProRes 4444 with a real alpha channel, the last 0.55s
fading to transparent. Baking the dissolve into the asset means the editor can
just lay it on top of the scene with no opacity keyframes at all.

ffmpeg here has no drawtext filter, so every glyph is baked in PIL.
"""
import math
import os
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1280, 720
CX, CY = 640, 360
FPS = 30
DUR = 20.0
FADE = 0.55                      # alpha dissolve at the tail

S = "/System/Library/Fonts/Supplemental/"
NUM_FONT = S + "Arial.ttf"
HEAD_FONT = S + "Arial Bold.ttf"

# Lamp falloff: luma = 255 * exp(-K * r**N) over the normalized elliptical
# radius r. A, B, N and K are a least squares fit to six luma samples taken off
# the reference on rows and columns that miss the crosshair and the numeral:
#   row y=340   luma 200 at x = 207 and 1069, 179 at x=180, 232 at x=300
#   col x=980   luma 200 at y = 200 and 521,  73 at y=90
# Solving those gives N = 6.64 and B = 0.606*A, and setting r=1 on the row
# half width fixes A = 431 and K = ln(255/200). The lamp is far wider than it
# is tall, which is the thing the first attempt got wrong.
LAMP_A, LAMP_B = 431.0, 261.0
LAMP_N = 6.64
LAMP_K = -math.log(200 / 255)

NUM_W, NUM_H = 286, 420          # measured ink box of the reference "4"
RINGS = (225, 250, 300, 320)
RING_LIFT = 7                    # measured about 5 luma above background

T_BLACK, T_HEAD, T_SOFT, T_NUMS = 0.5, 2.6, 4.2, 10.0
FRAMES, OUT = "leader_ref_frames", "leader.mov"   # own dir, never shared


def lamp():
    """The out of focus lamp, as an analytic falloff rather than a blurred blob."""
    y, x = np.mgrid[0:H, 0:W]
    r = np.sqrt(((x - CX) / LAMP_A) ** 2 + ((y - CY) / LAMP_B) ** 2)
    a = 255.0 * np.exp(-LAMP_K * r ** LAMP_N)

    # rings sit just barely above the lamp, a few luma, not bright white
    for R in RINGS:
        d = np.sqrt(((x - CX) / R) ** 2 + ((y - CY) / (R * 0.92)) ** 2)
        a += RING_LIFT * np.exp(-((d - 1.0) * 260) ** 2)

    return np.clip(a, 0, 255).astype(np.uint8)


def chrome(img):
    """Black dash-dot crosshair, full width and full height."""
    d = ImageDraw.Draw(img)
    for x in range(0, W, 34):
        d.line([x, CY, x + 22, CY], fill=0, width=3)
    for y in range(0, H, 34):
        d.line([CX, y, CX, y + 22], fill=0, width=3)
    return img


def sweep(img, ang):
    """The hand, black, running from the centre out past the frame edge."""
    d = ImageDraw.Draw(img)
    r = math.radians(ang - 90)
    d.line([CX, CY, CX + 1500 * math.cos(r), CY + 1500 * math.sin(r)], fill=0, width=3)
    d.ellipse([CX - 6, CY - 6, CX + 6, CY + 6], fill=0)
    return img


def digit_mask(text):
    """A numeral whose ink box is exactly NUM_W x NUM_H, returned as a mask.

    No font on this machine has the reference's proportions: Arial is too wide
    (aspect 0.78), Arial Narrow too condensed (0.53), and the reference sits at
    0.68 between them. So render big, crop to the ink, and resample to the
    measured box. That hits the target exactly whatever the face does.
    """
    f = ImageFont.truetype(NUM_FONT, 700)
    tmp = Image.new("L", (1600, 1400), 0)
    ImageDraw.Draw(tmp).text((200, 150), text, font=f, fill=255)
    return tmp.crop(tmp.getbbox()).resize((NUM_W, NUM_H), Image.LANCZOS)


def stamp(img, text, font, fill=0):
    """Draw text so its INK box is centred on the frame, not its layout box."""
    d = ImageDraw.Draw(img)
    bb = d.textbbox((0, 0), text, font=font)
    d.text((CX - (bb[0] + bb[2]) / 2, CY - (bb[1] + bb[3]) / 2 - 1),
           text, font=font, fill=fill)
    return img


def main():
    if os.path.exists(FRAMES):
        shutil.rmtree(FRAMES)
    os.makedirs(FRAMES)

    base = lamp()
    soft = {}

    def ground(blur):
        """The lamp at a given defocus, cached per half step."""
        k = round(blur * 2) / 2
        if k not in soft:
            im = Image.fromarray(base, "L")
            soft[k] = im.filter(ImageFilter.GaussianBlur(k)) if k > 0.05 else im
        return soft[k].copy()

    digits = {n: digit_mask(str(n)) for n in range(1, 11)}
    DX, DY = CX - NUM_W // 2, 359 - NUM_H // 2
    print(f"numerals rendered at exactly {NUM_W} x {NUM_H}")

    head = ImageFont.truetype(HEAD_FONT, 210)
    total = int(DUR * FPS)

    for i in range(total):
        t = i / FPS
        if t < T_BLACK:
            img = Image.new("L", (W, H), 0)
        elif t < T_HEAD:
            img = stamp(chrome(ground(14)), "HEAD", head)
        elif t < T_SOFT:
            img = chrome(ground(12))
        elif t < T_NUMS:
            k = (t - T_SOFT) / (T_NUMS - T_SOFT)
            img = sweep(chrome(ground(12 - 11.2 * k)), (t * 360) % 360)
        else:
            n = max(1, 10 - int(t - T_NUMS))
            frac = (t - T_NUMS) % 1.0
            img = chrome(ground(0.8))
            img.paste(0, (DX, DY), digits[n])
            img = sweep(img, frac * 360)

        # alpha: opaque until the tail, then dissolve so the scene underneath
        # is revealed without the editor needing a single keyframe
        a = 255
        if t > DUR - FADE:
            a = int(255 * max(0.0, (DUR - t) / FADE))
        rgba = Image.merge("RGBA", (img, img, img,
                                    Image.new("L", (W, H), a)))
        rgba.save(f"{FRAMES}/{i:05d}.png")
        if i % 120 == 0:
            print(f"  {t:5.1f}s / {DUR:.0f}s", flush=True)

    print("encoding", OUT)
    subprocess.run(
        ["ffmpeg", "-nostdin", "-y", "-v", "error",
         "-framerate", str(FPS), "-i", f"{FRAMES}/%05d.png",
         "-c:v", "prores_ks", "-profile:v", "4444",
         "-pix_fmt", "yuva444p10le", "-r", str(FPS), OUT],
        check=True)
    shutil.rmtree(FRAMES)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    sys.exit(main())
