# Multi agent study PDFs

A semester's worth of worked solutions built from a textbook whose PDF text layer was broken.

## The problem

Text extraction silently corrupted the maths: a matrix with three negative entries came out as `10 4 21 0 4 3 5 1 12`. Copying that would have produced a study document full of wrong maths, found only in a test.

Fix: crop every problem as an image instead of transcribing it. Correct by construction, not by proofreading.

## The workflow

- 5 solver agents split by chapter, each feeding an **independent auditor** that re read the problem images, recomputed every answer and checked against the textbook's answer key.
- 10 agents, 0 errors left, 1.82M subagent tokens.
- All 5 groups came back "repaired", not "clean". Catches included a self contradictory solution and three places where "row reducing gives the answer" was standing in for the entire working.
- Every output page was rendered and looked at, which took the PDF from 99 pages to 80 with no near empty pages.

The PDFs aren't here because they reproduce copyrighted textbook content.
