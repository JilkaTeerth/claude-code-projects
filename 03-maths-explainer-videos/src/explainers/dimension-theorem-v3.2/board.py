"""v3 storyboard: the frames the argument rests on. Rendered by explain.py board."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from manim import *
from props import *

config.background_color = BG
config.tex_template = latex_template()
M = np.array([[1, -1], [2, -2]])            # kernel span{[1,1]}, range span{[1,2]}: NOT perpendicular
HUES = [interpolate_color(ManimColor("#ff5a5f"), ManimColor("#ff9f43"), t) for t in np.linspace(0, 1, 7)]

def stick(plane, c, **kw):
    """The line y = x + c, clipped to the plane's [-3, 3] box so it never spills off the grid."""
    x0, x1 = max(-3, -3 - c), min(3, 3 - c)
    return Line(plane.c2p(x0, x0 + c), plane.c2p(x1, x1 + c), **kw)

def caption(s):
    return Text(s, color=GREY_A).scale(0.36).to_edge(DOWN, buff=0.25)


class Board1_question(Scene):
    def construct(self):
        pc = pancake(1.8).shift(DOWN * 1.6)
        burgers = VGroup(burger(0.9), burger(1.6).stretch(1.6, 1), burger(1.2)).arrange(RIGHT, buff=1.0).shift(UP * 1.4)
        pick = Text("+ pickles", color=GREEN_B).scale(0.35).next_to(burgers[2], UP, buff=0.1)
        arrows = VGroup(*[DashedLine(b.get_bottom(), pc.get_top(), color=GREY_B, dash_length=0.12).add_tip(tip_length=0.18) for b in burgers])
        q = Text("which burger made this?", color=KEEP).scale(0.55).next_to(pc, RIGHT, buff=0.6)
        self.add(burgers, pick, arrows, pc, face(pc), q, caption("question: many burgers, one pancake. What does the machine forget?"))


class Board2_sticks(Scene):
    def construct(self):
        b = burger(2.2).set_opacity(0.25).shift(LEFT * 3.2)
        sticks = VGroup(*[Line(b.get_bottom() + [x, 0.05, 0], b.get_top() + [x, -0.05, 0], color=CRUSH, stroke_width=4)
                          for x in np.linspace(-0.95, 0.95, 9)])
        sticks[4].set_stroke(width=8)
        pc = pancake(2.2).shift(RIGHT * 2.8 + DOWN * 0.2)
        dots = VGroup(*[Dot(pc.get_center() + [x * 1.35, 0.02, 0], radius=0.07, color=KEEP) for x in np.linspace(-0.95, 0.95, 9)])
        dots[4].scale(1.8)
        link = Arrow(sticks[4].get_center() + RIGHT * 0.2, dots[4].get_center() + UP * 0.25, color=GREY_B, buff=0.1)
        lab1 = Text("a whole stick...", color=CRUSH).scale(0.42).next_to(b, UP)
        lab2 = Text("...becomes one dot", color=KEEP).scale(0.42).next_to(pc, UP, buff=0.7)
        self.add(b, sticks, pc, dots, link, lab1, lab2, caption("sticks: the pancake is a map of sticks"))


class Board3_count(Scene):
    def construct(self):
        grid = VGroup(*[Dot([x, y * 0.5, 0], radius=0.05, color=KEEP) for x in np.linspace(-1.5, 1.5, 7) for y in np.linspace(-1, 1, 5)]).shift(LEFT * 3.4 + UP * 0.3)
        g = Text("which stick: 2", color=KEEP).scale(0.5).next_to(grid, DOWN)
        st = Line(DOWN, UP, color=CRUSH, stroke_width=8).shift(RIGHT * 0.2 + UP * 0.3)
        s = Text("inside a stick: 1", color=CRUSH).scale(0.5).next_to(st, DOWN)
        eq = MathTex("2", "+", "1", "=", "3").scale(2.0).shift(RIGHT * 3.6 + UP * 0.3)
        eq[0].set_color(KEEP); eq[2].set_color(CRUSH)
        self.add(grid, g, st, s, eq, caption("count: how many sticks + inside a stick = everything"))


class Board4_plane(Scene):
    """The mute-test frame: slanted sticks (left) each land on ONE dot (right). Colours match stick to dot."""
    def construct(self):
        left = NumberPlane(x_range=[-3, 3], y_range=[-3, 3], x_length=5.2, y_length=5.2,
                           background_line_style={"stroke_color": GREY_D, "stroke_opacity": 0.4}).shift(LEFT * 3.3 + DOWN * 0.2)
        right = left.copy().shift(RIGHT * 6.6)
        lines, dots = VGroup(), VGroup()
        for i, c in enumerate(np.linspace(-1.5, 1.5, 7)):
            lines.add(stick(left, c, color=HUES[i], stroke_width=7 if abs(c) < 1e-9 else 3.5))
            img = M @ np.array([0, c])                                       # every point on it lands here
            dots.add(Dot(right.c2p(*img), color=HUES[i], radius=0.11 if abs(c) < 1e-9 else 0.08))
        rng = Line(right.c2p(-1.5, -3), right.c2p(1.5, 3), color=KEEP, stroke_width=4)
        arrow = Arrow(left.get_right(), right.get_left(), color=GREY_B, buff=0.15)
        mt = tag(r"A=\begin{bmatrix}1&-1\\2&-2\end{bmatrix}").scale(0.8).next_to(arrow, UP)
        k = tag(r"\ker(L)", CRUSH).scale(0.8).move_to(left.c2p(2.0, 1.4))
        r = tag(r"\text{range}(L)", KEEP).scale(0.8).move_to(right.c2p(1.9, 2.4))
        self.add(left, right, rng, lines, dots, arrow, mt, k, r, caption("plane: each slanted stick collapses to ONE dot, same colour"))


class Board5_angle(Scene):
    def construct(self):
        plane = NumberPlane(background_line_style={"stroke_color": GREY_D, "stroke_opacity": 0.35})
        ker = Line([-3.5, -3.5, 0], [3.5, 3.5, 0], color=CRUSH, stroke_width=6)
        rng = Line([-2, -4, 0], [2, 4, 0], color=KEEP, stroke_width=6)
        ang = Angle(Line(ORIGIN, [1, 1, 0]), Line(ORIGIN, [1, 2, 0]), radius=0.9, color=WHITE)
        note = Text("not 90°", color=WHITE).scale(0.45).next_to(ang, UR, buff=0.05)
        k = tag(r"\ker(L)=\text{span}\{[1,1]\}", CRUSH).to_corner(UR)
        r = tag(r"\text{range}(L)=\text{span}\{[1,2]\}", KEEP).next_to(k, DOWN, aligned_edge=RIGHT)
        eq = tag(r"1 + 1 = 2").to_corner(UL)
        self.add(plane, ker, rng, ang, note, k, r, eq, caption("trap: kernel and range need not be perpendicular"))


class Board6_solve(Scene):
    def construct(self):
        left = NumberPlane(x_range=[-3, 3], y_range=[-3, 3], x_length=5.2, y_length=5.2,
                           background_line_style={"stroke_color": GREY_D, "stroke_opacity": 0.35}).shift(LEFT * 3.3 + DOWN * 0.2)
        right = left.copy().shift(RIGHT * 6.6)
        c = 1.0
        st = stick(left, c, color=CRUSH, stroke_width=7)
        x0 = Dot(left.c2p(0, c), color=WHITE)
        b = Dot(right.c2p(*(M @ np.array([0, c]))), color=KEEP, radius=0.12)
        bl = tag(r"\mathbf b", KEEP).next_to(b, RIGHT)
        off = Dot(right.c2p(1.6, -1.2), color=GREY_B, radius=0.1)
        offl = Text("off the range: no solution", color=GREY_B).scale(0.34).next_to(off, DOWN)
        rng = Line(right.c2p(-1.5, -3), right.c2p(1.5, 3), color=KEEP, stroke_width=4)
        sl = tag(r"\mathbf x_0 + \ker(L)", CRUSH).scale(0.8).move_to(left.c2p(1.6, 1.0))
        self.add(left, right, rng, st, x0, b, bl, off, offl, sl, caption("solve: Ax = b is the pancake question backwards"))


class Board7_exam(Scene):
    def construct(self):
        A = Matrix([[1, 2, 1, 0, 3], [2, 4, 3, 1, 5], [1, 2, 2, 2, 4]], h_buff=0.8).scale(0.75)
        B = Matrix([[1, 2, 0, 0, 6], [0, 0, 1, 0, -3], [0, 0, 0, 1, 2]], h_buff=0.8).scale(0.75)   # sympy-verified rref of A
        VGroup(A, B).arrange(RIGHT, buff=1.2).shift(UP * 0.8)
        arrow = Arrow(A.get_right(), B.get_left(), color=GREY_B)
        al = Text("row reduce", color=GREY_B).scale(0.35).next_to(arrow, UP)
        for j in (0, 2, 3):
            A.get_columns()[j].set_color(KEEP); B.get_columns()[j].set_color(KEEP)
        for j in (1, 4):
            B.get_columns()[j].set_color(CRUSH)
        warn = Text("range: pivot columns of the ORIGINAL A", color=KEEP).scale(0.42).next_to(A, DOWN, buff=0.4)
        eq = MathTex(r"\underbrace{3}_{\text{pivots}}", "+", r"\underbrace{2}_{\text{free}}", "=", r"\underbrace{5}_{n}").next_to(B, DOWN, buff=0.4)
        eq[0].set_color(KEEP); eq[2].set_color(CRUSH)
        self.add(A, B, arrow, al, warn, eq, caption("exam: Range Method uses A; Kernel Method uses free variables"))


class Board8_poly(Scene):
    def construct(self):
        p = press(label="d/dx").scale(0.8).shift(LEFT * 3.6 + DOWN * 0.3)
        inp = MathTex("a x^3 + b x^2 + c x +", "d").scale(0.9).next_to(p, UP, buff=0.3)
        inp[1].set_color(CRUSH)
        out = MathTex("3a x^2 + 2b x + c", color=KEEP).scale(0.9).shift(RIGHT * 2.2 + UP * 0.6)
        binlab = VGroup(Rectangle(width=1.4, height=0.9, color=CRUSH), MathTex("d", color=CRUSH)).shift(RIGHT * 0.2 + DOWN * 1.8)
        crushed = Text("crushed: constants", color=CRUSH).scale(0.38).next_to(binlab, DOWN, buff=0.1)
        eq = MathTex("1", "+", "3", "=", "4", r"=\dim P_3").scale(1.0).shift(RIGHT * 3.4 + DOWN * 1.4)
        eq[0].set_color(CRUSH); eq[2].set_color(KEEP)
        self.add(p, inp, out, binlab, crushed, eq, caption("poly: works for polynomials too"))


class Board9_kernelmethod(Scene):
    """Kernel Method on the sympy-verified rref: free x2, x5 -> basis [-2,1,0,0,0], [-6,0,3,-2,1]."""
    def construct(self):
        B = Matrix([[1, 2, 0, 0, 6], [0, 0, 1, 0, -3], [0, 0, 0, 1, 2]], h_buff=0.8).scale(0.8).to_edge(UP, buff=0.6)
        for j in (1, 4):
            B.get_columns()[j].set_color(CRUSH)
        hd = Text("free variables: x2, x5", color=CRUSH).scale(0.45).next_to(B, DOWN, buff=0.3)
        v1 = MathTex(r"x_2=1,\ x_5=0:\quad", r"\begin{bmatrix}-2\\1\\0\\0\\0\end{bmatrix}").scale(0.75)
        v2 = MathTex(r"x_2=0,\ x_5=1:\quad", r"\begin{bmatrix}-6\\0\\3\\-2\\1\end{bmatrix}").scale(0.75)
        v1[1].set_color(CRUSH); v2[1].set_color(CRUSH)
        VGroup(v1, v2).arrange(RIGHT, buff=1.0).next_to(hd, DOWN, buff=0.35)
        lab = tag(r"\ker(L)=\text{span of these two},\ \dim(\ker(L))=2", CRUSH).scale(0.8).next_to(VGroup(v1, v2), DOWN, buff=0.3)
        self.add(B, hd, v1, v2, lab, caption("kernel method: one basis vector per free variable"))


class Board10_space(Scene):
    """3D, drawn flat: left, sticks are lines (2 + 1). Right, the 'sticks' are whole sheets (1 + 2)."""
    def construct(self):
        def slab(c):
            return Polygon([-1.2, -0.5, 0], [0.6, -0.5, 0], [1.2, 0.3, 0], [-0.6, 0.3, 0],
                           fill_color=c, fill_opacity=0.35, stroke_color=c, stroke_width=3)
        lp = slab(KEEP).shift(LEFT * 3.4 + DOWN * 1.2)
        lines = VGroup(*[Line([x, -1.1, 0], [x + 0.5, 1.6, 0], color=CRUSH, stroke_width=3).shift(LEFT * 3.4)
                         for x in np.linspace(-0.9, 0.6, 5)])
        l_eq = MathTex("2", "+", "1", "=", "3").scale(1.0).next_to(lp, DOWN, buff=0.4)
        l_eq[0].set_color(KEEP); l_eq[2].set_color(CRUSH)
        l_t = Text("onto a plane: sticks are lines", color=GREY_A).scale(0.38).next_to(lines, UP)
        rl = Line([-1.4, -1.2, 0], [1.4, -0.6, 0], color=KEEP, stroke_width=6).shift(RIGHT * 3.4)
        sheets = VGroup(*[slab(CRUSH).rotate(1.2, axis=RIGHT).scale(0.7).shift(RIGHT * (3.4 + dx) + UP * 0.6) for dx in (-0.8, 0, 0.8)])
        r_eq = MathTex("1", "+", "2", "=", "3").scale(1.0).next_to(rl, DOWN, buff=0.6)
        r_eq[0].set_color(KEEP); r_eq[2].set_color(CRUSH)
        r_t = Text("onto a line: sticks are sheets", color=GREY_A).scale(0.38).next_to(sheets, UP)
        self.add(lp, lines, l_eq, l_t, rl, sheets, r_eq, r_t, caption("3D: the pieces change shape, the count never breaks"))
