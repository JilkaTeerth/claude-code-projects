# Learnings (append every piece of feedback, newest last)

## 2026-10-07, v1 "5.3 Dimension Theorem" (1:48)
- Said: "this is good", but speak slower, change the tone, add insane funny hooking stories,
  explain like a kid building up to the concept, show something really interesting.
- Measured: 166 wpm (target 115 to 130). Jargon in the first 20 seconds. No story. Visuals were
  correct but only grids and labels.
- Changed: STYLE.md arc (hook story, noticing, count in the story, reveal, real version, exam,
  callback). Pause marks in say.py. Review and storyboard stages before any render.

## 2026-10-07, v2 "the Pancake Machine" (tests only, not rendered)
- Script review: v1 scored 2/10 on the automatic checks, v2 scores 10/10. Funny? and correct? wait for Teerth.
- Pace calibration: pause marks add padding, so af_heart speaks ~147 wpm at speed 1.0 in a marked
  script (not 176). The estimator now uses 147. Speed 0.92 gives ~115 wpm overall; the hook alone
  runs ~104 wpm because it's pause-heavy on purpose (comic timing).
- The storyboard caught 4 bugs with no video render: burger taller than the press gap, pancake too
  thin to show a face, Cube() renders flat in a 2D Scene (now iso_cube with coloured edges),
  the wink was invisible. Fixed in props.py so every future video gets the fix.
- Rule refined: "visual change" means a new event every 8s or less, not "beats under 14s".

## 2026-10-08, the rubric was grading its own homework
- Said: "your v2 also shudn't score so much, it's not technical to go from 2 to 10, watch 3blue1brown".
- He was right. Read 3b1b ch.3 and ch.7 transcripts (benchmarks/3b1b-ch7.md). 3b1b averages 22
  words a sentence and asks 1 question in ch.7, so it would FAIL the old checks. They measured my
  style choices, not quality.
- New rubric v2: weighted, judged with evidence, benchmark scored first (3b1b ch.7 = 7.95). The old
  checks are now pass/fail hygiene gates.
- Honest rescore: v1 4.3, v2 4.4. v2 only improved engagement. It also taught a misconception
  ("every direction is crushed or survives" is false) and kept a symmetric matrix that makes the
  kernel look perpendicular to the range.
- Rule: a score can only rise for what actually changed. A funnier hook doesn't raise Insight.

## 2026-10-08, reviewing the review (he asked: keep going until the review of the review holds)
- Round 1 critique of rubric v2: 3b1b's visuals were scored with no frames seen; no anchors; A and D
  overlapped; F for 3b1b was a guess about Teerth; v3 was given a predicted score before it existed;
  only one benchmark.
- Fixes (rubric v3): evidence tags [T]/[F]/[P] required; anchors for 0/3/6/8/10; A = logic only,
  D = the mute test; F capped at 6 without his verdict; never score unbuilt work; ordering and
  equal-weight checks. Pulled 16 real frames of ch.7: it opens with the π characters (humour) and
  uses a NON-symmetric example [2 -2; 1 -1]. Both corrected my earlier claims.
- Round 2 critique: a hand-added total was wrong (7.85, real 7.50). Totals are now computed by code only.
- Result: 3b1b 7.50 > v1 5.00 > v2 3.65, same order with equal weights, so it's robust. v2 ranks
  BELOW v1: funnier, but it stated something false, and for exam prep accuracy outranks jokes.
- Known limits, not hidden: one judge (me); 3b1b frames are 16 low-res samples; F needs his
  verdict; one benchmark. The next step for independence is a blind second judge.

## 2026-10-08, rounds 4 to 6: outcomes, not proxies
- Round 4 critique: the rubric measures proxies. Fix: a pre-registered quiz (eval/quiz-5.3.md,
  sha256 931b18b7..., written before v3) from A&H 5.3 plus our two misconception probes. A
  "student" agent sees one video, answers citing what taught it; anything not taught = 0.
- Round 5 critique: one judge (me). Fix: a blind second judge agent scores packets P/Q/R/S
  (narration + real images, my "see" text stripped so intentions can't inflate D). Label key in
  eval/blind-key.json. Limit: the 3b1b transcript is recognisable by length and style.
- Round 6 critique: v3 was written knowing the rubric (Goodhart risk). The quiz pre-dates it and the
  judge is blind; that's the guard.
- Storyboard caught 2 more bugs: a hand-typed rref with a wrong last column (now: sympy-verify every
  on-screen number, in STYLE.md), and stick lines spilling off their grids (now clipped).

## 2026-10-08, rounds 7 to 8: second judge, students, held-out quiz
- Students (pre-registered quiz, /11): v3 10, v1 6, 3b1b 5, v2 3. The v2 student BELIEVED the false
  slogan (answered "true" to "every direction is crushed or unchanged"): the misconception is real
  and it transmits. Nobody was taught how to find kernel basis vectors.
- Blind judge: v3 8.10 (stills, provisional), 3b1b 6.65, v1 4.55, v2 4.00. Same order with equal weights.
- Me vs the judge: I was 0.85 high on 3b1b (reputation) and +4 on v1's visuals (self-serving).
  Rule 7: on our own videos the judge's score stands. Rule 8: measured learning outranks the rubric.
- New errors only the judge caught: "it doesn't land on the line, it lands on zero" (zero is ON the
  line) in v1/v2; "count the pivots, that's the range" (it's dim(range)).
- Goodhart caught in myself: v3 was written after the quiz, so it covers Q7/Q9 on purpose. Fix: a
  held-out quiz written by an agent that never saw any video.
- v3.1 = v3 plus 8 fixes, each traced to a student or judge finding. Known risk: the 3D-sheets
  storyboard is weak; the real build needs a ThreeDScene.
- Length is now 5.5 min, against his 3-min preference. Unresolved trade-off: coverage vs patience.
  His call.

## 2026-10-08, round 9: held-out quiz
- Lesson-taught scores (blind grader): v3.1 90.25, v1 73.75, 3b1b 47. Correctness was 100 for all
  three: the student agents already know linear algebra, so correctness is useless as a measure and
  only the self-reported "taught" flags carry signal. That's the weakest link in the instrument.
- The held-out quiz is now SPENT for anything I change because of it. v3.2 fixes (Theorem 5.8,
  Corollary 5.11, [A|b] test, theorem names) need a fresh quiz (quiz-c) to be verified honestly.
- Still unmeasured: the finished animation (everything so far is narration + stills) and Teerth
  himself. His verdict and his real Test 2 (23 Oct) are the ground truth.

## 2026-10-08, v3.2 built (6:23, 1080p, 128 wpm measured)
- He chose one 6-minute video over two parts or a cut (asked directly).
- v3.2 = v3.1 + Theorem 5.8 (subspaces, dim range <= dim W), [A|b] membership test, Corollary
  5.11 (rank A^T), theorem names. Script frozen (sha in eval/frozen-v3.2.sha256) before quiz-c was read.
- New tooling: phrase-level cue timestamps (audio/cues.json) so visuals land on the words;
  mid-phrase cues placed proportionally; synthesized SFX (sfx/: slam, pop, ding, buzz, whoosh).
- Frame QA on a 480p render caught the worst bug of the session: in the plane beat ApplyMatrix
  on a singular matrix squashes each Dot to nothing, so the "each stick becomes one dot" frame was
  empty. Fixed by moving dots to M @ p explicitly. Rule: never ApplyMatrix a singular matrix to Dots.
- Also caught: 3 empty-screen openings (count, names, membership: a cue waits with nothing on
  screen; rule: every beat shows something in its first 0.5s), a label over an arrow, a
  garbled Text-to-MathTex morph, Kernel Method vectors overlapping the matrix.

## 2026-10-08, final round on the FINISHED v3.2
- Blind judge on real frames: v3.2 7.95 vs 3b1b 6.80 vs v1 4.90 (same order with equal weights).
  Every number on screen sympy-checked by the judge: all correct.
- Quiz-c (written after the script freeze): lesson-taught v3.2 74.67 vs 3b1b 47.5. Correctness 100 for both.
- v3.2 is ahead of 3b1b on every learning measure we have. Where 3b1b still wins: visual craft (D 8 vs 7).
- v3.3 to-do, all from evidence: (1) a short visual proof (extend a kernel basis; the new vectors
  map to a range basis); (2) one worked kernel/range for a non-AX map (write it in coordinates
  first); (3) show the kernel = {0} case early (every stick is a single dot); (4) one line on row
  space vs column space; (5) "every polynomial of degree at most 2", not "every quadratic";
  (6) fill the sparse frames (Theorem 5.8, the empty 3D axes).
- Still missing: Teerth's own verdict (F is capped) and Test 2 on 23 Oct.

## 2026-10-08, he caught it: voice cut out near the end
- Manim's add_sound mixer produced a 333s track for a 383s video on the final re-render. I'd checked the audio on the
  first HD render but not the re-render. Fix: scene logs every sound's start time (audio/timeline.json), mux.py mixes
  the soundtrack in numpy and attaches it with ffmpeg; explain.py build now refuses to deliver if audio != video length.
