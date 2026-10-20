# Pre-registered quiz: 5.3 The Dimension Theorem
Written 2026-10-08 BEFORE v3's script exists, so no video can be written to this quiz.
It is never edited after the first student run. Changes go in a new file (quiz-5.3-b.md).
Sources: Andrilli & Hecker 5.3 (Theorem 5.9, Theorem 5.10, Kernel/Range Methods, Example 2),
plus misconceptions found in our own review (LEARNINGS.md, 2026-10-08).

Q1. L: R^5 -> R^3 is linear and rank(A) = 3. What is dim(ker(L))?
Q2. A is 4x6, and its reduced row echelon form has 4 pivots. Give dim(range(L)) and dim(ker(L)) for L(x) = Ax.
Q3. L: R^3 -> R^3 has dim(ker(L)) = 1. Can L be onto? Why?
Q4. In your own words, explain WHY dim(ker(L)) + dim(range(L)) = dim(V). Not a restatement: a reason.
Q5. True or false: the kernel of a linear transformation is always perpendicular to its range.
Q6. True or false: under a linear transformation, every direction either gets sent to zero or comes out unchanged.
Q7. Ax = b has one solution x0, and dim(ker(A)) = 2. Describe ALL the solutions.
Q8. A = [[1,3],[2,6]]. Give a basis for ker(L) and a basis for range(L).
Q9. L: P3 -> P2 is differentiation. Find dim(ker(L)) and dim(range(L)), and check the theorem.
Q10. For A = [[1,3],[2,6]], which vectors b make Ax = b solvable?

## Key (graders only)
Q1 2 · Q2 4 and 2 · Q3 No: range has dim 2 < 3 · Q4 full marks only for a mechanism: the domain
splits into the kernel's directions plus directions that map one-to-one onto the range (or:
parallel copies of the kernel each collapse to one point of the range; or: extend a kernel basis
to a basis of V, the new vectors' images form a basis of the range). A restatement scores 0.
Q5 False · Q6 False · Q7 x0 + ker(A): a plane of solutions (x0 plus any kernel vector)
Q8 ker: {[-3,1]}, range: {[1,2]} · Q9 ker = constants, dim 1; range = P2, dim 3; 1 + 3 = 4 = dim P3
Q10 b in span{[1,2]}, i.e. b2 = 2 b1
Scoring: 1 point each; Q4 is 0, 1 (partial mechanism) or 2. Out of 11.
