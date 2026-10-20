# Explainer style: the rulebook

What every video must do. Written from Teerth's feedback (LEARNINGS.md) plus what makes
3Blue1Brown work, and where we try to beat it.

## The arc (every video, in this order)
1. **Hook story (0:00 to 0:25).** An absurd, funny, concrete situation with zero maths words.
   It has a main character, an object, and an escalation of three things where the third is
   the funniest (burger, basketball, then his phone becomes "a very expensive coaster").
2. **Kid-level noticing.** Point at the one weird thing in the story and ask about it.
   Rhetorical questions, short sentences.
3. **Count or play with it.** Do the maths of the concept INSIDE the story first, with the
   story's objects (1 crushed + 2 survived = 3).
4. **The reveal.** "That's the whole theorem. Mathematicians just gave it a fancy name."
   Jargon arrives only now, mapped one-to-one onto story objects, in the same colours.
5. **The real version.** The textbook example, with the textbook's notation (Andrilli & Hecker).
6. **Exam move.** The mechanical recipe for the test, in at most three steps.
7. **Callback.** The last line returns to the hook story, so the idea sticks to the joke.

## Voice and pacing
- Target **115 to 130 words a minute** of finished audio. Kokoro af_heart at speed ~0.88 plus pause marks.
- Use `[pause]` (0.7s) after every new idea, `[beat]` (0.35s) before a punchline, `[long]` before the reveal.
- Write it the way you'd talk to a friend: contractions, "okay", "honestly", "here's the weird part".
- Sentences average under 12 words. One idea per sentence.
- Tone is warm, amused, never lecturing. Jokes are about the situation, never about the viewer being slow.

## Maths on screen
- Every matrix, rref, kernel and range shown on screen is verified in sympy before it's drawn.
  (2026-10-08: a hand-typed rref in v3's storyboard had a wrong last column.)

## Build rules (learned the hard way)
- Never ApplyMatrix a singular matrix to Dots: they squash to nothing. Move them to M @ p explicitly.
- Every beat shows something in its first half second. A cue that waits on an empty screen reads as broken.
- Don't morph Text into MathTex; it garbles mid-transform. Fade in and Indicate instead.
- QA a 480p render with a frame every 6s before the 1080p one; then a dense pass on the key beat.

- Re-check the AUDIO after every re-render, not only the first one: audio length = video length, and no silent stretch over 3s.
  (2026-10-08: Manim's mixer silently dropped the last ~50s of narration; mux.py now builds the soundtrack.)

## Visuals
- Something new happens on screen at least every 6 to 8 seconds.
- The hook is drawn as cartoon props (press, burger, phone), not grids.
- Colours carry meaning across the whole video: **red = crushed / kernel**, **yellow = kept / range**.
  The story's colours and the maths' colours are the same, so the mapping is visual.
- Labels sit on dark background boxes so they never fight with lines.
- Every frame is checked before a full render (storyboard stills).

## Where we beat 3Blue1Brown
- 3b1b assumes curiosity. We create it with a story first, because the viewer is tired and has an exam.
- 3b1b rarely gives the exam recipe. We always end with the exact moves for the test.
- The notation matches the viewer's own textbook and professor, not a generic one.
- Short: under 3 minutes per concept. One concept per video.
