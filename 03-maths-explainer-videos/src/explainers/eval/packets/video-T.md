# Video T

Images: video-T.png (storyboard stills (planned frames; not a finished video)).

## Narration (everything the viewer hears)

Okay. Your roommate built a machine. The Pancake Three Thousand. Burger goes in... burger pancake comes out. Basketball goes in... sad orange circle. Then he puts in his phone. Now he owns a very expensive coaster.

So I hand you a pancake. Which burger made this? You can't tell. A tiny burger, a giant tower burger, a burger with extra pickles... same pancake. The machine forgets something. But what?

Here's the trick. Think of the burger as skinny vertical sticks, like spaghetti standing up. The press squishes each whole stick into one single dot. So the pancake is a map of sticks. Every dot was a stick.

Now we can count. How many directions to point at a stick? Two. Left right, front back. That's the pancake. How much room inside one stick? One. Up down. Two plus one is three. Every direction the burger had. Not luck. The burger is literally made of sticks.

Mathematicians have names for all this. The press is a linear transformation, L. Everything you can feed it is the domain, V. The stick that lands exactly on zero is the kernel. Some books call it the null space: everything that becomes null. And every other stick is that same kernel, slid over. Parallel copies. The pancake, everything that comes out, is the range. So: the dimension of the kernel, plus the dimension of the range, equals the dimension of V. Inside a stick, plus how many sticks.

Careful, though. A real press squishes straight down. Most transformations don't. The sticks can lean. And the other directions don't come out untouched. They get stretched and turned. What's conserved isn't any one direction. It's the count.

Let's watch a real one. This matrix, one, minus one, two, minus two, is a machine for the flat plane. First, slice the plane into its sticks. They're these slanted red lines. Now press. Every red line collapses into one yellow dot. And all the dots line up on a single line. That's the range.

Check the count. Kernel: the line through one, one. Dimension one. Range: the line through one, two. Dimension one. One plus one is two. And they're not at right angles. They don't have to be.

In 3D, same story. Squash space onto a plane: the sticks are lines. Two plus one. Squash it onto a line: the sticks become flat sheets. One plus two. The pieces change shape. The count never breaks.

And here's why you care. Solving A x equals b is the pancake question, backwards. Which inputs land on b? If b is off the pancake: none. No solution. If b is on it: a whole stick lands there. So find one particular solution, call it x zero, and every solution is x zero plus something from the kernel.

On the test, skip the pictures. Row reduce. Pivots give the rank, the dimension of the range. The range is spanned by the pivot columns of the original A, not the reduced one. Free variables give the dimension of the kernel. Together: n, the number of columns, which is the dimension of the domain.

And to get the actual kernel vectors: set one free variable to one, the others to zero, and solve. Each free variable gives you one basis vector. Here, two free variables... two vectors. The kernel's a plane.

It even works without arrows. Differentiation, from P three to P two. What gets crushed? Constants. Dimension one. What comes out? Every quadratic. Dimension three. One plus three is four. Exactly P three.

One last thing, because it's next week's whole lesson. If the kernel is just the zero vector, every stick is a single dot: L is one to one. If the range is everything, L is onto.

So next time a scary transformation shows up on your exam... ask the pancake question. How big is one stick? And how many sticks are there?
