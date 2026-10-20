# Canvas PA

Always-on study assistant for Teerth's F&M coursework. Runs as a launchd agent,
polls Canvas every 5 minutes, serves http://localhost:7373.

## Files
- `pa.py`        server + Canvas poller + notification loop
- `planner.py`   free-slot detection, cost-of-delay maths, daily block planning
- `notes.py`     reads your notes from `~/Documents/F&M Notes/<COURSE>/`
- `nudge.py`     macOS notifications (morning brief, block start, check-in, deadlines)
- `config.json`  timetable, per-course difficulty, office hours, poll interval
- `squash.json`  squash schedule scraped from Teamworks (Aug 2026 - Feb 2027, 112 events)
- `squash_overrides.json` your own cancellations and additions, applied over the scrape
- `tasks.json`   tasks you added yourself
- `squash-import.ics` the file imported into Google Calendar (101 events, 28 Aug 2026)
- `store.json`   what you ticked, binned, and logged. Your real data.
- `state.json`   last Canvas snapshot (cache)
- `sent.json`    notification dedupe ledger

## Writing to it from the browser

The capture bar at the top of the page is the point. Four modes, all persist to disk
and feed straight back into planning:

- **+ task**, anything Canvas does not know about. Lands in `tasks.json`, appears in
  Deadlines marked "yours", and gets scheduled into blocks like any other work.
- **+ note**, appends to `~/Documents/F&M Notes/<COURSE>/<date> quick.md`. Shows up in
  the brief for that course's next class.
- **+ question for office hours**, filed under a `## questions` heading so
  `notes.open_questions()` surfaces it before you see that professor.
- **squash change**, cancel a session the team dropped, or add an early/late one.
  Stored in `squash_overrides.json` and folded over the Teamworks scrape by
  `capture.apply_overrides()`, so re-scraping never wipes your edits.

Endpoint is `PUT /api/add` with a `kind` field. See `capture.py`.

## Control
```
launchctl unload ~/Library/LaunchAgents/com.teerth.canvaspa.plist   # stop
launchctl load   ~/Library/LaunchAgents/com.teerth.canvaspa.plist   # start
tail -f ~/.canvas-pa/pa.err                                          # errors
canvas upcoming                                                      # terminal view
```
Editing `config.json` or any `.py` needs an unload/load to take effect.

## How the estimates work
Each assignment gets a base estimate from its points and the course's difficulty
rating in config.json. Every time you answer a check-in, the PA compares what it
predicted against what you reported and stores a per-course correction factor.
After 2 check-ins in a course the factor goes live and all future estimates for
that course are multiplied by it. Answer check-ins honestly or this stays wrong.

## Notifications
Two independent channels:
1. **Browser** - works now, needs the tab open. Click "enable notifications" once.
2. **macOS via terminal-notifier** - works with the tab closed, but macOS must
   grant permission. System Settings > Notifications > terminal-notifier > Allow.
   Until that is granted, `nudge.py` silently no-ops.

## Refreshing the squash schedule
`squash.json` is a static scrape. Teamworks needs an interactive login, so it
cannot self-refresh. When the schedule changes, ask Claude to re-scrape it, or
subscribe Google Calendar to the Teamworks feed for a self-maintaining version.

## Known assumptions
- Last day of classes assumed **11 Dec 2026** for the Google Calendar recurrences.
- Waking window for planning is 08:00-23:00, max 3h of planned work per day.
- Office hours conflicts for McDanel are hardcoded in config.json.
