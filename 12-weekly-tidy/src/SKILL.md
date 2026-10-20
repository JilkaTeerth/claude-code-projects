---
name: tidy
description: Teerth's weekly file tidy. Use when he says "tidy", "weekly tidy", "sort my files", "organise my downloads", or opens the Todoist task "Weekly tidy: N files need a home". Works through ~/.tidy/pending.md, asking him where unclear files go, and moves them with the logged, no-overwrite `tidy mv`.
---

# Weekly tidy session

Every Sunday at 19:00, `~/bin/tidy` (launchd `com.teerth.tidy`, log `~/Library/Logs/tidy.log`) runs. It has already moved the *certain* cases (screenshots, installers for apps he has, exact duplicates, and coursework whose course is unambiguous, which goes to `~/Desktop/F&M Notes/<COURSE>/_Inbox/`). It wrote everything else to `~/.tidy/pending.md` and made a Todoist task. Your job is to finish the rest with him. Keep it quick.

## Steps

1. Run `~/bin/tidy --no-todoist` first. This picks up anything new since Sunday and refreshes `~/.tidy/pending.md`. Then read `~/.tidy/pending.md`.
2. **Coursework `_Inbox/` folders.** For each `~/Desktop/F&M Notes/*/_Inbox/` that has files, file them into that course's layout: `Lectures/NN Topic/`, `Labs/Lab N/`, `Homework/HWN/` (DSC 215 uses top-level `HW<n>/`), `Exams/`, `Textbook/`, plus `_versions/` for older non-identical copies.
   - Work out *which* lab, homework or lecture from evidence: the Canvas "Readings and Slides" pages (`~/bin/canvas raw /api/v1/courses/<id>/pages/<url>`), the Java or class names the handout PDF mentions, and the title inside an `.Rmd`.
   - If the evidence doesn't settle it, ask. Never rename `Study Guides/`, `DSC 215/HW<n>/` or `MAT 230/Daily HW/`, because tools depend on those names.
3. **Pending items.** Look at each one before asking: open PDFs with PyMuPDF (`import fitz`), view images, read text heads.
   - Then ask him in batches with AskUserQuestion: 2 to 4 questions per batch, one-line previews, and your best guess first.
   - **Never file by topic similarity.** One example: a flight-home PDF is *not* spring-break material.
4. Move everything with `~/bin/tidy mv SRC DSTDIR "reason"`. It never overwrites and it logs to `~/.tidy/moves.log`. Never use `rm`.
5. If the report shows the review pile `~/_Review Before Delete/` is 14+ days old, remind him to skim and trash it. Never trash it yourself.
6. When done, run `~/bin/tidy` (without flags), which closes the Todoist task if nothing is left. Then tell him in 3 to 5 lines what went where.

## Where things live (as of 2026-10)

- Coursework: `~/Desktop/F&M Notes/<COURSE>/`. Past semesters: `F&M Notes/_Past Semesters (2025-26)/`. Admin: `F&M Notes/_Admin/`.
- Client work: one folder per client on the Desktop. The vault is in there too.
- Code projects: `~/Projects/`. Personal, photos, finance, career, travel: `~/Downloads/<emoji folder>/`. Screenshots: `~/Pictures/Screenshots/YYYY-MM/`.
- `~/Desktop/power-hour/` must not move, because Palmier links it by absolute path.
- Course codes and extension rules: `~/.tidy/config.json`. **Update it each semester**, otherwise new course files stop auto-filing.
