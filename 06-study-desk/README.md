# Study Desk

My local study pipeline: Canvas to Todoist to study guides, on a schedule, with a dashboard at localhost:7474.

## Why it exists

I missed a lab because the assignment never made it from Canvas into anything I actually look at. So Claude built a pipeline that pulls every deadline, puts it where I see it, and builds the material to start on.

## Pieces

- `bin/canvas`, a Canvas LMS CLI on the Canvas REST API.
- `bin/canvas-sweep`, Canvas to Todoist sync, 4 times a day through launchd. Dedup is stateless: each task carries `[canvas:<id>]` in its description, so it can't create duplicates even if it crashes halfway.
- **Dead man's switch.** The first sync job died silently for 9 days and nobody noticed. The new one tells me if it hasn't run.
- `parse_syllabus.py` turns syllabus schedule tables into JSON: test dates, what each test covers, the exact assigned problems.
- `bin/study-guide` builds a guide per test from the professor's own material. It respects each course's AI policy, and hand written guides are marked so the script never overwrites them, not even with `--force`.
- `bin/dsc215-watch`, because one professor announces quizzes only inside lecture handout PDFs. It reads the PDFs and creates "Build guide" tasks.
- `server.py`, the dashboard.

## What's in `src/`

All of the above. Credentials are read from env files that are not in the repo. Professor names are replaced with generic labels.
