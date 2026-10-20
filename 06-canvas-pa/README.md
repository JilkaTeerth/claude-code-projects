# Canvas PA

An always on study assistant at localhost:7373. Its sibling, the Study Desk, is about having the right material. This one is about actually starting.

## Design rules (from what works for me)

1. **One thing, not a list.** A list of four gets scrolled past.
2. **A first step, not the task.** Every block names the smallest opening move, like "open the template and paste in question 1, don't solve it yet."
3. **Cost of delay in hours per day.** "Start today 1.2h/day, wait until Sunday 4.8h/day" works better than "due Monday".
4. **Schedule the daily rate, not the whole task.** Max 3h a day, blocks of 30 to 90 minutes.
5. **Honest check ins.** After each block it asks whether the work happened. Two answers in a course give a correction factor applied to all future estimates.

## Pieces

`pa.py` (server, 5 minute Canvas poller, notification loop), `planner.py` (free slots around class and squash training, cost of delay), `notes.py`, `nudge.py` (morning brief, block start, check in, deadline warnings), `cli.py`, `capture.py` (squash schedule overrides).

## What's in `src/`

The code and README. My timetable, squash schedule and tick data are left out.
