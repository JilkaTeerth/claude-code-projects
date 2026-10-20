# Student quiz results, quiz-5.3 (sha256 931b18b7...), graded against the locked key
Rules: taught and correct = 1 (Q4: 0/1/2); half taught (a step filled from prior knowledge) = 0.5;
NOT TAUGHT = 0 even if the guess was right; a misconception the video planted = 0.
Blind labels: P = v2, Q = 3b1b ch.7, R = v3, S = v1 (blind-key.json).

| Q | P (v2) | Q (3b1b) | R (v3) | S (v1) | notes |
|---|---|---|---|---|---|
| 1 rank to nullity | 0.5 | 0 | 1 | 1 | P: "rank" never named. Q: no computation in 3b1b |
| 2 4x6, 4 pivots | 1 | 0 | 1 | 1 | |
| 3 can it be onto | 0 | 1 | 0.5 | 1 | R: "onto" never defined; S: 5.4 teaser defined it |
| 4 WHY (0-2) | 1 | 0 | 2 | 1 | R: "which stick + where inside it". P/S: "crushed or kept" + own pivot argument |
| 5 ker perpendicular? | 0 | 1 | 1 | 0 | P believed TRUE; S said the video pushes toward true |
| 6 every direction crushed or unchanged? | 0 | 1 | 1 | 0.5 | P answered TRUE from v2's slogan: the misconception transmitted |
| 7 all solutions of Ax=b | 0 | 0 | 1 | 0 | |
| 8 bases for ker and range | 0.5 | 0.5 | 0.5 | 0.5 | NOBODY was taught how to find kernel basis vectors |
| 9 differentiation P3 to P2 | 0 | 0.5 | 1 | 0.5 | P got range dim 2 (wrong) |
| 10 which b are solvable | 0 | 1 | 1 | 0.5 | |
| **total /11** | **3** | **5** | **10** | **6** | |

Engagement (student-rated): P 8, Q 7, R 8, S 7.

Caveats, stated up front:
- The quiz targets the professor's exam (computation). 3b1b says on purpose that it doesn't teach computing, so its 5/11 is a mismatch of goals, not a bad video.
- **v3 was written AFTER this quiz, by the same author.** It covers Ax=b (Q7) and differentiation (Q9) partly because I knew the quiz asked. Pre-registration stops the quiz changing; it doesn't stop the video teaching to it. Fix: a held-out quiz written by someone who hasn't seen v3.
- Student agents are role-played; LLMs know linear algebra. The "cite what taught you" rule limits this, but doesn't remove it.

Fixes for v3 that the student found (not my rubric):
1. "One solution, plus anything in the kernel" was heard as "a unique solution". Say "one particular solution".
2. Never says "domain"; V and "n, the number of columns" are never linked.
3. Kernel Method missing: dim(ker) is taught, finding the actual kernel vectors isn't. Every student lost Q8.
4. "onto" never defined (Q3 half marks).
5. "Sticks are parallel to the kernel" is only inferred from a picture. Say it and show it.
6. 3D sheets case is said, not shown.
7. The upright burger primes "kernel = straight down" until the trap beat. Lean the sticks earlier.
