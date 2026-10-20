# Squash academy fee system (client work, anonymised)

A squash academy with about 124 students tracked fees and attendance in one 468 column Excel sheet. Staff found unpaid fees by eyeballing it.

## The audit

- The "paid until" column had about 26 free text formats plus blanks.
- The fee period column had 10 inconsistent codes.
- The expected fee column was blank for 45 of 124 students and out of date for 21 more.

## Decisions

- A student's real plan is what they actually pay most often, not the stale recorded total.
- Fees are class packs that carry over, not calendar months. Balance = classes bought minus classes taken. You only owe when you've taken more than you bought, like a gym.

## What was delivered

- A self updating workbook with an auto ranked "fees due" sheet and a flag for students who are attending but not paying.
- A recommendations doc with an LLM council verdict, and a slide deck for parents.
- 10 one page fee statements with a full month by month ledger.

## Verification

Attendance and payment totals were re derived **three times by separate checker agents**, and all three passed before any statement went out.

No files here: it's student data.
