# Sixty Cuts

A 60 minute movie power hour. One Bollywood or Hollywood scene per minute,
alternating, sixty rounds, exactly sixty seconds each. The format is copied
shot for shot from `Guess the Movie - Power Hour` (Vercery, YouTube
`B0uYXqmmIa0`); only the films are ours.

**Finished file: `POWERHOUR.mp4`** (60:24, a 24 second intro card plus exactly
60:00 of rounds). `POWERHOUR_small.mp4` is the same thing at a shareable size.

## How a round plays

    0:00 - 0:10   audio only. Leader on screen, no numerals yet.
    0:10 - 0:20   audio only. The countdown runs, 10 down to 1.
    0:20          the leader dissolves, picture revealed mid scene.
    0:40          the movie name fades up bottom left and stays.
    0:55          "Drink!"
    1:00          hard cut to the next round

The scene's audio runs unbroken from 0:00. That is the whole trick: the
picture is underneath the leader the entire time, it just is not shown.

## Where it is built

Two halves, split by what each tool is actually good at.

**ffmpeg and PIL** make the things an editor cannot:

    clean.sh       60 scene clips, each exactly 60s, levelled, no overlays
    leader_ref.py  leader.mov, the countdown, ProRes 4444 with real alpha
    intro_bg.py    intro_bg.mp4, the blue light-streak intro background

**Palmier Pro** assembles it. Project: `~/Documents/Palmier Pro/Sixty Cuts
Power Hour.palmier`, 1280x720 at 30fps, two timelines.

    Timeline 1    the hour. 361 objects over six tracks:
                  V1+A1 scenes, V2 side/year, V3 movie name,
                  V4 drink call, V5 leader, V6 round number
    Intro Card    the 24 second how to play card

Everything is live, so any round can be nudged by hand without rebuilding.

## Matching the reference

`SPEC.md` holds every measurement, taken off 1280x720 frames of the source
rather than estimated. What the finished build actually hits:

    leader numeral   282 x 417 ink box     target 286 x 420
    lamp, row 340    212..1068             target 207..1069
    lamp, col 980    202..518              target 200..521
    lamp at x=180    luma 174              target 179
    frame corners    luma 0                target 2
    "Drink!"         630 x 161             target 629 x 161
    intro title      554 x 78              target 552 x 79
    intro rule 1     831 x 49              target 828 x 48

Two things worth knowing if you touch the text. Palmier's `fontSize` renders
about 0.66x canvas pixels and caps at 300, so "Drink!" needs `widthScale` and
`heightScale` to reach the reference size, and the leader numerals (about 586)
cannot be text at all, which is why they live inside `leader.mov`. And no font
on this machine has the reference's numeral proportions, so `leader_ref.py`
renders each digit large, crops to the ink and resamples to the measured box.

## Rebuilding

    ./build.sh links      check what each row resolved to
    ./pick.py --write --all --refresh
                          replace any source that is too short, too long or
                          under 480p, and clear the stale files for those rows
    ./build.sh fetch      download the 60 sources into raw/
    ./clean.sh            cut the 60 clean scene clips
    python3 leader_ref.py rebuild the countdown
    python3 intro_bg.py   rebuild the intro background

Then reassemble in Palmier, or use the older all-ffmpeg path (`build.sh cut
join`) which burns the overlays in directly and needs no editor.

## Editing clips.tsv

Columns are tab separated: min, act, side, movie, year, scene, search, url, offset

    url      pin an exact YouTube URL instead of trusting the search
    offset   start the window this many seconds into the source

A row with no offset gets its leading silence measured and skipped, so a clip
that opens on two seconds of black does not burn the guessing window.

`./qa.sh` drops a contact sheet of every finished round into `qa/`, sampled at
0:45 so both picture and name are up. That is how you catch a row whose search
landed on a trailer or the wrong scene.

## Decisions, not defects

- The movie name **hard cuts in at 0:40** rather than fading over about 0.7s.
  Teerth reviewed this and called it fine on 2026-09-10. Leave it alone. If it
  ever does need to fade, it is `fadeInFrames` on the 120 name and side/year
  clips plus a full re-export of the hour.
- The reference uses each film's real logo artwork bottom left. Sourcing 60 of
  those is not realistic, so the name is set as type in the same position and
  size band. This is the one element that is a deliberate substitute.
