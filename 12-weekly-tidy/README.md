# Weekly tidy

A file tidy that runs every Sunday at 19:00 through launchd and only moves what it's sure about.

## How it works

- `bin/tidy` scans Downloads and the Desktop. Files that match a certain rule (course code in the name, known extension) get filed automatically.
- Everything else goes on a pending list and a Todoist task. It never files something by guessing the topic.
- The `tidy` Claude skill (`SKILL.md`) finishes the job with me: it asks where each unclear file goes, one folder at a time, and moves it with a logged, no overwrite `tidy mv`.
- Nothing is ever deleted. Old stuff goes to a review pile I check myself.

## What's in `src/`

The script, the launchd wrapper and the skill.
