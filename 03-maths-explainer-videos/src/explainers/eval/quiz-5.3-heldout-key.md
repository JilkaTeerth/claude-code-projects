# MAT 230 Midterm Quiz: Section 5.3, The Dimension Theorem (WITH ANSWER KEY)

Andrilli and Hecker, Elementary Linear Algebra, 4th ed. Time: 50 minutes. Show your work. No calculators.
Notation follows the text: ker(L), range(L), rank(A), Theorem 5.9, Theorem 5.10 (Dimension Theorem), Kernel Method, Range Method. Vectors in R^n may be written as rows.

---

**Question 1 (8 points).** Let L: R^3 → R^3 be given by L(X) = AX, where

```
A = [ 2  -1  3 ]
    [ 1   1  0 ]
    [ 3   0  3 ]
```

(a) Is [1, 1, -1] in ker(L)? Why or why not?
(b) Is [-2, 2, 2] in ker(L)? Why or why not?
(c) Is [1, 2, 3] in range(L)? Why or why not?
(d) Is [1, 2, 4] in range(L)? Why or why not?

---

**Question 2 (12 points).** Let L: R^3 → R^3 be given by L(X) = AX, where

```
A = [  1  -2  3 ]
    [  2  -3  8 ]
    [ -1   4  1 ]
```

Use the Kernel Method to find a basis for ker(L) and the Range Method to find a basis for range(L). Verify that dim(ker(L)) + dim(range(L)) = dim(R^3).

---

**Question 3 (14 points).** Let L: R^5 → R^4 be given by L(X) = AX, where

```
A = [  1   2  -1  0   3 ]
    [  2   4   1  3   0 ]
    [ -1  -2   2  1  -5 ]
    [  3   6   0  3   3 ]
```

(a) Find a basis for ker(L).
(b) Find a basis for range(L).
(c) State rank(A), and verify that your answers agree with Theorem 5.9.

---

**Question 4 (10 points).** Answer each part using Theorem 5.9 or the Dimension Theorem. Give a one-line justification for each.

(a) L: R^7 → R^5 is given by L(X) = AX with rank(A) = 4. Find dim(ker(L)) and dim(range(L)).
(b) L: P_4 → M_23 is a linear transformation with dim(ker(L)) = 2. Find dim(range(L)).
(c) L: M_33 → R^4 is a linear transformation. What is the smallest possible value of dim(ker(L))?
(d) L: R^3 → R^8 is a linear transformation. What is the largest possible value of dim(range(L))?

---

**Question 5 (10 points).** Let L: P_3 → R^2 be given by L(p) = [p(2), p'(2)].

(a) Find a basis for ker(L).
(b) Find range(L) and dim(range(L)).
(c) Verify that dim(ker(L)) + dim(range(L)) = dim(P_3).

---

**Question 6 (10 points).** Let

```
B = [ 1  2 ]
    [ 2  4 ]
```

and let L: M_22 → M_22 be given by L(A) = AB.

(a) Find a basis for ker(L).
(b) Find a basis for range(L).
(c) Verify the Dimension Theorem for L.

---

**Question 7 (10 points).** Let L: R^3 → R^3 be given by L(X) = AX, where

```
A = [ 1  2  -1 ]
    [ 2  5   1 ]
    [ 4  9   k ]
```

and k is a real number.

(a) Find the value of k for which ker(L) ≠ {0}.
(b) For that value of k, find a basis for ker(L) and a basis for range(L).
(c) For every other value of k, what are ker(L) and range(L)?

---

**Question 8 (8 points).** Let A be a 4 × 6 matrix, and let L: R^6 → R^4 be given by L(X) = AX. Suppose dim(ker(L)) = 3.

(a) Find rank(A) and dim(range(L)).
(b) Find rank(A^T).
(c) Let M: R^4 → R^6 be given by M(Y) = A^T Y. Find dim(range(M)) and dim(ker(M)).
(d) Is range(L) = R^4? Explain.

---

**Question 9 (12 points).** True or False. Give a brief reason or counterexample for each.

(a) If L: R^4 → R^6 is a linear transformation, then dim(range(L)) ≤ 4.
(b) If L: V → W is a linear transformation, then ker(L) is a subspace of W.
(c) If A is a 3 × 7 matrix and L(X) = AX, then dim(ker(L)) ≥ 4.
(d) If L(X) = AX and B is the reduced row echelon form of A, then the pivot columns of B form a basis for range(L).
(e) If A is a 4 × 4 matrix with rank(A) = 4 and L(X) = AX, then ker(L) = {0}.
(f) If A is a square matrix, then the row space of A equals the column space of A.

---

**Question 10 (6 points).** Explain why.

(a) Explain why there is no linear operator L: R^5 → R^5 with ker(L) = range(L).
(b) Explain why every linear transformation L: R^6 → R^4 has a nonzero vector in its kernel.

---
---

# Answer Key

All numeric answers below were checked with sympy (RREF, rank, nullspace, consistency of augmented systems). Any basis that spans the same subspace with the correct number of vectors earns full credit; the bases shown are the ones the Kernel Method and Range Method produce.

## Question 1

RREF of A is

```
B = [ 1  0   1 ]
    [ 0  1  -1 ]
    [ 0  0   0 ]
```

(a) No. A[1, 1, -1] = [-2, 2, 0] ≠ 0.
(b) Yes. A[-2, 2, 2] = [0, 0, 0]. (Equivalently, [-2, 2, 2] = 2[-1, 1, 1], and the Kernel Method gives ker(L) = span{[-1, 1, 1]}.)
(c) Yes. The system AX = [1, 2, 3] is consistent: the augmented matrix [A | 1,2,3] has the same rank (2) as A. For example X = [1, 1, 0] works: A[1, 1, 0] = [1, 2, 3].
(d) No. The augmented matrix [A | 1,2,4] has rank 3 > rank(A) = 2, so the system is inconsistent. (Range Method: range(L) = span{[2, 1, 3], [-1, 1, 0]}, which is the plane x + y - z = 0, and 1 + 2 - 4 ≠ 0.)

## Question 2

RREF:

```
B = [ 1  0  7 ]
    [ 0  1  2 ]
    [ 0  0  0 ]
```

Independent variable x3. Setting x3 = 1 gives x1 = -7, x2 = -2.

- Basis for ker(L): {[-7, -2, 1]}, so dim(ker(L)) = 1.
- Pivots in columns 1 and 2, so by the Range Method a basis for range(L) is {[1, 2, -1], [-2, -3, 4]} (columns 1 and 2 of A, not of B), so dim(range(L)) = 2.
- Check: 1 + 2 = 3 = dim(R^3).

## Question 3

RREF:

```
B = [ 1  2  0  1   1 ]
    [ 0  0  1  1  -2 ]
    [ 0  0  0  0   0 ]
    [ 0  0  0  0   0 ]
```

Pivots in columns 1 and 3; independent variables x2, x4, x5, with x1 = -2x2 - x4 - x5 and x3 = -x4 + 2x5.

(a) Kernel Method:
- x2 = 1, x4 = x5 = 0: v1 = [-2, 1, 0, 0, 0]
- x4 = 1, x2 = x5 = 0: v2 = [-1, 0, -1, 1, 0]
- x5 = 1, x2 = x4 = 0: v3 = [-1, 0, 2, 0, 1]

Basis for ker(L): {v1, v2, v3}; dim(ker(L)) = 3.

(b) Range Method: columns 1 and 3 of A. Basis for range(L): {[1, 2, -1, 3], [-1, 1, 2, 0]}; dim(range(L)) = 2.

(c) rank(A) = 2 (two nonzero rows in B). Theorem 5.9: dim(range(L)) = rank(A) = 2, dim(ker(L)) = n - rank(A) = 5 - 2 = 3, and 3 + 2 = 5 = dim(R^5). Note range(L) is a 2-dimensional subspace of R^4, so L is not onto R^4.

## Question 4

(a) dim(range(L)) = rank(A) = 4; dim(ker(L)) = 7 - 4 = 3 (Theorem 5.9).
(b) dim(P_4) = 5, so dim(range(L)) = 5 - 2 = 3 (Dimension Theorem).
(c) dim(M_33) = 9, and range(L) is a subspace of R^4 so dim(range(L)) ≤ 4. Hence dim(ker(L)) = 9 - dim(range(L)) ≥ 5. Smallest possible value: 5.
(d) dim(range(L)) = 3 - dim(ker(L)) ≤ 3 (and 3 is also ≤ 8). Largest possible value: 3 (attained, e.g., by L([x1,x2,x3]) = [x1,x2,x3,0,0,0,0,0]).

## Question 5

Write p = ax^3 + bx^2 + cx + d. Then p(2) = 8a + 4b + 2c + d and p'(2) = 12a + 4b + c, so in coordinates (a, b, c, d) L has matrix

```
[  8  4  2  1 ]   RREF   [ 1  0  -1/4  -1/4 ]
[ 12  4  1  0 ]   --->   [ 0  1    1    3/4 ]
```

(a) Independent variables c, d. Kernel Method (scaled by 4 to clear fractions) gives ker(L) basis {x^3 - 4x^2 + 4x, x^3 - 3x^2 + 4}. An equivalent, nicer basis is {(x - 2)^2, x(x - 2)^2} = {x^2 - 4x + 4, x^3 - 4x^2 + 4x}: these are exactly the cubics with a double root at 2. dim(ker(L)) = 2.
(b) rank of the matrix is 2, so dim(range(L)) = 2 and range(L) = R^2. (Directly: L(1) = [1, 0] and L(x - 2) = [0, 1].)
(c) 2 + 2 = 4 = dim(P_3).

## Question 6

For A = [[a, b], [c, d]], AB = [[a + 2b, 2a + 4b], [c + 2d, 2c + 4d]]. Using the standard basis of M_22 (coordinates a, b, c, d), the matrix of L is

```
[ 1  2  0  0 ]   RREF   [ 1  2  0  0 ]
[ 2  4  0  0 ]   --->   [ 0  0  1  2 ]
[ 0  0  1  2 ]          [ 0  0  0  0 ]
[ 0  0  2  4 ]          [ 0  0  0  0 ]
```

(a) Independent variables b, d. ker(L) basis:

```
{ [ -2  1 ]   [  0  0 ] }
{ [  0  0 ] , [ -2  1 ] }
```

(the matrices each of whose rows is a multiple of [-2, 1]). dim(ker(L)) = 2.

(b) Pivot columns 1 and 3, giving range(L) basis

```
{ [ 1  2 ]   [ 0  0 ] }
{ [ 0  0 ] , [ 1  2 ] }
```

(the matrices each of whose rows is a multiple of [1, 2]). dim(range(L)) = 2.

(c) 2 + 2 = 4 = dim(M_22).

## Question 7

(a) |A| = k + 1, so ker(L) ≠ {0} exactly when k = -1. (Equivalently rank(A) < 3 iff k = -1.)

(b) With k = -1:

```
B = [ 1  0  -7 ]
    [ 0  1   3 ]
    [ 0  0   0 ]
```

ker(L) basis: {[7, -3, 1]}. range(L) basis (columns 1 and 2 of A): {[1, 2, 4], [2, 5, 9]}. Check: 1 + 2 = 3.

(c) For k ≠ -1, rank(A) = 3, so dim(ker(L)) = 0, ker(L) = {0}, and dim(range(L)) = 3, so range(L) = R^3.

## Question 8

(a) By Theorem 5.9, 3 = dim(ker(L)) = 6 - rank(A), so rank(A) = 3 and dim(range(L)) = 3.
(b) rank(A^T) = rank(A) = 3 (Corollary 5.11).
(c) M has matrix A^T (6 × 4), so dim(range(M)) = rank(A^T) = 3 and dim(ker(M)) = 4 - 3 = 1.
(d) No. range(L) is a 3-dimensional subspace of R^4, so it cannot be all of R^4.

## Question 9

(a) TRUE. dim(range(L)) = 4 - dim(ker(L)) ≤ 4.
(b) FALSE. ker(L) is a subspace of the domain V, not W (Theorem 5.8).
(c) TRUE. rank(A) ≤ 3 (at most 3 pivots), so dim(ker(L)) = 7 - rank(A) ≥ 4.
(d) FALSE. The Range Method takes the columns of A (not of B) corresponding to pivot columns of B. Counterexample: A = [[1], [1]] has B = [[1], [0]], but range(L) = span{[1, 1]} ≠ span{[1, 0]}.
(e) TRUE. dim(ker(L)) = 4 - 4 = 0.
(f) FALSE. Corollary 5.11 says only the dimensions are equal. Counterexample: A = [[0, 1], [0, 0]] has row space span{[0, 1]} but column space span{[1, 0]}.

## Question 10

(a) If ker(L) = range(L), then dim(ker(L)) = dim(range(L)) = d. The Dimension Theorem gives d + d = dim(R^5) = 5, so 2d = 5, which has no integer solution. So no such L exists.
(b) range(L) is a subspace of R^4, so dim(range(L)) ≤ 4. By the Dimension Theorem, dim(ker(L)) = 6 - dim(range(L)) ≥ 6 - 4 = 2 > 0, so ker(L) contains a nonzero vector. (In matrix terms: the 4 × 6 matrix has at most 4 pivots, so at least 2 independent variables in AX = O.)

## Point totals

Q1 8, Q2 12, Q3 14, Q4 10, Q5 10, Q6 10, Q7 10, Q8 8, Q9 12, Q10 6. Total 100.
