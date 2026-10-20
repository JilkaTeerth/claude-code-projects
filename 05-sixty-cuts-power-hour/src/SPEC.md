# Visual spec, measured off the reference

Reference: `Guess the Movie - Power Hour`, Vercery, YouTube `B0uYXqmmIa0`, 3897s.
Every number below was measured off 1280x720 frames pulled from that video, not
estimated by eye. Frame grabs live in the scratchpad as `frames720/*.png`.

Canvas for everything here: **1280 x 720, 30fps**.

## Round timing (confirmed, keep as is)

Black frames in the reference sit at `26.97, 93.53, 157.80, 224.33`, so its
rounds run 66.6 / 64.3 / 66.5s. We use a flat **60s** round instead, which is
the only intentional divergence and makes 60 rounds land on exactly one hour.

    0:00 - 0:10   audio only. Leader on screen, no numerals yet.
    0:10 - 0:20   audio only. Big countdown numerals, 10 down to 1.
    0:20          leader dissolves over 0.55s, picture revealed mid scene.
    0:40          movie name fades in bottom left over 0.7s, stays.
    0:55.2        "Drink!" fades in
    0:58.0        "Drink!" gone
    1:00          hard cut to the next round

The scene's audio runs unbroken from 0:00. That is the whole trick: the picture
is underneath the leader the entire time, it just is not shown.

## Leader (leader.mp4, 20s, silent)

Ground is pure black. Corners measure luma 0-2.

**Lamp.** A soft white radial. Measured: luma > 200 spans **x 312..963** and
**y 88..685**, so a bright core of roughly 651 x 597, falling smoothly to black
by the frame edge. Slightly wider than tall. Build it from stacked ellipses and
a heavy gaussian blur, not a hard shape.

**Rings.** Faint, not bright. At y=352 the ring pixels read 245-247 against a
local background of 240-243, so only about 5 luma above ground. Centred on
(640, 360), elliptical, radii near 225, 250, 300 and 320.

**Crosshair.** Black, not grey. A column profile at x=180 across the horizontal
line reads `180 179 175 175 167 121 58 7 0 44 111 161 175 ...` so the line is
about 3px of true black with roughly 2px of antialiasing either side. Full
width at y=360 and full height at x=640, dash-dot.

**Sweep hand.** Black, about 3px, from the centre out past the frame edge, one
revolution per second.

**Numerals.** Measured on the "4": bounding box **x 482..768 (286 wide), y
149..569 (420 tall)**, centred on the frame. Aspect 0.68. Arial at the size
that gives 420 tall is 327 wide (aspect 0.78), so the reference face is
condensed: use **Arial Narrow** and tune the size until the digit box measures
286 x 420. Fill is black.

**Phases.**

    0.0 - 0.5    black
    0.5 - 2.6    "HEAD", heavily defocused
    2.6 - 4.2    lamp only, still soft
    4.2 - 10.0   sweep starts, focus pulls in
    10.0 - 20.0  numerals 10 down to 1, one per second, sharp

## Round number

White, bold rounded sans, rendered as `N.` (with the full stop).
Measured bounding box **x 17..59, y 14..69**, so about 42 wide by 55 tall.
That is roughly fontSize 76. Sits on the leader only, gone by the reveal.

## Movie name

The reference uses each film's real logo artwork, which we cannot source for 60
titles, so this is the one element that is a deliberate substitute. Match its
geometry: the logo block occupies **x from 14, y 550..690**, bottom left,
bottom aligned around y=690.

## Drink call

Transitional serif (Times New Roman is a match).
Measured white bounding box **x 319..948 (629 wide), y 276..437 (161 tall)**,
centre **(633, 356)**, so essentially dead centre, a few pixels above.
Times New Roman at 230 measures 613 x 163 and at 240 measures 640 x 170, so
**fontSize about 233**.

Fill pure white. The shadow is a **hard black offset of about 8px down and
right, with no blur**, not a soft glow.

Normalized for Palmier: centerX `633/1280 = 0.4945`, centerY `356/720 = 0.4944`.

## Intro card

Blue vertical light-streak motion background, dark navy base with bright cyan
beams and a horizontal light bar low in the frame.

    "How to Play:"   white rounded bold, centred, cap band y 48..108
    rule 1           white bold, centred, y 138..185
    media box        x 14..682, y 243..625  (668 x 382)
                     plays the leader first, then a clip
    rules 2 and 3    to the right of the box, left edge x=700, from y=250,
                     line height about 63
    "Good Luck!"     right side, around y 400..460

Rule text, verbatim from the reference:

    1. Drink on each scene change.
    2. The first 20 seconds will just be a scene/song. Try to guess the movie
       to make someone drink again.
    3. Video will then be shown. The movie name will appear at 40 seconds at
       the bottom left.

## Build shape

`leader.mp4` and the 60 clean scene clips are made with PIL and ffmpeg, because
a film leader cannot be drawn in an NLE and Palmier's text tops out at
fontSize 300 while the numerals need about 586. Everything above that cap is
assembled in **Palmier Pro**: the movie track, the leader track, and the round
number / movie name / drink call as native text layers, exported from there so
the project stays editable by hand afterwards.
