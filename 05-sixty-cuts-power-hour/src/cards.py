#!/usr/bin/env python3
"""Render every overlay the power hour burns into the picture.

The format is deliberately bare. Once the leader clears there is nothing on
screen except the film, until the name arrives in the bottom left at forty
seconds and the drink call flashes just before the cut. So there are only four
kinds of art here.

  cards/n_NN.png    round number, top left, rides on the leader only
  cards/t_NN.png    the answer, bottom left, from 0:40
  cards/drink.png   the drink call, just before the round cuts
  cards/intro_N.png the how to play card, revealed a line at a time
  cards/outro.png   end card

ffmpeg here is built without drawtext (no freetype), so all text is baked here.
"""
import csv
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

S = "/System/Library/Fonts/Supplemental/"
DISPLAY = S + "Arial Black.ttf"
BOLD = S + "Arial Bold.ttf"
BOOK = S + "Arial.ttf"
SERIF = S + "Times New Roman.ttf"

W, H = 1280, 720
INK = (13, 10, 17)
CREAM = (243, 236, 221)
GOLD = (247, 178, 41)
BLUE = (122, 200, 226)
DIM = (140, 128, 156)

f = lambda p, s: ImageFont.truetype(p, s)
os.makedirs("cards", exist_ok=True)


def track(d, xy, text, font, fill, sp=0.0):
    """Draw text with manual letterspacing. Returns the width drawn."""
    x, y = xy
    x0 = x
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill)
        x += d.textlength(ch, font=font) + sp
    return x - x0 - (sp if text else 0)


def track_width(d, text, font, sp=0.0):
    if not text:
        return 0
    return sum(d.textlength(c, font=font) for c in text) + sp * (len(text) - 1)


def fit(d, text, path, size, maxw, sp=0.0, floor=26):
    while size > floor and track_width(d, text, f(path, size), sp) > maxw:
        size -= 2
    return f(path, size)


def shadowed(draw_fn, blur=14, alpha=205, spread=3):
    """Run a draw function twice: once in black and blurred, once for real.

    Keeps a title readable over a bright frame without laying a heavy scrim
    across the picture, which is what the format does.
    """
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(sh), (0, 0, 0, alpha))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for _ in range(spread):
        out = Image.alpha_composite(out, sh)
    draw_fn(ImageDraw.Draw(out), None)
    return out


# ---------------------------------------------------------------- plate

def plate():
    """Ink ground, film perforation lattice, warm glow. Used by intro and outro."""
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)
    random.Random(7)
    for gy in range(-40, H + 40, 46):
        for gx in range(-40, W + 40, 46):
            x = gx + (23 if (gy // 46) % 2 else 0)
            d.rounded_rectangle([x, gy, x + 13, gy + 9], radius=3, fill=(26, 21, 34))
    glow = Image.new("RGB", (W, H), INK)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([-260, -420, 900, 420], fill=(58, 40, 16))
    gd.ellipse([620, 200, 1700, 1000], fill=(16, 38, 50))
    img = Image.blend(img, glow.filter(ImageFilter.GaussianBlur(150)), 0.55)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 5], fill=GOLD)
    d.rectangle([0, H - 5, W, H], fill=BLUE)
    return img


# ---------------------------------------------------------------- rounds

def round_number(n):
    """Small mark top left, the only chrome on the leader."""
    def go(d, force):
        d.text((26, 14), f"{n}.", font=f(BOLD, 34), fill=force or (255, 255, 255, 255))
    return shadowed(go, blur=8, alpha=190, spread=2)


def answer(row, n, total):
    """The name, bottom left, the way a studio logo sits on the frame."""
    title = row["movie"].upper()
    side = row["side"]
    meta = f"{side}   {row['year']}"

    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    tf = fit(probe, title, DISPLAY, 74, 700, sp=1.5)
    mf = f(BOLD, 21)

    # anchored off the bottom so a long title grows upward, never off frame
    rule_y = 672
    title_y = rule_y - 26 - tf.size
    meta_y = title_y - 34

    def go(d, force):
        track(d, (64, meta_y), meta, mf, force or GOLD + (255,), sp=3.2)
        track(d, (64, title_y), title, tf, force or CREAM + (255,), sp=1.5)
        d.rectangle([64, rule_y, 118, rule_y + 4], fill=force or BLUE + (255,))
        d.text((136, rule_y - 13), f"{n} of {total}", font=f(BOOK, 19),
               fill=force or (255, 255, 255, 130))

    return shadowed(go, blur=16, alpha=185, spread=2)


def drink():
    """The call. Big serif, dead centre, same as the format it is lifted from."""
    fnt = f(SERIF, 132)

    def go(d, force):
        t = "Drink!"
        w = d.textlength(t, font=fnt)
        d.text(((W - w) / 2, H / 2 - 96), t, font=fnt,
               fill=force or (255, 255, 255, 255))

    return shadowed(go, blur=22, alpha=215, spread=3)


# ---------------------------------------------------------------- intro

def intro(total, hindi, english):
    """How to play, revealed a line at a time. Returns a list of frames."""
    rules = [
        ("1", "Drink on every scene change."),
        ("2", "The first 20 seconds is sound only. Name the movie and"
              " you get to make someone else drink."),
        ("3", "The picture comes in at 20 seconds. The name drops into the"
              " bottom left at 40."),
    ]
    frames = []
    for step in range(5):
        img = plate()
        d = ImageDraw.Draw(img)
        track(d, (96, 58), "HOW TO PLAY", f(DISPLAY, 62), CREAM, sp=2.0)
        d.text((100, 134), f"{total} scenes   {hindi} Hindi   {english} English"
                           "   one minute each", font=f(BOLD, 26), fill=GOLD)

        y = 210
        for i, (num, text) in enumerate(rules):
            if i >= step:
                break
            d.ellipse([96, y, 148, y + 52], fill=GOLD)
            nf = f(DISPLAY, 30)
            d.text((122 - d.textlength(num, font=nf) / 2, y + 8), num, font=nf, fill=INK)
            tf = f(BOOK, 28)
            # wrap by hand so the lattice stays quiet behind long rules
            words, line, lines = text.split(), "", []
            for wd in words:
                probe = (line + " " + wd).strip()
                if d.textlength(probe, font=tf) > 980 and line:
                    lines.append(line)
                    line = wd
                else:
                    line = probe
            lines.append(line)
            for j, ln in enumerate(lines):
                d.text((180, y + 6 + j * 34), ln, font=tf, fill=CREAM)
            y += 52 + 34 * len(lines) + 20

        if step >= 4:
            gf = f(DISPLAY, 54)
            t = "GOOD LUCK"
            d.text(((W - d.textlength(t, font=gf)) / 2, 604), t, font=gf, fill=BLUE)
        frames.append(img)
    return frames


def outro(total, hindi, english):
    img = plate()
    d = ImageDraw.Draw(img)
    for t, fnt, y, col in (("THAT IS ALL", f(DISPLAY, 118), 214, CREAM),
                           (f"{total} scenes   {hindi} Hindi   {english} English",
                            f(BOLD, 34), 380, GOLD),
                           ("count them up. lowest score gets the next round in.",
                            f(BOOK, 28), 442, DIM)):
        d.text(((W - d.textlength(t, font=fnt)) / 2, y), t, font=fnt, fill=col)
    return img


# ---------------------------------------------------------------- main

def main():
    tsv = sys.argv[1] if len(sys.argv) > 1 else "clips.tsv"
    rows = list(csv.DictReader(open(tsv), delimiter="\t"))
    total = len(rows)
    hindi = sum(1 for r in rows if r["side"].strip().upper() == "BOLLYWOOD")

    for r in rows:
        n = int(r["min"])
        round_number(n).save(f"cards/n_{n:02d}.png")
        answer(r, n, total).save(f"cards/t_{n:02d}.png")

    drink().save("cards/drink.png")
    for i, img in enumerate(intro(total, hindi, total - hindi), 1):
        img.save(f"cards/intro_{i}.png")
    outro(total, hindi, total - hindi).save("cards/outro.png")
    print(f"rendered {total} rounds, drink call, 5 intro states and the end card")


if __name__ == "__main__":
    sys.exit(main())
