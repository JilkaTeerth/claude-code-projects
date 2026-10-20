# MAT 230 Midterm Quiz: Section 5.3, The Dimension Theorem

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
