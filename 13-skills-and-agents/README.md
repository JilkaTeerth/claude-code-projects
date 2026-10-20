# Custom skills and agents

Things I built to extend Claude Code itself.

## The Council (`agents/the-council.md`)

An adversarial review agent for decks and proposals. Three roles: VERITAS (accuracy purist), IGNIS (persuasion maximalist) and ARBITER (the boss who decides). Each reviewer has to directly attack at least 3 of the other's findings by ID. On a real client deck it caught overhead being counted twice, which inflated the per role cost above the deck's own stated band.

## Reel footage scout (`agents/reel-footage-scout.md`)

Watches a folder of raw photos and video and returns a footage log: what each clip is, its mood, motion, whether it's hook grade, and which reel formats the footage can support. It exists because looking at dozens of images uses a lot of context, so a subagent takes that cost and returns only the conclusions.

## Reels editor skill (`skills/reels-editor/`)

A skill that edits Instagram reels for a squash academy in Palmier Pro through its MCP server. It includes a library of named reel formats, each with a ready prompt (Cold Open Rally, Podium Ladder, Freeze and Name...), edit craft rules and a Palmier cookbook. The client brand kit and footage log are left out.

## Also used daily

- An LLM council skill (5 advisors, anonymous peer review, then a verdict) for real decisions. Not written by me.
- An Obsidian second brain that Claude writes to after every session, with hooks that capture project work automatically.
