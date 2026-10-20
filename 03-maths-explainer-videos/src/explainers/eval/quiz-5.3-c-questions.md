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
