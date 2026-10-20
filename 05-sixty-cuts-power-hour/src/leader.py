#!/usr/bin/env python3
"""Render the 20 second academy countdown leader that opens every round.

This is the thing that makes the format work: while the leader is on screen the
scene's audio is already running, so the only thing you have to go on is sound.
The picture is underneath the whole time, it just is not shown yet.

Shape of the 20 seconds, matched off the reference cut:

    0.0  to  0.5   black
    0.5  to  2.6   HEAD, badly out of focus
    2.6  to  4.2   just the lamp, still soft
    4.2  to 10.0   sweep hand starts, focus slowly pulls in
   10.0  to 20.0   numbers 10 down to 1, one per second, sharp

Writes leader.mp4 (1280x720, 30fps, silent). Rendered once, reused by all 60
rounds. The per round number in the corner is a separate overlay so this file
never has to be rebuilt.

ffmpeg here is built without drawtext (no freetype), so every glyph is baked in
PIL and composited as pixels.

Every constant below is measured off real frame grabs of the reference video,
not eyeballed. See SPEC.md, section "Leader", for the numbers this file is
trying to hit and how each one was measured.
"""
import math
import os
import shutil
import subprocess
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

W, H = 1280, 720
FPS = 30
DUR = 20.0
CX, CY = W // 2, H // 2

S = "/System/Library/Fonts/Supplemental/"
NUM_FONT = S + "Arial Narrow.ttf"  # the reference numerals are condensed, plain Arial is too wide
HEAD_FONT = S + "Arial Bold.ttf"
MARK_FONT = S + "Arial Bold.ttf"

FRAMES = "leader_frames"
OUT = "leader.mp4"

# phase boundaries, seconds
T_BLACK, T_HEAD, T_SOFT, T_NUMS = 0.5, 2.6, 4.2, 10.0

# the lamp core, tuned so luma>200 spans x 312..963 and y 88..685 (measured),
# falling to near zero by the corners. one big soft ellipse does the job, the
# rest of the falloff comes from the blur, not from stacking more shapes.
LAMP_RX, LAMP_RY, LAMP_DY, LAMP_BLUR = 374, 337, 21, 50

# rings sit only a few luma above whatever the lamp gradient reads at that
# radius, so their color is computed from the lamp itself, not a fixed value.
RING_RADII = (225, 250, 300, 320)
RING_ASPECT = LAMP_RY / LAMP_RX
RING_WIDTH = 3
RING_LIFT = 10  # luma added on top of the local background at each ring

# digit box target, measured on the "4": x 482..768 (286 wide), y 149..569
# (420 tall), centred on frame. arial narrow is close but not exact, so after
# sizing for height we stretch the glyph to close the rest of the gap. see
# fit_numeral_metrics() below, nothing here is a guessed constant.
DIGIT_TARGET_W, DIGIT_TARGET_H = 286, 420


def tight_glyph(ch, font):
    """Render one character and crop to its actual ink, not its advance box.

    A tabular face like Arial Narrow gives every digit the same advance
    width, so textbbox width does not track what is actually drawn. Rendering
    onto a padded canvas and cropping with Image.getbbox() measures the same
    thing a video frame measurement would: real ink pixels, nothing assumed.
    """
    probe = ImageDraw.Draw(Image.new("L", (10, 10)))
    l, t, r, b = probe.textbbox((0, 0), ch, font=font)
    pad = 20
    canvas = Image.new("L", (r - l + 2 * pad, b - t + 2 * pad), 0)
    ImageDraw.Draw(canvas).text((pad - l, pad - t), ch, font=font, fill=255)
    bbox = canvas.getbbox()
    return canvas.crop(bbox) if bbox else None


def fit_numeral_metrics():
    """Binary search the arial narrow size that gives digit '4' a 420 tall box.

    Sized with ImageDraw.textbbox, per spec, since its height tracks the ink
    closely even though its width does not (see tight_glyph). Once the size
    is found we measure the true ink box on "4" and return the horizontal and
    vertical scale that stretches it onto the 286x420 target exactly, the
    same correction then applied uniformly to every digit.
    """
    probe = ImageDraw.Draw(Image.new("L", (10, 10)))
    lo, hi = 50, 900
    size = None
    while lo <= hi:
        mid = (lo + hi) // 2
        f = ImageFont.truetype(NUM_FONT, mid)
        l, t, r, b = probe.textbbox((0, 0), "4", font=f)
        h = b - t
        if abs(h - DIGIT_TARGET_H) <= 6:
            size = mid
            break
        if h < DIGIT_TARGET_H:
            lo = mid + 1
        else:
            hi = mid - 1
    if size is None:
        size = lo
    f = ImageFont.truetype(NUM_FONT, size)
    glyph = tight_glyph("4", f)
    hstretch = DIGIT_TARGET_W / glyph.width
    vstretch = DIGIT_TARGET_H / glyph.height
    return size, hstretch, vstretch


def lamp_gray():
    """The out of focus lamp: one soft ellipse, blurred hard. Fixed, cached once."""
    img = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(img)
    cy = CY + LAMP_DY
    d.ellipse([CX - LAMP_RX, cy - LAMP_RY, CX + LAMP_RX, cy + LAMP_RY], fill=255)
    return img.filter(ImageFilter.GaussianBlur(LAMP_BLUR))


def dashdot(d, points_fn, length, fill, width):
    """Draw a dash dot pattern of the given fill/width along a 1D span.

    points_fn(a, b) returns the two endpoints for a segment running from
    offset a to offset b, so the same helper draws both the horizontal and
    vertical crosshair arms.
    """
    period = 74
    dash, gap1, dot, gap2 = 40, 14, 6, 14
    pos = 0
    while pos < length:
        d.line(points_fn(pos, min(pos + dash, length)), fill=fill, width=width)
        pos += dash + gap1
        if pos < length:
            d.line(points_fn(pos, min(pos + dot, length)), fill=fill, width=width)
        pos += dot + gap2


def base(extra_blur):
    """The lamp plus rings, crosshair and gauge marks, optionally defocused more.

    extra_blur is the phase level of softness on top of the lamp's own blur:
    heavy during HEAD, easing off through the sweep, almost nothing once the
    numerals are sharp. Cached per blur level so 600 frames render fast.
    """
    gray = lamp_gray()

    # rings are only ever a few luma above whatever is already there, all the
    # way around the ellipse. a flat outline colour would be wrong for that,
    # since the lamp is brighter at the sides than at top and bottom, so the
    # lift is applied pixel by pixel: local background plus RING_LIFT, only
    # where the ring outline mask is set.
    ring_mask = Image.new("L", (W, H), 0)
    dm = ImageDraw.Draw(ring_mask)
    for r in RING_RADII:
        ry = r * RING_ASPECT
        dm.ellipse([CX - r, CY - ry, CX + r, CY + ry], outline=255, width=RING_WIDTH)
    lifted = ImageChops.add(gray, Image.new("L", (W, H), RING_LIFT))
    img = Image.composite(lifted, gray, ring_mask).convert("RGB")
    d = ImageDraw.Draw(img)

    # crosshair, black, dash dot, full width and full height
    dashdot(d, lambda a, b: [a, CY, b, CY], W, (0, 0, 0), 3)
    dashdot(d, lambda a, b: [CX, a, CX, b], H, (0, 0, 0), 3)

    # the 35mm gauge marks either side, as on a real leader
    mf = ImageFont.truetype(MARK_FONT, 62)
    for x in (90, W - 90):
        t = "35"
        d.text((x - d.textlength(t, font=mf) / 2, CY - 34), t, font=mf, fill=(70, 70, 70))

    if extra_blur > 0.05:
        img = img.filter(ImageFilter.GaussianBlur(extra_blur))
    return img


def sweep(img, ang):
    """The rotating hand, black, running from the centre out past every edge."""
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    box = [CX - 340, CY - 300, CX + 340, CY + 300]
    d.pieslice(box, -90, ang - 90, fill=(0, 0, 0, 40))
    r = math.radians(ang - 90)
    # 850px reaches past the frame in every direction, corners included
    reach = 850
    d.line([CX, CY, CX + reach * math.cos(r), CY + reach * math.sin(r)], fill=(0, 0, 0, 255), width=3)
    d.ellipse([CX - 7, CY - 7, CX + 7, CY + 7], fill=(0, 0, 0, 255))
    return Image.alpha_composite(img.convert("RGBA"), lay).convert("RGB")


def centred(img, text, font, dy=0, fill=(8, 8, 8)):
    d = ImageDraw.Draw(img)
    l, t, r, b = d.textbbox((0, 0), text, font=font)
    d.text((CX - (r + l) / 2, CY - (b + t) / 2 + dy), text, font=font, fill=fill)
    return img


def paste_numeral(img, ch, font, hstretch, vstretch):
    """Draw one digit, stretched to the calibrated box, centred on the frame."""
    glyph = tight_glyph(ch, font)
    if glyph is None:
        return img
    neww = max(1, round(glyph.width * hstretch))
    newh = max(1, round(glyph.height * vstretch))
    glyph = glyph.resize((neww, newh), Image.LANCZOS)
    solid = Image.new("RGB", glyph.size, (0, 0, 0))
    img.paste(solid, (CX - neww // 2, CY - newh // 2), glyph)
    return img


def main():
    if os.path.exists(FRAMES):
        shutil.rmtree(FRAMES)
    os.makedirs(FRAMES)

    cache = {}

    def bg(blur):
        k = round(blur * 2) / 2
        if k not in cache:
            cache[k] = base(k)
        return cache[k]

    num_size, hstretch, vstretch = fit_numeral_metrics()
    print(f"numeral font size {num_size}, stretch x{hstretch:.4f} y{vstretch:.4f}")
    num_font = ImageFont.truetype(NUM_FONT, num_size)

    head = ImageFont.truetype(HEAD_FONT, 210)
    total = int(DUR * FPS)

    for i in range(total):
        t = i / FPS

        if t < T_BLACK:
            img = Image.new("RGB", (W, H), (0, 0, 0))

        elif t < T_HEAD:
            img = bg(14).copy()
            img = centred(img, "HEAD", head)

        elif t < T_SOFT:
            img = bg(12).copy()

        elif t < T_NUMS:
            # focus pulls from soft to nearly sharp while the hand spins up
            k = (t - T_SOFT) / (T_NUMS - T_SOFT)
            img = sweep(bg(12 - 10.4 * k), (t * 360) % 360)

        else:
            n = 10 - int(t - T_NUMS)
            n = max(n, 1)
            img = bg(0.8).copy()
            img = paste_numeral(img, str(n), num_font, hstretch, vstretch)
            frac = (t - T_NUMS) % 1.0
            img = sweep(img, frac * 360)

        img.save(f"{FRAMES}/{i:05d}.png")
        if i % 60 == 0:
            print(f"  leader {t:5.1f}s / {DUR:.0f}s", flush=True)

    print("encoding leader.mp4")
    subprocess.run(
        ["ffmpeg", "-nostdin", "-y", "-v", "error",
         "-framerate", str(FPS), "-i", f"{FRAMES}/%05d.png",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
         "-pix_fmt", "yuv420p", "-r", str(FPS), OUT],
        check=True)
    shutil.rmtree(FRAMES)
    print(f"wrote {OUT}  ({DUR:.0f}s)")


if __name__ == "__main__":
    sys.exit(main())
