# Edit craft, what makes a cut look expensive

Effects are cheap and everyone has them. What separates a paid edit from a free one is
pacing, motion discipline, type restraint, and one consistent grade. This file is the
craft layer; `palmier-cookbook.md` is how to execute it in the tool.

---

## 1. Pacing

**Cut length carries meaning.** Use it deliberately:

| Length | Frames @30 | Reads as |
|---|---|---|
| Flash | 4 to 10f | Impact, punctuation. Only in a run of them. |
| Fast | 12 to 24f | Energy, montage, hype |
| Medium | 30 to 60f | Narrative, "watch this" |
| Slow | 75 to 120f | Emotion, weight, let-it-breathe |
| Held | 150f+ | The end, or a deliberate stop |

**Never uniform.** A reel of all-45f cuts is a metronome and reads as an automated edit, which is precisely the tell you're trying to avoid. Every reel needs a **rhythm curve**:

```
slow ─── accelerating ───── fastest ── STOP ── held
 90f      70 55 40 30        20 20 20    (silence)   150f
```
The stop before the ending is the single highest-leverage move in short-form editing. One
beat of nothing, then the last image. It makes everything before it feel intentional.

**Cut on motion, not after it.** A cut lands cleanest when the outgoing frame is still
moving. If a player's arm is mid-swing, cut there, not after the swing completes. The eye
carries the motion across the cut and stops noticing the edit.

**Cut on the beat.** `detect_beats` returns beat positions; snap cut points to them.
Off-beat cuts feel cheap even when the viewer can't articulate why. Exception: **The
Corner** and **Silent Coach**, where you cut on breath instead.

---

## 2. Motion on stills, the Ken Burns rule

**A static photo on a moving timeline looks broken.** Every still gets a move. But the
move must be *invisible*, if the viewer notices the zoom, it's too much.

| Setting | Value |
|---|---|
| Scale range | 1.00 → 1.08 over a 60f hold. **Never exceed 1.15.** |
| Direction | Push-in for reward/emotion. Pull-out for reveal/context. |
| Position drift | ≤ 3% of frame width, and only *with* the scale, never against it. |
| Easing | Ease-out. A linear zoom is the amateur signature. |
| Start scale | Never 1.00 flat on a photo you'll crop, start at 1.02 so edges never show. |

**Direction discipline:** within one section, all moves go the same way. Mixed directions
create visual chatter. Change direction only at a section break, and when you do, the
change itself becomes a transition.

**Match the move to the subject.** Push in on a face. Pull out from a trophy to reveal the
room. Drift across a wide. Never push in on a wide shot with no clear subject, there's
nothing to arrive at.

---

## 3. Type

Amateur edits are identifiable by their type in under one second. The rules:

- **Two fonts, three sizes.** Already in `brand-kit.md`. This one rule fixes most edits.
- **Punch on, don't fade on.** Text should arrive in 3 to 5 frames with a scale from 1.06 →
  1.00 and ease-out. Fading text in over 15 frames reads as a slideshow.
- **Hold ≥ 24f.** Below 0.8s nobody reads it, so it's decoration you paid for with
  attention.
- **Cut out, don't fade out.** Especially on beat-cut sections.
- **Never centre-centre** unless it's a full-screen title card. Lower-left at y≈1350 or
  upper-left at y≈360 reads as designed; dead-centre reads as default.
- **One text element on screen at a time.** Two competing labels means the viewer reads
  neither.
- **Always a plate or shadow.** Squash courts are white walls and busy backgrounds; raw
  white type vanishes.

**The hook text specifically:** ≤ 5 words, present tense, no punctuation at the end. It
appears by frame 20 and leaves by frame 70. It is a hook, not a summary.

---

## 4. Grade

**One grade for the whole reel, pasted to every clip.** Mixed grades are the most visible
amateur tell, phone footage from three cameras, ungraded, cut together, looks exactly
like what it is.

Build one grade, then paste it via `apply_color`'s `color` parameter to every clip. The
reference `get_timeline` returns a graded clip's `color` block in the exact vocabulary
`apply_color` accepts, copy that object onto the rest.

House grade for the academy (indoor court, mixed fluorescent + daylight):

| Control | Direction | Why |
|---|---|---|
| Temperature | slightly warm | Fights the green-cyan of indoor fluorescents |
| Tint | slight magenta | Same reason, fluorescents skew green |
| Contrast | +modest | Phone footage is flat out of camera |
| Saturation | +slight | But watch the blue walls; they clip to neon fast |
| Highlights | pull down | Court white walls blow out |
| Shadows | lift slightly | Crushed blacks on a dark court hide the players |

**Test the grade on the hardest frame**, the blue-wall venue shots, not the easiest one.
If the blue wall stays believable, everything else will.

Two-grade exception: **Before/After the Point**, where the grade flip *is* the edit.

---

## 5. Audio

Audio is half the edit and gets a tenth of the attention.

- **Real audio in the hook.** Shoe squeak, ball strike, breath. Nothing signals "real
  sports content" faster. Then duck it under music, don't kill it, keep it at 15 to 25%.
- **Music enters on a cut**, never mid-shot.
- **Duck the bed to ~13%** under any speech.
- **The drop is a cut point.** Find it, put your best image there.
- **Silence is an effect.** One beat of nothing before the payoff outperforms any
  transition sound.
- **Never fade music out at the end**, that's a school project. Either cut it dead on the
  last frame, or let one tail note ring over the end card.
- **Duration-match the music to the edit**, not the edit to the music, unless the format
  is beat-driven (2, 9, 16).

---

## 6. Transitions

Default to a **hard cut**. It is correct 90% of the time.

The only earned transitions:
- **Whip / motion blur** (4f), when both shots have motion in the same direction.
- **Flash to gold** (2 to 3f), on a beat drop, once per reel maximum.
- **Speed ramp**, the transition that isn't a transition. Best tool you have.
- **Match cut**, same shape, same position, two different shots. Rare and worth hunting
  for: a racquet swing cutting to a trophy lift on the same arc.

Banned: cross-dissolves between action shots, star wipes, page curls, zoom blurs on every
cut, and anything the software offers as "cinematic".

---

## 7. The last three frames

The final image is what gets screenshotted and what the viewer leaves with.

- End on **stillness**. Never mid-motion.
- End card holds **≥ 45f**. Anything less and the logo is a flicker.
- The end card is the *only* place the logo gets to be big.
- If the reel is a promo, the CTA is the last card, not the logo.

---

## 8. Self-check before export

Run this list. It catches most of what goes wrong:

- [ ] Is there motion in frame 1? (not a logo, not a title card)
- [ ] Does the hook land before frame 45?
- [ ] Any clip under 8f or over 105f that isn't deliberate?
- [ ] Does every still have a move? Same direction within each section?
- [ ] More than 2 fonts or 3 sizes anywhere?
- [ ] Any text in y<220 or y>1560, or x>900?
- [ ] Is there one grade across all clips?
- [ ] Do the cuts land on beats (or on breath, if that's the format)?
- [ ] Is there a stop before the ending?
- [ ] Does the last frame hold ≥45f on stillness?
- [ ] Sponsor obligations met?
- [ ] 1080×1920, 30fps, H.264, verified with `ffprobe`, not assumed?
