# MAT 230 Quiz: Section 5.3, The Dimension Theorem

Andrilli and Hecker, Elementary Linear Algebra, 4th ed. Show your work. Use the Kernel Method and the Range Method by name where they apply, and cite theorem numbers (Theorem 5.8, 5.9, 5.10, Corollary 5.11) when you use them. 100 points total.

---

## Question 1 (12 points)

Let L: R^5 -> R^3 be given by L(X) = AX, where

```
A = [  1  -2   3   1   4 ]
    [  2  -4   7   0   9 ]
    [ -1   2  -1  -5  -2 ]
```

(a) Use the Kernel Method to find a basis for ker(L).

(b) Use the Range Method to find a basis for range(L).

(c) Verify that dim(ker(L)) + dim(range(L)) = dim(R^5). Is L onto? Explain.

---

## Question 2 (10 points)

Let L: R^3 -> R^3 be given by L(X) = AX, where

```
A = [ 1   2   0 ]
    [ 2  -1   5 ]
    [ 3   1   5 ]
```

(a) Is [2, -1, -1] in ker(L)? Why or why not?

(b) Is [1, 1, 1] in ker(L)? Why or why not?

(c) Is [4, -3, 1] in range(L)? If so, find a vector X with L(X) = [4, -3, 1].

(d) Is [1, 2, 4] in range(L)? Why or why not?

---

## Question 3 (10 points)

Answer each part using the Dimension Theorem (Theorem 5.10). Justify briefly.

(a) L: R^7 -> R^4 is linear and dim(ker(L)) = 4. Find dim(range(L)). Is L onto?

(b) L: M_23 -> P_3 is linear and onto. Find dim(ker(L)).

(c) Can there be a linear transformation L: P_4 -> R^3 with dim(ker(L)) = 1? What is the smallest possible value of dim(ker(L))?

(d) Can a linear transformation L: R^5 -> R^6 be onto?

(e) L: P_2 -> M_22 is linear, and its matrix with respect to some ordered bases is a 4 x 3 matrix of rank 3. Find ker(L).

---

## Question 4 (10 points)

Let L: P_3 -> R^2 be given by L(p) = [p(2), p'(2)].

(a) Is x^3 - 3x^2 + 4 in ker(L)? Is x^2 - x - 2 in ker(L)? Explain.

(b) Find a basis for ker(L).

(c) Find range(L), and verify the Dimension Theorem for L.

---

## Question 5 (10 points)

Let B = [ 0 1 ; 0 0 ] (rows separated by semicolons) and define L: M_22 -> M_22 by L(A) = AB - BA.

(a) Compute L(A) for a general A = [ a b ; c d ].

(b) Find a basis for ker(L). Describe ker(L) in words.

(c) Find a basis for range(L).

(d) Verify that dim(ker(L)) + dim(range(L)) = dim(M_22).

---

## Question 6 (10 points)

Let

```
A = [ 2  -1   3   0   4 ]
    [ 1   1   0   3  -1 ]
    [ 4   1   3   6   2 ]
```

(a) Find rank(A).

(b) Without row reducing A^T, state rank(A^T) and justify using Corollary 5.11.

(c) Let L: R^5 -> R^3 be L(X) = AX and M: R^3 -> R^5 be M(Y) = A^T Y. Find dim(ker(L)), dim(range(L)), dim(ker(M)) and dim(range(M)).

(d) Find a basis for ker(M).

(e) A student says "since rank(A) = rank(A^T), the row space of A equals the column space of A." What is wrong with this?

---

## Question 7 (10 points)

For each real number k, let L: R^3 -> R^3 be given by L(X) = AX, where

```
A = [ 1     2    -1 ]
    [ 2     5     k ]
    [ 3   k+5     1 ]
```

(a) Find all values of k for which dim(ker(L)) = 1.

(b) Is there any value of k for which dim(ker(L)) >= 2? Explain.

(c) For k = 2, find a basis for ker(L) and a basis for range(L).

(d) For which values of k is range(L) = R^3?

---

## Question 8 (14 points)

True or False. Give a brief reason for each (a counterexample for False, a theorem or argument for True).

(a) If L: R^6 -> R^4 is linear, then dim(ker(L)) >= 2.

(b) If L: V -> W is linear, then ker(L) is a subspace of the codomain W.

(c) If L: P_3 -> M_22 is linear and dim(range(L)) = 4, then ker(L) = {0}.

(d) If L(X) = AX and B is the reduced row echelon form of A, then the pivot columns of B form a basis for range(L).

(e) If A is a 3 x 5 matrix, then the row space of A and the column space of A have the same dimension.

(f) If L: V -> W is linear and L(u) = L(v), then u - v is in ker(L).

(g) If L: V -> W is linear with dim(V) = 5 and dim(W) = 8, then the Dimension Theorem implies ker(L) = {0_V}.

---

## Question 9 (8 points)

(a) Let L: R^n -> R^m be given by L(X) = AX. Using the Kernel Method and the Range Method, explain why dim(ker(L)) + dim(range(L)) = n. Your explanation should refer to pivot and nonpivot columns.

(b) Now let L: V -> W be any linear transformation with dim(V) = n finite. Suppose {k_1, ..., k_s} is a basis for ker(L), extended to a basis {k_1, ..., k_s, q_1, ..., q_t} for V. Explain why {L(q_1), ..., L(q_t)} spans range(L) and why it is linearly independent, and conclude the Dimension Theorem.

---

## Question 10 (6 points)

(a) Give an explicit 4 x 4 matrix A such that the operator L: R^4 -> R^4, L(X) = AX, satisfies ker(L) = range(L). Verify your answer.

(b) Explain why no linear operator L: R^3 -> R^3 can satisfy ker(L) = range(L).

---
---

# Answer Key

All numeric answers below were checked with sympy (rref, nullspace, columnspace, rank, det).

## Answer 1

RREF of A:

```
B = [ 1  -2   0   7   1 ]
    [ 0   0   1  -2   1 ]
    [ 0   0   0   0   0 ]
```

Pivots in columns 1 and 3. Independent variables x2, x4, x5. From BX = O: x1 = 2x2 - 7x4 - x5, x3 = 2x4 - x5.

(a) Kernel Method, setting each independent variable to 1 in turn:
- x2 = 1: v1 = [2, 1, 0, 0, 0]
- x4 = 1: v2 = [-7, 0, 2, 1, 0]
- x5 = 1: v3 = [-1, 0, -1, 0, 1]

Basis for ker(L): {[2,1,0,0,0], [-7,0,2,1,0], [-1,0,-1,0,1]}, so dim(ker(L)) = 3.

(b) Range Method: take columns 1 and 3 of A (not of B). Basis for range(L): {[1, 2, -1], [3, 7, -1]}, so dim(range(L)) = 2 = rank(A).

(c) 3 + 2 = 5 = dim(R^5). L is not onto, since dim(range(L)) = 2 < 3 = dim(R^3); range(L) is a plane through the origin in R^3.

## Answer 2

RREF of A is [ 1 0 2 ; 0 1 -1 ; 0 0 0 ], so ker(L) = span{[-2, 1, 1]} and rank(A) = 2. Also row 3 of A = row 1 + row 2, so every image [y1, y2, y3] satisfies y3 = y1 + y2; range(L) = {[y1, y2, y3] : y3 = y1 + y2}.

(a) Yes. A[2, -1, -1] = [2 - 2 + 0, 4 + 1 - 5, 6 - 1 - 5] = [0, 0, 0]. (It is -1 times the kernel basis vector [-2, 1, 1].)

(b) No. A[1, 1, 1] = [3, 6, 9], which is not the zero vector.

(c) Yes. Row reducing [A | 4, -3, 1] gives [ 1 0 2 | -2/5 ; 0 1 -1 | 11/5 ; 0 0 0 | 0 ], which is consistent. Taking x3 = 0: X = [-2/5, 11/5, 0], and A X = [4, -3, 1]. (General solution X = [-2/5, 11/5, 0] + t[-2, 1, 1].) Quick check: 4 + (-3) = 1.

(d) No. Row reducing [A | 1, 2, 4] gives a pivot in the augmented column (an inconsistent row 0 0 0 | nonzero). Equivalently 1 + 2 = 3, not 4.

## Answer 3

(a) dim(range(L)) = 7 - 4 = 3. Not onto, since 3 < 4 = dim(R^4).

(b) dim(M_23) = 6 and range(L) = P_3 has dimension 4, so dim(ker(L)) = 6 - 4 = 2.

(c) No. dim(P_4) = 5, so dim(ker(L)) = 1 would force dim(range(L)) = 4, but range(L) is a subspace of R^3, so dim(range(L)) <= 3. The smallest possible value is dim(ker(L)) = 5 - 3 = 2.

(d) No. dim(range(L)) = 5 - dim(ker(L)) <= 5 < 6.

(e) By Theorem 5.9 (any bases), dim(range(L)) = rank = 3, so dim(ker(L)) = dim(P_2) - 3 = 3 - 3 = 0. Hence ker(L) = {0} (the zero polynomial).

## Answer 4

Write p = ax^3 + bx^2 + cx + d. Then L(p) = [8a + 4b + 2c + d, 12a + 4b + c].

(a) For x^3 - 3x^2 + 4: p(2) = 8 - 12 + 4 = 0 and p'(x) = 3x^2 - 6x, so p'(2) = 0. Yes, it is in ker(L). (It factors as (x + 1)(x - 2)^2.)
For x^2 - x - 2: p(2) = 0 but p'(2) = 2(2) - 1 = 3. L(p) = [0, 3], so it is not in ker(L).

(b) p is in ker(L) exactly when 2 is a root of p of multiplicity at least 2, i.e. p = (x - 2)^2 (mx + n). Basis: {(x - 2)^2, x(x - 2)^2} = {x^2 - 4x + 4, x^3 - 4x^2 + 4x}. dim(ker(L)) = 2. (Via the Kernel Method on the matrix [ 8 4 2 1 ; 12 4 1 0 ] in the variables a, b, c, d, you get an equivalent basis such as {x^3 - 4x^2 + 4x, x^3 - 3x^2 + 4}; any basis of the same span is correct.)

(c) L(1) = [1, 0] and L(x) = [2, 1] are linearly independent, so range(L) = R^2 and dim(range(L)) = 2. Check: 2 + 2 = 4 = dim(P_3).

## Answer 5

(a) AB = [ 0 a ; 0 c ] and BA = [ c d ; 0 0 ], so L(A) = [ -c  a - d ; 0  c ].

(b) L(A) = O iff c = 0 and a = d. So ker(L) = { [ a b ; 0 a ] : a, b in R }, with basis { [ 1 0 ; 0 1 ], [ 0 1 ; 0 0 ] }. In words: ker(L) is the set of 2 x 2 matrices that commute with B. dim(ker(L)) = 2.

(c) range(L) = { [ -c  t ; 0  c ] : c, t in R } (t = a - d can be anything). Basis: { [ 0 1 ; 0 0 ], [ -1 0 ; 0 1 ] }. dim(range(L)) = 2.

(d) 2 + 2 = 4 = dim(M_22).

## Answer 6

(a) RREF of A is [ 1 0 1 1 1 ; 0 1 -1 2 -2 ; 0 0 0 0 0 ], so rank(A) = 2. (Row 3 = row 1 + 2 row 2.)

(b) rank(A^T) = 2 by Corollary 5.11, which says rank(A) = rank(A^T) for any matrix.

(c) By Theorem 5.9: dim(range(L)) = rank(A) = 2 and dim(ker(L)) = 5 - 2 = 3. M has matrix A^T (5 x 3), so dim(range(M)) = rank(A^T) = 2 and dim(ker(M)) = 3 - 2 = 1.

(d) ker(M) = {Y : A^T Y = 0}. Since row 1 + 2 row 2 - row 3 = 0, Y = [1, 2, -1] works: A^T [1, 2, -1] = [2 + 2 - 4, -1 + 2 - 1, 3 + 0 - 3, 0 + 6 - 6, 4 - 2 - 2] = 0. As dim(ker(M)) = 1, basis {[1, 2, -1]}.

(e) Corollary 5.11 only says the dimensions agree. Here the row space of A is a subspace of R^5 and the column space of A is a subspace of R^3; they contain vectors of different sizes, so they cannot be equal.

## Answer 7

(a) |A| = 1(5 - k(k + 5)) - 2(2 - 3k) - 1(2(k + 5) - 15) = -k^2 - k + 6 = -(k - 2)(k + 3). dim(ker(L)) = 1 requires rank(A) = 2, which happens exactly when |A| = 0: k = 2 or k = -3. (sympy: rank 2 at both values.)

(b) No. Rows 1 and 2, [1, 2, -1] and [2, 5, k], are never multiples of each other (the 2 x 2 minor 1(5) - 2(2) = 1 is nonzero), so rank(A) >= 2 for every k, and dim(ker(L)) = 3 - rank(A) <= 1.

(c) k = 2: A = [ 1 2 -1 ; 2 5 2 ; 3 7 1 ], RREF [ 1 0 -9 ; 0 1 4 ; 0 0 0 ]. Independent variable x3: x1 = 9x3, x2 = -4x3. Basis for ker(L): {[9, -4, 1]}. Pivot columns 1 and 2, so basis for range(L): {[1, 2, 3], [2, 5, 7]}. Check 1 + 2 = 3.

(d) range(L) = R^3 iff rank(A) = 3 iff |A| is nonzero iff k is not 2 and not -3.

## Answer 8

(a) True. dim(range(L)) <= 4, so dim(ker(L)) = 6 - dim(range(L)) >= 2.

(b) False. ker(L) is a subspace of the domain V (Theorem 5.8). Example: L: R^3 -> R^2, L([x, y, z]) = [x, y]; ker(L) = span{e3} lives in R^3, not R^2.

(c) True. dim(P_3) = 4, so dim(ker(L)) = 4 - 4 = 0, so ker(L) = {0}.

(d) False. The Range Method uses the columns of A corresponding to pivot columns of B. Counterexample: A = [ 1 2 ; 1 2 ], B = [ 1 2 ; 0 0 ]. range(L) = span{[1, 1]}, but the pivot column [1, 0] of B is not even in range(L).

(e) True. By Corollary 5.11, dim(row space of A) = rank(A) = rank(A^T) = dim(column space of A). (They are not equal as sets: one is in R^5, the other in R^3.)

(f) True. L(u - v) = L(u) - L(v) = 0_W.

(g) False. The Dimension Theorem only gives dim(ker(L)) + dim(range(L)) = 5. The zero transformation L(v) = 0_W has ker(L) = V, of dimension 5.

## Answer 9

(a) Let B be the RREF of A. The Kernel Method produces one basis vector of ker(L) for each independent variable of BX = O, and independent variables correspond exactly to the nonpivot columns of B. The Range Method produces one basis vector of range(L) for each pivot column (the matching columns of A, which span range(L) since range(L) = span{columns of A} and are independent by the Independence Test Method). Every one of the n columns is either a pivot column or a nonpivot column, never both, so dim(ker(L)) + dim(range(L)) = (# nonpivot columns) + (# pivot columns) = n. This is Theorem 5.9 part (3), with dim(range(L)) = rank(A) and dim(ker(L)) = n - rank(A).

(b) Spanning: any w in range(L) is w = L(v) for some v in V. Write v = d_1 k_1 + ... + d_s k_s + b_1 q_1 + ... + b_t q_t. Since each L(k_i) = 0_W, w = L(v) = b_1 L(q_1) + ... + b_t L(q_t). So {L(q_1), ..., L(q_t)} spans range(L).

Independence: suppose c_1 L(q_1) + ... + c_t L(q_t) = 0_W. By linearity L(c_1 q_1 + ... + c_t q_t) = 0_W, so c_1 q_1 + ... + c_t q_t is in ker(L), hence equals d_1 k_1 + ... + d_s k_s for some scalars d_i. Moving everything to one side gives a linear combination of the basis {k_1, ..., k_s, q_1, ..., q_t} equal to 0_V, so every c_i (and every d_i) is 0.

So {L(q_1), ..., L(q_t)} is a basis for range(L), dim(range(L)) = t, and dim(ker(L)) + dim(range(L)) = s + t = dim(V). This is Theorem 5.10. (Key idea: the kernel vectors are "used up" by mapping to 0, and the leftover basis vectors map injectively onto a basis of the range.)

## Answer 10

(a) One answer:

```
A = [ 0 0 1 0 ]
    [ 0 0 0 1 ]
    [ 0 0 0 0 ]
    [ 0 0 0 0 ]
```

L([x1, x2, x3, x4]) = [x3, x4, 0, 0]. ker(L) = {x3 = x4 = 0} = span{e1, e2}. range(L) = span{columns of A} = span{e1, e2} (Range Method: pivot columns 3 and 4 of A are e1 and e2). So ker(L) = range(L). (Also A^2 = O, consistent with range(L) being inside ker(L).) Any A with A^2 = O and rank 2 works.

(b) If ker(L) = range(L) then dim(ker(L)) = dim(range(L)) = r, and the Dimension Theorem gives 2r = 3, which is impossible for an integer r. (In general this can only happen when the dimension of the domain is even.)
