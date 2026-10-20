# Maths explainer videos with an honest evaluation

A local pipeline that makes 3Blue1Brown style explainer videos for my linear algebra class: Manim animation, Kokoro TTS voice, phrase timed sync, synthesized sound effects. The first full video explains the Dimension Theorem in about 6 minutes.

## The interesting part is the evaluation

It's easy to make an AI grade its own work 10/10. That happened: version 2 scored 10/10 on Claude's own checks and I called it out. So I had it rebuild the evaluation to resist gaming:

- A rubric benchmarked against real 3Blue1Brown transcripts first (3b1b ch.7 scores 7.95), so the rubric measures quality, not my style choices.
- A pre registered quiz, plus two held out quizzes written by agents that never saw the videos.
- A blind judge and a blind grader.
- A rule that a score can only go up for what actually changed. A funnier hook doesn't raise Insight.

Result: ahead of 3b1b ch.7 on the judge (7.95 vs 6.80) and on taught learning (75 vs 48 on the last quiz). Stated limit: the student agents already know the maths, so only their "taught" flags carry signal.

## Other things it caught

- Speaking speed measured at 166 wpm, way too fast. Retuned to about 115 wpm with pause marks.
- A storyboard stage that catches visual bugs before any render. It found 4 in one pass (a prop taller than the gap it had to fit through, a face too thin to see, a 3D cube rendering flat, an invisible wink).

## What's in `src/`

`explain.py` (the pipeline), `props.py` (reusable animated props), `STYLE.md`, `RUBRIC.md`, `LEARNINGS.md` (every piece of feedback, newest last), the final v3.2 scene, and the eval quizzes and results. Rendered video and audio are left out.
