# The reel format library

16 named formats. Each one is a **structure**, not a template, the frame counts are
starting points to adjust to the music, not laws.

**How to use:** pick the format whose "needs" line matches the footage you actually have,
then paste its prompt. The prompt assumes the `reels-editor` skill is loaded, so it can
be terse, the skill supplies the brand, the craft rules, and the build order.

All timings at **30fps**. `f` = frames. 450f = 15s · 600f = 20s · 900f = 30s.

Quick chooser:

| You have | Use |
|---|---|
| Good rally video | 1 · 14 · 15 |
| Mostly prize/podium stills | 2 · 9 · 16 |
| A mix, telling a day's story | 4 · 8 · 11 |
| Emotional coaching moments | 5 · 10 |
| Nothing but stills, need hype | 3 · 12 · 7 |
| A date to promote | 13 |
| Many players to feature | 6 |

---

## 1. Cold Open Rally
**Feeling:** adrenaline · **Length:** 15 to 20s · **Needs:** one clean rally clip ≥8s

Opens mid-point with zero setup. The most reliable hook in sports content: the viewer
arrives *late* and has to catch up, which is exactly the state that stops a scroll.

```
0 to 90f     rally, full speed, real court audio up. NO title, NO logo.
90 to 100f   hard cut on the winning shot. Beat 1.
100 to 160f  same shot, 0.4× speed, audio ducked to 20%. Gold "MATCH POINT" slams in.
160 to 400f  3 to 4 cuts of aftermath, reaction, handshake, coach nod. Music enters at 160f.
400 to 450f  end card: wordmark + WHERE CHAMPIONS RISE on Ink.
```
Never open on the serve. Open on the third or fourth shot of the rally.

> **Prompt:** Build a Cold Open Rally reel from the the academy footage. Find the cleanest
> rally in the video assets and open mid-point at full speed with real court audio and no
> titles. Hard-cut on the winning shot, then replay that same shot at 0.4× with a gold
> "MATCH POINT" title. Cut to 3 to 4 reaction beats with music entering, and land on the
> wordmark end card. 18s target. Show me the beat sheet before you build.

---

## 2. Podium Ladder
**Feeling:** pride · **Length:** 20 to 25s · **Needs:** 6+ prize-presentation stills

Prize photos are the academy's most-repostable asset, every one of those parents saves
it. The trap is that six near-identical handshake photos are boring. The fix is
**rhythm**: identical framing, identical duration, identical move, cut hard on the beat.
Sameness becomes the device instead of the flaw.

```
0 to 45f     hook: widest trophy-table shot, fast push-in, "MONKEY ICE OPEN 2026" gold.
45 to 585f   9 stills × 60f. Every one: same 1.06→1.12 push-in, same cut point on the beat.
          Each carries a small lower-third: category name (Boys U11, Girls U13...).
585 to 650f  the group/wide shot, held 65f, no move.
650 to 700f  end card + sponsor strip.
```
Youngest category first, oldest last. It builds.

> **Prompt:** Build a Podium Ladder reel from the the academy prize-distribution stills.
> Order the categories youngest to oldest. Every still gets an identical 60-frame hold
> and an identical 1.06→1.12 push-in, cut hard on the music beat so the repetition
> becomes the rhythm. Small gold lower-third with the category on each. Open on the
> widest trophy-table shot with the event title, close on the group shot plus sponsor
> strip. 22s. Ask me for the category names if you can't read them off the photos.

---

## 3. Where Champions Rise
**Feeling:** hunger · **Length:** 25 to 30s · **Needs:** anything, this is the anthem format

The academy's brand film. Slower than a hype reel, more deliberate. Alternates **effort**
(sweat, breath, the corner) with **reward** (trophy, the handshake). The tagline is the
spine and each line lands on a matched image.

```
0 to 60f     black. Court audio only, one shoe squeak, one ball strike. Then a hard cut
          to a face mid-effort. This is the hook: sound before image.
60 to 150f   "ONE COURT", wide empty court, slow push.
150 to 240f  "ONE PASSION", the corner, coach and player, heads together.
240 to 330f  "ONE CHAMPION", trophy lifted.
330 to 780f  build: alternating effort/reward, cuts accelerating 90f → 40f → 24f.
780 to 870f  everything stops. Held wide of the whole academy. Music tail.
870 to 900f  lion + WHERE CHAMPIONS RISE.
```
The acceleration is the whole trick. Cuts get shorter, music gets denser, then silence.

> **Prompt:** Build the Where Champions Rise anthem reel. Open on black with court audio
> only for half a second before the first image. Use the three tagline beats, ONE COURT /
> ONE PASSION / ONE CHAMPION, each matched to an image, then build an accelerating
> montage alternating effort shots with reward shots, cuts tightening from 90 frames down
> to 24. Full stop on a held wide, then the lion end card. 30s.

---

## 4. Day N: Road to Finals
**Feeling:** belonging · **Length:** 20 to 30s · **Needs:** a day's mixed footage

The episodic tournament diary. The academy already shoots this, one clip in the Aug 2026
folder has a burned-in "Day 4 Road to Finals" sticker. Formalise it: same card, same
position, same font every day, so the series becomes recognisable on the grid.

```
0 to 40f     day card: "DAY 4" huge gold, "ROAD TO FINALS" small under it, on Ink.
          Punches on for 6f, holds, cuts out, no fade.
40 to 500f   the day in 8 to 10 beats. Arrival → warm-up → play → the corner → result.
          Vary shot scale every cut: wide, close, wide, medium. Never two wides adjacent.
500 to 560f  the day's headline result as a full-screen type card.
560 to 600f  "DAY 5 →" teaser. Always end on the next one.
```

> **Prompt:** Build a "Day N: Road to Finals" episode from the the academy footage, ask me
> which day number. Open with the day card, then take me through the day in 8 to 10 beats in
> chronological order (arrival, warm-up, play, coaching corner, result), alternating shot
> scale on every cut. Finish with the headline result as a type card and a "Day N+1 →"
> teaser. 25s. Keep the day card in the exact same position and style every episode so
> the series is consistent.

---

## 5. The Corner
**Feeling:** warmth · **Length:** 15 to 20s · **Needs:** coach-athlete stills or clips

The quietest format and often the best-performing, because it is the thing parents are
actually buying: someone who cares about their kid. Between-games coaching, heads
together, a hand on the shoulder, a player staring at the floor.

```
0 to 75f     one still. Slow 1.0→1.08 push. No text at all for the first 2.5s.
75 to 330f   3 to 4 more corner moments, 60 to 85f each, all slow moves, all one direction.
330 to 420f  ONE line of type, quiet, Paper not gold: "Every champion has someone in
          their corner."
420 to 480f  the player walking back onto court. End card, small.
```
Music: sparse piano or ambient. No drums. No beat cutting, this is the one format where
you deliberately ignore the beat and cut on breath instead.

> **Prompt:** Build The Corner, a quiet reel from the coach-and-player moments in the
> the academy stills. No text for the first 2.5 seconds. Slow push-ins only, all moving the
> same direction, 60 to 85 frames each. One line of quiet type near the end: "Every champion
> has someone in their corner." End on a player heading back to court. Sparse ambient
> music, no drums, and cut on breath rather than on the beat. 18s.

---

## 6. Whip Pan Roster
**Feeling:** energy · **Length:** 15 to 20s · **Needs:** 8+ players, one shot each

Fast player introductions. Each player gets ~35f and a name slam. The whip transition
sells it: a 4-frame motion-blurred wipe between every card.

```
0 to 30f     "THE SQUAD" or "MEET THE 2026 ROSTER"
30 to 450f   12 × 35f. Each: player image, 1.15 scale, opposing-direction drift.
          Name in Display gold, punches on at frame 4 of each card.
          4f whip blur between every one.
450 to 500f  the whole group, held. End card.
```
Alternate drift direction card to card (left, right, left), that alternation is what
makes the whips feel motivated rather than random.

> **Prompt:** Build a Whip Pan Roster reel from the the academy player photos. One card per
> player, 35 frames each, name in gold Display type punching on 4 frames into each card.
> Add a 4-frame motion-blur whip between every card and alternate the drift direction
> card to card. Open on a "MEET THE 2026 ROSTER" title, close on the group shot. 17s.
> Ask me for the player names.

---

## 7. Freeze & Name
**Feeling:** triumph · **Length:** 10 to 15s · **Needs:** one clip with a clear winning moment

The shortest format. One action, one freeze, one name. Brutally effective as a
single-player highlight the athlete will repost.

```
0 to 100f    the point, full speed, real audio.
100 to 105f  FREEZE on the winning frame. Audio hard-cuts to silence.
105 to 115f  gold stroke draws around the player (or a gold flash frame).
115 to 250f  name slams on huge. Category underneath, small. Frozen frame holds.
250 to 330f  unfreeze, motion resumes into the celebration. Music hits.
330 to 360f  end card.
```
The silence at the freeze is doing more work than any effect.

> **Prompt:** Build a Freeze & Name highlight from the the academy rally footage. Play the
> point at full speed with real audio, freeze hard on the winning frame with audio cutting
> to total silence, slam the player's name on huge in gold with the category underneath,
> then unfreeze into the celebration as music hits. 12s. Ask me for the player name and
> category.

---

## 8. Before / After the Point
**Feeling:** tension → release · **Length:** 15s · **Needs:** a rally + reaction stills

Two-act structure built on a single hard cut. Everything before the cut is tight, tense,
close. Everything after is wide, loose, bright.

```
0 to 200f    ACT 1, close-ups only. Hands on the racquet, eyes, the ball. Tight framing,
          desaturated grade, low rumble under it. No wide shots at all.
200 to 210f  the point. One cut.
210 to 420f  ACT 2, wides only. Warm grade, music, arms up, the bench standing.
420 to 450f  end card.
```
The grade change across the cut does half the work. Set two `apply_color` grades and
paste each to its act.

> **Prompt:** Build a Before/After the Point reel from the the academy footage. Act 1 is close
> framing only with a cool desaturated grade and a low rumble under it, no wide shots.
> One hard cut on the decisive point. Act 2 is wide shots only, warm grade, music up.
> Use two distinct colour grades, one per act, so the cut reads as a tonal flip. 15s.

---

## 9. Trophy Rain
**Feeling:** abundance · **Length:** 12 to 18s · **Needs:** many trophy/prize stills

Pure velocity. Every trophy handover in the folder, cut fast on the beat, no lower-thirds,
no explanation. The message is volume: *look how many kids won something today.*

```
0 to 36f     the trophy table, wide. "47 TROPHIES. ONE DAY." (use the real count)
36 to 450f   every prize still at 18 to 24f each, hard cuts, all on beat. Alternate
          push-in / pull-out so the rhythm has internal variation.
450 to 500f  the trophy table again, now empty. Held.
500 to 540f  end card.
```
The empty-table bookend is the joke and the payoff. Shoot it deliberately next time.

> **Prompt:** Build a Trophy Rain reel, every prize-handover still from the the academy
> folder, 18 to 24 frames each, hard cuts on the beat, alternating push-in and pull-out. No
> lower-thirds. Open on the trophy table wide with a count of the trophies, close on the
> table after it's cleared. 15s. Tell me the trophy count you used.

---

## 10. Silent Coach
**Feeling:** intimacy · **Length:** 20s · **Needs:** coaching footage with usable audio

No music. At all. Just what the coach is saying between games, with the room's ambience.
On a feed of volume-maxed hype reels, silence is the pattern interrupt.

```
0 to 450f    coaching audio runs unbroken. Pictures cut to what's being said.
          `remove_silence` to tighten dead air, `denoise_audio` for room hum.
450 to 560f  the player nods, stands, walks out.
560 to 600f  end card, silent, no sting.
```
Burn captions, most viewers are muted, and the words are the entire point here.

> **Prompt:** Build a Silent Coach reel from the the academy coaching footage. No music at
> all, the coach's audio and room ambience only. Run `remove_silence` to tighten pauses
> and `denoise_audio` for room hum, then cut pictures to match what's being said. Burn
> captions from the transcript in Archivo on Ink plates. End on the player walking back
> out, with a silent end card. 20s.

---

## 11. The Parents
**Feeling:** community · **Length:** 15 to 20s · **Needs:** spectator/audience stills

Nobody makes this reel and everybody responds to it. The audience *is* the customer.
Grandmothers on plastic chairs, mothers filming on phones, fathers leaning forward.

```
0 to 60f     a parent watching, unaware of camera. No text.
60 to 400f   6 to 8 spectator moments, 45 to 55f each, gentle moves. Between two of them, cut
          away to what they're watching for 20f, then back. That reverse is the device.
400 to 480f  "They train. You show up. That's the deal." (or the academy's own line)
480 to 540f  end card.
```

> **Prompt:** Build The Parents reel from the the academy spectator stills, the families
> watching, not the players. 6 to 8 moments at 45 to 55 frames with gentle moves. Twice, cut
> away for 20 frames to what they're watching and back again. One warm line of type near
> the end. 18s. Suggest three options for that line and let me pick.

---

## 12. One Court, One Passion
**Feeling:** identity · **Length:** 20s · **Needs:** anything

Tagline-driven. Three words, three acts, hard structural symmetry: each act is exactly
180f and opens with its word on a full-screen Ink card.

```
0 to 180f    "ONE COURT", the place. Empty court, the building, the wall.
180 to 360f  "ONE PASSION", the people. Effort, sweat, the corner.
360 to 540f  "ONE CHAMPION",  the result. Trophies, the podium, the lift.
540 to 600f  lion + wordmark.
```
The rigidity is the point. Same card duration, same type position, same transition.

> **Prompt:** Build the One Court, One Passion reel. Three acts of exactly 180 frames
> each, each opening with its word full-screen in gold on Ink: ONE COURT (the venue), ONE
> PASSION (the people and the effort), ONE CHAMPION (the trophies). Identical card
> duration, type position, and transition across all three. Lion end card. 20s.

---

## 13. Countdown Card
**Feeling:** urgency · **Length:** 12 to 15s · **Needs:** the event poster + any action

Event promo. Its only job is the date and the registration link, but the date has to
arrive *last*, front-load energy, back-load information.

```
0 to 24f     hardest action frame available. Full speed. No text.
24 to 240f   6 to 8 fast action beats, 24 to 30f each, on beat.
240 to 300f  everything stops on a freeze. "MONKEY ICE SQUASH OPEN"
300 to 360f  "JUNE 2026" on a gold plate.
360 to 420f  categories: "BOYS & GIRLS · U11 U13 U15 U17 U19" small, clean.
420 to 450f  "REGISTER, LINK IN BIO" + sponsor strip.
```
Never open a promo on the poster. Open on a kid hitting a ball.

> **Prompt:** Build a Countdown Card promo for the Monkey Ice Squash Open. Open on the
> hardest action frame with no text, run 6 to 8 fast beats on the music, then freeze
> everything and deliver the event name, JUNE 2026 on a gold plate, the categories, and a
> REGISTER, LINK IN BIO card with the sponsor strip. Do not open on the poster. 14s.
> Confirm the categories and dates with me before building.

---

## 14. Rally Cam
**Feeling:** mastery · **Length:** 15 to 20s · **Needs:** technique footage, one player

Technique showcase, a drill or solo hitting, treated as craft rather than competition.
Speed ramps do the storytelling: full speed into the shot, 0.3× through contact, full
speed out.

```
0 to 30f     mid-swing, already moving.
30 to 420f   4 to 5 shots. Each: 20f full speed → 40f at 0.3× through contact → 15f full speed.
          Tiny gold labels on 2 of them only: "DROP", "BOAST", "STRAIGHT DRIVE".
420 to 480f  the player resets, breathing. Held.
480 to 540f  end card.
```
Label two shots, not five. Restraint is what separates this from a coaching video.

> **Prompt:** Build a Rally Cam technique reel from the the academy court footage, one player.
> Speed-ramp each shot: full speed in, 0.3× through the moment of contact, full speed out.
> 4 to 5 shots. Label only two of them with small gold shot names. End on the player resting,
> held. 17s.

---

## 15. Match Point
**Feeling:** drama · **Length:** 20 to 25s · **Needs:** one long rally, good audio

The single-point film. One rally, treated like a scene. Real audio carries it; music only
enters after the point is won.

```
0 to 60f     the serve. Wide. Real audio only, shoes, breath, the ball.
60 to 330f   the rally uncut. Do not cut. The length IS the tension.
330 to 345f  the winning shot at 0.25×, audio pitched down.
345 to 420f  full speed again, the reaction. Music hits here for the first time.
420 to 540f  crowd, coach, handshake.
540 to 600f  score card: "11 to 9. MATCH." then end card.
```
The discipline is not cutting during the rally. Every instinct will say cut. Don't.

> **Prompt:** Build a Match Point reel from the longest clean rally in the the academy
> footage. Do not cut during the rally, let it run uncut with real audio only, no music.
> Slow the winning shot to 0.25× with the audio pitched down, return to full speed for the
> reaction, and let music enter for the first time there. Finish with a score card and the
> end card. 22s. Ask me for the final score.

---

## 16. Grid Drop
**Feeling:** completeness · **Length:** 15 to 20s · **Needs:** 9+ stills of anything

The photo-dump reel, a carousel that moves. A 3×3 grid assembles tile by tile on the
beat, then one tile takes over full-screen, then the grid rebuilds with new photos.

```
0 to 150f    9 tiles drop in on consecutive beats, 16f apart, each scaling 0.9→1.0.
150 to 180f  the grid holds, complete.
180 to 260f  one tile expands to full screen, the day's best photo.
260 to 410f  grid rebuilds with 9 new photos.
410 to 470f  final tile expands: the group shot.
470 to 540f  end card.
```
Good use for the leftovers, photos not strong enough to hold a full beat alone still
work as one ninth of a grid.

> **Prompt:** Build a Grid Drop reel from the the academy stills. A 3×3 grid assembles tile by
> tile on consecutive beats, 16 frames apart, holds complete, then one tile expands to
> full screen. Rebuild the grid with a second set of nine and expand to the group shot.
> 18s. Use the weaker photos as grid tiles and save the strongest for the full-screen
> expansions.

---

## Adding a format

When you invent one that works, append it here in the same shape: name, feeling, length,
needs, the frame map, one thing that makes it work, and a copy-paste prompt. A format that
worked once and wasn't written down is a format you will re-derive badly.
