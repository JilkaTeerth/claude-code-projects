"""MAT 230, 5.3 The Dimension Theorem, v3.2: "Every Pancake Has a Stick".

Narration: Kokoro af_heart @0.96 (audio/*.wav), phrase-timed via audio/cues.json so every visual lands
on its words. Notation: Andrilli & Hecker 4th ed. (Theorems 5.8, 5.9, 5.10, Corollary 5.11, Kernel
and Range Methods). Every number on screen was checked in sympy (see LEARNINGS.md).
Render via:  ../explain.py build dimension-theorem-v3.2
"""
import json, pathlib, sys
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from manim import *
from props import *

DUR = json.load(open(HERE / "audio" / "durations.json"))
CUES = json.load(open(HERE / "audio" / "cues.json"))
SFX = HERE.parent / "sfx"
M2 = np.array([[1, -1], [2, -2]])                     # plane example: ker span{[1,1]}, range span{[1,2]}
A35 = [[1, 2, 1, 0, 3], [2, 4, 3, 1, 5], [1, 2, 2, 2, 4]]
B35 = [[1, 2, 0, 0, 6], [0, 0, 1, 0, -3], [0, 0, 0, 1, 2]]   # sympy rref of A35
config.background_color = BG
config.tex_template = latex_template()


class Video(ThreeDScene):
    # ------------------------------------------------------------ timing
    def beat(self, key):
        # Manim's own mixer dropped the last ~50s of narration once (2026-10-08). Every sound is
        # also logged with its exact start time; mux.py builds the real soundtrack from this log.
        self.timeline.append([round(self.renderer.time, 4), str(HERE / "audio" / f"{key}.wav"), 0])
        self.add_sound(str(HERE / "audio" / f"{key}.wav"))
        self.key, self.t0 = key, self.renderer.time

    def at(self, phrase, lead=0.0):
        """Wait until the narration reaches the phrase (minus a small lead)."""
        cues = CUES[self.key]
        for i, (t, text) in enumerate(cues):
            j = text.lower().find(phrase.lower())
            if j >= 0:
                # mid-phrase cue: place it proportionally through the phrase's spoken length
                end = cues[i + 1][0] - 0.35 if i + 1 < len(cues) else DUR[self.key] - 0.35
                t = t + max(0.0, end - t) * (j / max(1, len(text)))
                gap = self.t0 + t - lead - self.renderer.time
                if gap > 0.02:
                    self.wait(gap)
                return
        raise KeyError(f"{phrase!r} not in beat {self.key}")

    def done(self, pad=0.25):
        gap = self.t0 + DUR[self.key] + pad - self.renderer.time
        if gap > 0.02:
            self.wait(gap)

    def sfx(self, name, gain=-6):
        self.timeline.append([round(self.renderer.time, 4), str(SFX / f"{name}.wav"), gain])
        self.add_sound(str(SFX / f"{name}.wav"), gain=gain)

    def clear(self, rt=0.6):
        if self.mobjects:
            self.play(*[FadeOut(m) for m in self.mobjects], run_time=rt)

    def shake(self, group, amp=0.12):
        for d in (RIGHT, LEFT, RIGHT * 0.5):
            self.play(group.animate.shift(d * amp), run_time=0.05)
        self.play(group.animate.shift(LEFT * 0.5 * amp), run_time=0.05)

    def pop(self, *ms, rt=0.35):
        self.sfx("pop", -10)
        self.play(*[FadeIn(m, scale=0.8) for m in ms], run_time=rt)

    # ------------------------------------------------------------ the press
    def build_press(self, label="PANCAKE 3000", pos=LEFT * 3 + DOWN * 0.4, gap=2.0):
        p = press(gap=gap, label=label).move_to(pos)
        top = VGroup(p[3], p[5])                      # top plate + its name tag move together
        return p, top

    def slam(self, p, top, item, flat, out_to=None, rt=0.25):
        base = p[2]
        self.play(item.animate.next_to(base, UP, buff=0.03), run_time=0.6)
        flat.next_to(base, UP, buff=0.03)
        d = top.get_bottom()[1] - base.get_top()[1] - flat.height - 0.02
        self.sfx("slam", -3)
        self.play(top.animate.shift(DOWN * d), Transform(item, flat), rate_func=rush_into, run_time=rt)
        self.shake(VGroup(p, item))
        self.play(top.animate.shift(UP * d), run_time=0.4)
        if out_to is not None:
            self.sfx("whoosh", -12)
            self.play(item.animate.move_to(out_to), run_time=0.5)
        return item

    # ------------------------------------------------------------ the video
    def construct(self):
        self.timeline = []
        self.hook(); self.question(); self.sticks(); self.count(); self.names(); self.subspaces()
        self.trap(); self.plane(); self.plane2(); self.space(); self.solve(); self.membership()
        self.exam(); self.kernelmethod(); self.transpose(); self.poly(); self.next54(); self.callback()
        json.dump({"total": round(self.renderer.time, 4), "sounds": self.timeline}, open(HERE / "audio" / "timeline.json", "w"), indent=0)

    def hook(self):
        self.beat("hook")
        title = Text("Every Pancake Has a Stick", weight=BOLD).scale(0.9)
        sub = Text("MAT 230 · 5.3 The Dimension Theorem", color=GREY_B).scale(0.4).next_to(title, DOWN)
        self.play(FadeIn(title, shift=UP * 0.2), FadeIn(sub), run_time=0.8)
        self.at("roommate", lead=0.3)
        self.play(FadeOut(title), FadeOut(sub), run_time=0.4)
        p, top = self.build_press()
        self.play(FadeIn(p, shift=DOWN * 0.5), run_time=0.8)
        self.at("Three Thousand")
        self.play(Indicate(p[5], color=KEEP, scale_factor=1.6), run_time=1.0)
        self.at("Burger goes in", lead=0.2)
        b = burger(1.5).move_to(LEFT * 8 + DOWN * 0.4)
        self.add(b)
        self.at("pancake comes out", lead=0.25)
        pc = self.slam(p, top, b, pancake(1.5), out_to=RIGHT * 1.0 + DOWN * 0.9)
        f1 = face(pc); self.pop(f1)
        self.at("Basketball", lead=0.1)
        ball = basketball(0.7).move_to(LEFT * 8 + DOWN * 0.4); self.add(ball)
        flat = basketball(0.7).stretch(0.22, dim=1).stretch(1.4, dim=0)
        disk = self.slam(p, top, ball, flat, out_to=RIGHT * 3.4 + DOWN * 0.9)
        f2 = face(disk); self.pop(f2)
        self.at("his phone", lead=0.2)
        ph = phone(1.5).move_to(LEFT * 8 + DOWN * 0.2); self.add(ph)
        co = coaster(1.5)[0]
        ph = self.slam(p, top, ph, co, out_to=RIGHT * 5.4 + DOWN * 0.9)
        self.at("very expensive coaster", lead=0.1)
        full = coaster(1.5).move_to(ph.get_center() + UP * 0.25)
        cup, crack = full[2], full[1]
        cup.shift(UP * 3)
        self.play(Create(crack), run_time=0.3)
        self.play(cup.animate.shift(DOWN * 3), rate_func=rush_into, run_time=0.45)
        self.sfx("slam", -16)
        joke = Text("a very expensive coaster", color=KEEP, slant=ITALIC).scale(0.45).next_to(ph, UP, buff=1.0)
        self.play(FadeIn(joke, shift=DOWN * 0.2), run_time=0.5)
        self.done()
        self.press_parts = (p, top)
        self.clear()

    def question(self):
        self.beat("question")
        p, top = self.build_press(pos=UP * 0.6)
        self.play(FadeIn(p), run_time=0.5)
        self.at("Which burger", lead=0.1)
        q = Text("which burger made this?", color=KEEP).scale(0.55).to_edge(DOWN, buff=0.7)
        target = pancake(1.6).move_to(DOWN * 2.2)
        self.add(target); self.play(FadeIn(target), FadeIn(face(target)), Write(q), run_time=0.8)
        self.at("tiny burger", lead=0.2)
        for b in (burger(0.9), burger(1.7).stretch(1.5, 1), burger(1.25)):
            b.move_to(UP * 4.5); self.add(b)
            flat = pancake(1.6)
            self.play(b.animate.next_to(p[2], UP, buff=0.03), run_time=0.35)
            flat.next_to(p[2], UP, buff=0.03)
            d = top.get_bottom()[1] - p[2].get_top()[1] - flat.height - 0.02
            self.sfx("slam", -8)
            self.play(top.animate.shift(DOWN * d), Transform(b, flat), rate_func=rush_into, run_time=0.2)
            self.play(top.animate.shift(UP * d), b.animate.move_to(target), run_time=0.4)
            self.remove(b)
        self.at("forgets something")
        qm = Text("?", weight=BOLD, color=KEEP).scale(2.4).next_to(p, RIGHT, buff=0.5)
        self.pop(qm)
        self.play(Wiggle(qm), run_time=1.0)
        self.done(); self.clear()

    def sticks(self):
        self.beat("sticks")
        b = burger(2.6).move_to(LEFT * 3 + UP * 0.2)
        self.play(FadeIn(b), run_time=0.5)
        self.at("skinny vertical sticks", lead=0.2)
        xs = np.linspace(-1.1, 1.1, 11)
        sticks = VGroup(*[Line(b.get_bottom() + [x, 0.05, 0], b.get_top() + [x, -0.05, 0], color=CRUSH, stroke_width=4) for x in xs])
        self.play(b.animate.set_opacity(0.22), LaggedStart(*[Create(s) for s in sticks], lag_ratio=0.08), run_time=1.6)
        tilt = sticks[2]
        self.play(Rotate(tilt, 0.5), run_time=0.35); self.play(Rotate(tilt, -0.5), run_time=0.35)   # a hint: sticks can lean
        self.at("squishes each whole stick", lead=0.2)
        pc = pancake(2.6).move_to(RIGHT * 3 + DOWN * 0.3)
        dots = VGroup(*[Dot(pc.get_center() + [x * 1.35, 0.03, 0], radius=0.08, color=KEEP) for x in xs])
        self.play(FadeIn(pc), run_time=0.4)
        self.sfx("slam", -10)
        self.play(*[ReplacementTransform(s.copy(), d) for s, d in zip(sticks, dots)], run_time=1.6)
        self.at("map of sticks")
        hl = sticks[5].copy().set_stroke(width=10)
        link = Arrow(hl.get_center() + RIGHT * 0.3, dots[5].get_center() + UP * 0.3, color=GREY_B, buff=0.1)
        self.play(Create(hl), GrowArrow(link), dots[5].animate.scale(2.2), run_time=0.8)
        self.at("Every dot was a stick")
        self.play(Indicate(dots[5], color=KEEP, scale_factor=1.6), Indicate(hl, color=CRUSH), run_time=1.0)
        self.done(); self.clear()

    def count(self):
        self.beat("count")
        hd = Text("Now we count", weight=BOLD).scale(0.6).to_edge(UP)
        self.play(FadeIn(hd, shift=DOWN * 0.2), run_time=0.5)
        grid = VGroup(*[Dot([x, y * 0.55, 0], radius=0.06, color=KEEP) for x in np.linspace(-1.6, 1.6, 8) for y in np.linspace(-1, 1, 5)]).move_to(LEFT * 3.6 + UP * 0.6)
        self.at("point at a stick", lead=0.1)
        self.play(LaggedStart(*[FadeIn(d, scale=0.5) for d in grid], lag_ratio=0.02), run_time=1.0)
        self.at("Two.")
        arrows = VGroup(Arrow(grid.get_corner(DL) + DOWN * 0.3, grid.get_corner(DR) + DOWN * 0.3, color=KEEP, buff=0),
                        Arrow(grid.get_corner(DR) + RIGHT * 0.3, grid.get_corner(UR) + RIGHT * 0.3, color=KEEP, buff=0))
        two = Text("which stick: 2", color=KEEP).scale(0.5).next_to(arrows[0], DOWN, buff=0.2)
        self.pop(two); self.play(GrowArrow(arrows[0]), GrowArrow(arrows[1]), run_time=0.6)
        self.at("Room inside one stick", lead=0.1)
        st = Line(DOWN * 1.1, UP * 1.1, color=CRUSH, stroke_width=9).move_to(RIGHT * 0.3 + UP * 0.6)
        self.play(Create(st), run_time=0.6)
        self.at("One. Up down")
        one = Text("inside a stick: 1", color=CRUSH).scale(0.5).next_to(st, DOWN)
        self.pop(one)
        self.at("Two plus one")
        eq = MathTex("2", "+", "1", "=", "3").scale(2.4).move_to(RIGHT * 4 + UP * 0.6)
        eq[0].set_color(KEEP); eq[2].set_color(CRUSH)
        self.play(FadeIn(eq, scale=1.2), Indicate(two, color=KEEP), Indicate(one, color=CRUSH), run_time=1.0)
        self.sfx("ding", -10)
        self.at("literally made of sticks")
        cube = iso_cube(1.0).next_to(eq, DOWN, buff=0.5)
        self.play(FadeIn(cube, shift=UP * 0.2), run_time=0.6)
        self.done(); self.clear()

    def names(self):
        self.beat("names")
        p, top = self.build_press(label="L", pos=LEFT * 4.2 + DOWN * 0.3)
        self.play(FadeIn(p), run_time=0.6)
        self.at("linear transformation", lead=0.1)
        lt = Text("a linear transformation", color=GREY_A, slant=ITALIC).scale(0.42).next_to(p, UP)
        self.play(FadeIn(lt), Indicate(p[5], color=KEEP, scale_factor=2.0), run_time=0.8)
        self.at("domain, V", lead=0.1)
        V = tag(r"V \text{ (the domain)}").scale(0.8).next_to(p, DOWN)
        self.pop(V)
        self.at("lands exactly on zero", lead=0.1)
        ker = Line(DOWN * 1.2, UP * 1.2, color=CRUSH, stroke_width=9).move_to(RIGHT * 0.2 + UP * 0.4)
        kl = tag(r"\ker(L)", CRUSH).next_to(ker, UP)
        self.play(Create(ker), run_time=0.6); self.pop(kl)
        self.at("null space", lead=0.1)
        ns = Text("a.k.a. null space", color=CRUSH).scale(0.38).next_to(kl, RIGHT)
        self.play(FadeIn(ns), run_time=0.4)
        self.at("that same kernel, slid over")
        copies = VGroup(*[ker.copy().set_stroke(width=4, opacity=0.6) for _ in range(4)])
        self.add(copies)
        self.play(*[c.animate.shift(RIGHT * dx) for c, dx in zip(copies, (-1.2, -0.6, 0.6, 1.2))], run_time=1.2)
        self.at("Parallel copies")
        par = Text("parallel copies", color=CRUSH).scale(0.4).next_to(copies, DOWN)
        self.pop(par)
        self.at("The pancake, everything", lead=0.1)
        pc = pancake(2.2).move_to(RIGHT * 4.3 + DOWN * 0.2)
        rl = tag(r"\text{range}(L)", KEEP).next_to(pc, UP, buff=0.4)
        self.play(FadeIn(pc), run_time=0.5); self.pop(rl)
        self.at("Theorem 5.10", lead=0.2)
        self.play(*[FadeOut(m) for m in (lt, ns, par, copies, V)], VGroup(p, ker, kl, pc, rl).animate.shift(UP * 1.2).scale(0.8), run_time=0.8)
        self.wait(0.1)
        thm = MathTex(r"\dim(\ker(L))", "+", r"\dim(\text{range}(L))", "=", r"\dim(V)").scale(1.1).move_to(DOWN * 1.7)
        thm[0].set_color(CRUSH); thm[2].set_color(KEEP)
        box = SurroundingRectangle(thm, color=WHITE, buff=0.22, corner_radius=0.1)
        name = Text("Theorem 5.10, the Dimension Theorem", color=GREY_B).scale(0.38).next_to(box, UP, buff=0.12)
        self.play(Write(thm), Create(box), FadeIn(name), run_time=1.6)
        self.at("Inside a stick, plus", lead=0.1)
        u1 = Text("inside a stick", color=CRUSH).scale(0.38).next_to(thm[0], DOWN, buff=0.35)
        u2 = Text("how many sticks", color=KEEP).scale(0.38).next_to(thm[2], DOWN, buff=0.35)
        self.pop(u1, u2)
        self.sfx("ding", -10)
        self.done(); self.clear()

    def subspaces(self):
        self.beat("subspaces")
        h = Text("Theorem 5.8", color=GREY_B).scale(0.45).to_edge(UP)
        self.play(FadeIn(h), run_time=0.4)
        Vr = RoundedRectangle(width=4.2, height=3.2, corner_radius=0.3, color=GREY_B).move_to(LEFT * 3.2 + DOWN * 0.2)
        Wr = Vr.copy().move_to(RIGHT * 3.2 + DOWN * 0.2)
        self.at("subspace of V", lead=0.2)
        vl = Text("V: inputs", color=GREY_A).scale(0.45).next_to(Vr, UP, buff=0.1)
        k = Line(DOWN * 1.1, UP * 1.1, color=CRUSH, stroke_width=8).move_to(Vr)
        kl = tag(r"\ker(L)", CRUSH).scale(0.8).next_to(k, RIGHT)
        self.play(Create(Vr), FadeIn(vl), run_time=0.6); self.play(Create(k), run_time=0.5); self.pop(kl)
        self.at("subspace of W", lead=0.2)
        wl = Text("W: outputs", color=GREY_A).scale(0.45).next_to(Wr, UP, buff=0.1)
        r = Line(LEFT * 1.5 + DOWN * 0.8, RIGHT * 1.5 + UP * 0.8, color=KEEP, stroke_width=8).move_to(Wr)
        rl = tag(r"\text{range}(L)", KEEP).scale(0.8).next_to(r, DOWN, buff=0.15)
        self.play(Create(Wr), FadeIn(wl), run_time=0.6); self.play(Create(r), run_time=0.5); self.pop(rl)
        self.at("can't be bigger than W", lead=0.1)
        cap = MathTex(r"\dim(\text{range}(L)) \le \dim(W)", color=KEEP).scale(0.8).next_to(Wr, DOWN, buff=0.3)
        self.play(Write(cap), Indicate(Wr, color=KEEP), run_time=1.0)
        self.at("six dimensions into four", lead=0.1)
        self.play(*[FadeOut(m) for m in (Vr, Wr, vl, wl, k, kl, r, rl, cap)], run_time=0.5)
        big = Rectangle(width=4.2, height=2.2, color=GREY_B, fill_opacity=0.15).move_to(LEFT * 2.5)
        bl = MathTex(r"\mathbb{R}^6").move_to(big)
        small = Rectangle(width=2.6, height=1.4, color=KEEP, fill_opacity=0.15).move_to(RIGHT * 3)
        sl = MathTex(r"\mathbb{R}^4", color=KEEP).move_to(small)
        self.play(FadeIn(big), FadeIn(bl), FadeIn(small), FadeIn(sl), run_time=0.5)
        self.sfx("slam", -10)
        self.play(big.animate.match_width(small).match_height(small).move_to(small), bl.animate.move_to(small).set_opacity(0), run_time=0.8)
        crushed = MathTex(r"\dim(\ker(L)) \ge 6 - 4 = 2", color=CRUSH).scale(0.95).next_to(small, DOWN, buff=0.5)
        self.play(Write(crushed), run_time=0.8)
        self.done(); self.clear()

    def trap(self):
        self.beat("trap")
        floor = Line(LEFT * 3, RIGHT * 3, color=KEEP, stroke_width=6).shift(DOWN * 1.6)
        xs = np.linspace(-2.4, 2.4, 9)
        sticks = VGroup(*[Line([x, -1.6, 0], [x, 1.4, 0], color=CRUSH, stroke_width=4) for x in xs])
        self.play(Create(floor), LaggedStart(*[Create(s) for s in sticks], lag_ratio=0.05), run_time=1.0)
        self.at("Most transformations don't", lead=0.1)
        warn = Text("careful", color=CRUSH, weight=BOLD).scale(0.6).to_corner(UL)
        self.pop(warn)
        self.at("The sticks can lean", lead=0.1)
        self.play(*[s.animate.put_start_and_end_on(s.get_start(), s.get_start() + [1.9, 3.0, 0]) for s in sticks], run_time=1.2)
        self.at("stretched and turned", lead=0.3)
        a_in = Arrow(LEFT * 5.8 + UP * 2.2, LEFT * 4.6 + UP * 2.2, color=BLUE_B, buff=0)
        a_out = Arrow(RIGHT * 4.0 + UP * 1.6, RIGHT * 4.0 + UP * 1.6 + 2.0 * np.array([np.cos(0.9), np.sin(0.9), 0]), color=BLUE_B, buff=0)
        self.play(GrowArrow(a_in), run_time=0.4)
        self.play(TransformFromCopy(a_in, a_out), run_time=0.9)
        self.at("conserved is the count", lead=0.1)
        ban = Text("the COUNT is conserved, not the directions", color=WHITE).scale(0.5)
        ban.add_background_rectangle(color=BG, opacity=0.9, buff=0.15).to_edge(DOWN, buff=0.35)
        self.play(FadeIn(ban, shift=UP * 0.3), run_time=0.5)
        self.done(); self.clear()

    def plane(self):
        self.beat("plane")
        self.plane_ = NumberPlane(x_range=[-7, 7], y_range=[-4, 4], background_line_style={"stroke_color": GREY_D, "stroke_opacity": 0.45})
        mt = tag(r"A=\begin{bmatrix}1&-1\\2&-2\end{bmatrix}").to_corner(UL)
        self.play(Create(self.plane_), run_time=1.0); self.pop(mt)
        self.at("slice the plane", lead=0.1)
        cs = np.linspace(-3, 3, 13)
        hues = [interpolate_color(ManimColor("#ff5a5f"), ManimColor("#ff9f43"), abs(c) / 3) for c in cs]
        lines = VGroup(*[Line([-9, -9 + c, 0], [9, 9 + c, 0], color=h, stroke_width=7 if c == 0 else 3) for c, h in zip(cs, hues)])
        dots = VGroup(*[Dot([0, c, 0], radius=0.09, color=h) for c, h in zip(cs, hues)])
        self.play(LaggedStart(*[Create(l) for l in lines], lag_ratio=0.06), run_time=1.6)
        self.at("slanted red lines")
        self.play(LaggedStart(*[FadeIn(d, scale=0.5) for d in dots], lag_ratio=0.04), run_time=0.8)
        self.at("Now press", lead=0.1)
        self.sfx("slam", -8)
        mat = [[1, -1], [2, -2]]
        targets = [M2 @ np.array([0.0, c]) for c in cs]                  # where each stick's points land
        self.play(ApplyMatrix(mat, lines),
                  *[d.animate.move_to([tx, ty, 0]) for d, (tx, ty) in zip(dots, targets)], run_time=2.6)
        self.remove(lines)
        self.at("collapses into one yellow dot")
        self.play(*[Flash(d.get_center(), color=d.get_color(), line_length=0.2, num_lines=8, run_time=0.6) for d in dots[4:9]])
        self.play(*[d.animate.set_color(KEEP) for d in dots], run_time=0.5)          # "...into one yellow dot"
        self.at("line up on a single line")
        rng = Line([-2.2, -4.4, 0], [2.2, 4.4, 0], color=KEEP, stroke_width=5)
        self.play(Create(rng), run_time=0.8)
        self.at("That's the range")
        rl = tag(r"\text{range}(L)", KEEP).move_to([2.6, 3.0, 0])
        self.pop(rl)
        self.plane_objs = VGroup(dots, rng, rl, mt)
        self.done()

    def plane2(self):
        self.beat("plane2")
        dots, rng, rl, mt = self.plane_objs
        self.play(FadeOut(dots), FadeOut(rl), run_time=0.4)
        self.at("Kernel: the line", lead=0.1)
        ker = Line([-3.8, -3.8, 0], [3.8, 3.8, 0], color=CRUSH, stroke_width=6)
        kt = tag(r"\ker(L)=\text{span}\{[1,1]\},\ \dim 1", CRUSH).to_corner(UR)
        self.play(Create(ker), run_time=0.6); self.pop(kt)
        self.at("Range: the line", lead=0.1)
        rt = tag(r"\text{range}(L)=\text{span}\{[1,2]\},\ \dim 1", KEEP).next_to(kt, DOWN, aligned_edge=RIGHT)
        self.play(Indicate(rng, color=KEEP), run_time=0.5); self.pop(rt)
        self.at("One plus one is two")
        eq = tag(r"1 + 1 = 2 = \dim(\mathbb{R}^2)").next_to(mt, DOWN, aligned_edge=LEFT)
        self.pop(eq); self.sfx("ding", -12)
        self.at("not at right angles")
        ang = Angle(Line(ORIGIN, [1, 1, 0]), Line(ORIGIN, [1, 2, 0]), radius=0.9, color=WHITE)
        note = Text("not 90°", color=WHITE).scale(0.45).next_to(ang, UR, buff=0.05)
        self.play(Create(ang), FadeIn(note), run_time=0.6)
        self.done(); self.clear()

    def space(self):
        self.beat("space")
        axes = ThreeDAxes(x_range=[-3, 3], y_range=[-3, 3], z_range=[-2, 2], x_length=6, y_length=6, z_length=4)
        self.set_camera_orientation(phi=68 * DEGREES, theta=-50 * DEGREES)
        self.play(FadeIn(axes), run_time=0.6)
        self.at("onto a plane", lead=0.1)
        flat = Surface(lambda u, v: axes.c2p(u, v, 0), u_range=[-2.4, 2.4], v_range=[-2.4, 2.4], resolution=(6, 6),
                       fill_color=KEEP, fill_opacity=0.35, stroke_color=KEEP, stroke_width=0.5)
        pts = [(x, y) for x in np.linspace(-2, 2, 5) for y in np.linspace(-2, 2, 5)]
        lines = VGroup(*[Line(axes.c2p(x, y, -1.8), axes.c2p(x, y, 1.8), color=CRUSH, stroke_width=3) for x, y in pts])
        self.play(Create(flat), LaggedStart(*[Create(l) for l in lines], lag_ratio=0.02), run_time=1.2)
        self.sfx("slam", -10)
        self.play(*[l.animate.put_start_and_end_on(axes.c2p(x, y, 0), axes.c2p(x, y, 0) + 1e-3 * RIGHT) for l, (x, y) in zip(lines, pts)], run_time=1.2)
        e1 = MathTex("2", "+", "1", "=", "3").scale(1.1).to_corner(UR)
        e1[0].set_color(KEEP); e1[2].set_color(CRUSH)
        self.add_fixed_in_frame_mobjects(e1); self.play(FadeIn(e1), run_time=0.4)
        self.at("onto a line", lead=0.2)
        self.play(FadeOut(flat), FadeOut(lines), run_time=0.4)
        xl = Line(axes.c2p(-2.8, 0, 0), axes.c2p(2.8, 0, 0), color=KEEP, stroke_width=6)
        sheets = VGroup(*[Surface(lambda u, v, x=x: axes.c2p(x, u, v), u_range=[-1.8, 1.8], v_range=[-1.4, 1.4], resolution=(4, 4),
                                  fill_color=CRUSH, fill_opacity=0.28, stroke_color=CRUSH, stroke_width=0.6) for x in (-1.6, 0, 1.6)])
        self.play(Create(xl), FadeIn(sheets), run_time=0.9)
        self.sfx("slam", -10)
        self.play(*[s.animate.scale(0.02) for s in sheets], run_time=1.0)
        e2 = MathTex("1", "+", "2", "=", "3").scale(1.1).next_to(e1, DOWN)
        e2[0].set_color(KEEP); e2[2].set_color(CRUSH)
        self.add_fixed_in_frame_mobjects(e2); self.play(FadeIn(e2), run_time=0.4)
        self.at("count never breaks")
        self.begin_ambient_camera_rotation(rate=0.15)
        self.done(pad=0.0)
        self.stop_ambient_camera_rotation()
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.5)
        self.set_camera_orientation(phi=0, theta=-90 * DEGREES)

    def two_planes(self):
        left = NumberPlane(x_range=[-3, 3], y_range=[-3, 3], x_length=5.4, y_length=5.4,
                           background_line_style={"stroke_color": GREY_D, "stroke_opacity": 0.4}).shift(LEFT * 3.4 + DOWN * 0.3)
        right = left.copy().shift(RIGHT * 6.8)
        return left, right

    def solve(self):
        self.beat("solve")
        left, right = self.two_planes()
        lt = Text("inputs", color=GREY_A).scale(0.4).next_to(left, UP, buff=0.1)
        rt = Text("outputs", color=GREY_A).scale(0.4).next_to(right, UP, buff=0.1)
        rng = Line(right.c2p(-1.5, -3), right.c2p(1.5, 3), color=KEEP, stroke_width=4)
        self.play(FadeIn(left), FadeIn(right), FadeIn(lt), FadeIn(rt), Create(rng), run_time=0.8)
        self.at("Which inputs land on b")
        b = Dot(right.c2p(-1, -2), color=KEEP, radius=0.13)
        bl = tag(r"\mathbf b", KEEP).scale(0.9).next_to(b, RIGHT)
        self.pop(b, bl)
        self.at("off the pancake", lead=0.1)
        self.play(b.animate.move_to(right.c2p(1.6, -1.3)), bl.animate.move_to(right.c2p(2.1, -1.3)), run_time=0.7)
        none = Text("nothing lands here: no solution", color=GREY_B).scale(0.38).next_to(b, DOWN)
        self.sfx("buzz", -12); self.pop(none)
        self.at("If b is on it", lead=0.1)
        self.play(FadeOut(none), b.animate.move_to(right.c2p(-1, -2)), bl.animate.move_to(right.c2p(-0.5, -2)), run_time=0.6)
        self.at("a whole stick lands there")
        st = Line(left.c2p(-3, -2), left.c2p(2, 3), color=CRUSH, stroke_width=7)      # y = x + 1, all map to (-1,-2)
        self.play(Create(st), run_time=0.8)
        self.play(*[TransformFromCopy(Dot(left.c2p(x, x + 1), color=CRUSH), b.copy()) for x in (-2, -1, 0, 1)], run_time=1.0)
        self.at("one particular solution", lead=0.1)
        x0 = Dot(left.c2p(0, 1), color=WHITE, radius=0.1)
        x0l = tag(r"\mathbf x_0", WHITE).scale(0.8).next_to(x0, LEFT)
        self.pop(x0, x0l)
        self.at("plus something from the kernel")
        sl = tag(r"\text{all solutions} = \mathbf x_0 + \ker(L)", CRUSH).scale(0.85).to_edge(DOWN, buff=0.25)
        self.play(Write(sl), Indicate(st, color=CRUSH), run_time=1.0)
        self.done(); self.clear()

    def membership(self):
        self.beat("membership")
        def aug(rows):
            m = Matrix(rows, h_buff=0.9).scale(0.8)
            bar = Line(m.get_top(), m.get_bottom(), color=GREY_B).move_to(m.get_columns()[2].get_left() + LEFT * 0.22)
            return VGroup(m, bar)
        hd = Text("Is b on the pancake?", weight=BOLD, color=KEEP).scale(0.6).to_edge(UP, buff=0.3)
        self.play(FadeIn(hd, shift=DOWN * 0.2), run_time=0.5)
        self.at("Glue b onto A", lead=0.1)
        m1 = aug([[1, -1, 1], [2, -2, 2]]).move_to(LEFT * 3.2 + UP * 1.3)
        self.play(FadeIn(m1), run_time=0.6)
        self.at("one, two", lead=0.2)
        r1 = aug([[1, -1, 1], [0, 0, 0]]).move_to(RIGHT * 1.0 + UP * 1.3)
        a1 = Arrow(m1.get_right(), r1.get_left(), color=GREY_B)
        self.play(GrowArrow(a1), TransformFromCopy(m1, r1), run_time=0.9)
        self.at("all zeros")
        row = r1[0].get_rows()[1]
        self.play(row.animate.set_color(GREEN_C), run_time=0.4); self.sfx("ding", -12)
        ok = Text("on the pancake", color=GREEN_C).scale(0.4).next_to(r1, RIGHT)
        self.pop(ok)
        self.at("one, three", lead=0.2)
        m2 = aug([[1, -1, 1], [2, -2, 3]]).move_to(LEFT * 3.2 + DOWN * 1.5)
        r2 = aug([[1, -1, 0], [0, 0, 1]]).move_to(RIGHT * 1.0 + DOWN * 1.5)        # sympy rref
        a2 = Arrow(m2.get_right(), r2.get_left(), color=GREY_B)
        self.play(FadeIn(m2), run_time=0.4)
        self.play(GrowArrow(a2), TransformFromCopy(m2, r2), run_time=0.9)
        self.at("zero equals one")
        row2 = r2[0].get_rows()[1]
        self.sfx("buzz", -10)
        self.play(row2.animate.set_color(CRUSH), Wiggle(row2), run_time=0.8)
        huh = MathTex(r"0 = 1\ ?!", color=CRUSH).scale(1.1).next_to(r2, RIGHT)
        self.pop(huh)
        self.at("off the pancake")
        mini = VGroup(Line([-0.6, -1.2, 0], [0.6, 1.2, 0], color=KEEP, stroke_width=4),
                      Dot([0.5, 1.0, 0], color=GREEN_C), Dot([1.3, 0.4, 0], color=CRUSH)).move_to(RIGHT * 5.6 + DOWN * 0.1)
        self.play(FadeIn(mini), run_time=0.5)
        self.done(); self.clear()

    def exam(self):
        self.beat("exam")
        head = Text("On the test", weight=BOLD).scale(0.6).to_edge(UP, buff=0.3)
        A = Matrix(A35, h_buff=0.8).scale(0.72).move_to(LEFT * 3.3 + UP * 0.9)
        Al = MathTex("A").next_to(A, UP, buff=0.1)
        self.play(FadeIn(head), FadeIn(A), FadeIn(Al), run_time=0.6)
        self.at("Row reduce", lead=0.1)
        B = Matrix(B35, h_buff=0.8).scale(0.72).move_to(RIGHT * 3.3 + UP * 0.9)
        Bl = Text("reduced", color=GREY_B).scale(0.38).next_to(B, UP, buff=0.1)
        arr = Arrow(A.get_right(), B.get_left(), color=GREY_B)
        self.play(GrowArrow(arr), TransformFromCopy(A, B), FadeIn(Bl), run_time=1.0)
        self.at("Pivots give the rank", lead=0.1)
        piv = [B.get_entries()[i] for i in (0, 7, 13)]
        self.play(*[Circumscribe(p, color=KEEP, shape=Circle, run_time=1.0) for p in piv])
        self.play(*[B.get_columns()[j].animate.set_color(KEEP) for j in (0, 2, 3)], run_time=0.5)
        self.at("Theorem 5.9", lead=0.1)
        t59 = tag(r"\text{rank}(A)=\dim(\text{range}(L)) = 3", KEEP).scale(0.8).next_to(B, DOWN, buff=0.3)
        self.pop(t59)
        self.at("Range Method", lead=0.1)
        self.play(*[A.get_columns()[j].animate.set_color(KEEP) for j in (0, 2, 3)], run_time=0.6)
        warn = Text("range: pivot columns of the ORIGINAL A", color=KEEP).scale(0.42).next_to(A, DOWN, buff=0.3)
        self.pop(warn)
        self.at("not the reduced one")
        no = Cross(VGroup(*[B.get_columns()[j] for j in (0, 2, 3)]), stroke_color=CRUSH, stroke_width=4).scale(0.6)
        self.play(Create(no), run_time=0.4); self.play(FadeOut(no), run_time=0.3)
        self.at("Free variables give", lead=0.1)
        self.play(*[B.get_columns()[j].animate.set_color(CRUSH) for j in (1, 4)], run_time=0.5)
        self.at("Together: n", lead=0.1)
        eq = MathTex(r"\underbrace{3}_{\text{pivots}}", "+", r"\underbrace{2}_{\text{free}}", "=", r"\underbrace{5}_{n\,=\,\dim(\mathbb{R}^5)}").scale(0.95).to_edge(DOWN, buff=0.45)
        eq[0].set_color(KEEP); eq[2].set_color(CRUSH)
        self.play(Write(eq), run_time=1.2); self.sfx("ding", -12)
        self.done()
        self.exam_objs = (head, A, Al, B, Bl, arr, t59, warn, eq)

    def kernelmethod(self):
        self.beat("kernelmethod")
        head, A, Al, B, Bl, arr, t59, warn, eq = self.exam_objs
        self.play(*[FadeOut(m) for m in (A, Al, arr, t59, warn, eq, Bl)], B.animate.scale(0.85).move_to(UP * 2.3), run_time=0.7)
        km = Text("Kernel Method", weight=BOLD, color=CRUSH).scale(0.5).next_to(head, DOWN, buff=0.05)
        self.play(Transform(head, km), run_time=0.4)
        self.at("set one free variable to one", lead=0.1)
        v1l = MathTex(r"x_2=1,\ x_5=0").scale(0.8).move_to(LEFT * 3.6 + DOWN * 0.55)
        v2l = MathTex(r"x_2=0,\ x_5=1").scale(0.8).move_to(RIGHT * 2.0 + DOWN * 0.55)
        self.play(FadeIn(v1l), run_time=0.4)
        v1 = Matrix([[-2], [1], [0], [0], [0]]).scale(0.55).set_color(CRUSH).next_to(v1l, RIGHT, buff=0.3)
        self.play(LaggedStart(*[FadeIn(e, shift=DOWN * 0.2) for e in v1.get_entries()], lag_ratio=0.2), FadeIn(v1.get_brackets()), run_time=1.2)
        self.at("one basis vector", lead=0.1)
        self.play(FadeIn(v2l), run_time=0.4)
        v2 = Matrix([[-6], [0], [3], [-2], [1]]).scale(0.55).set_color(CRUSH).next_to(v2l, RIGHT, buff=0.3)
        self.play(LaggedStart(*[FadeIn(e, shift=DOWN * 0.2) for e in v2.get_entries()], lag_ratio=0.2), FadeIn(v2.get_brackets()), run_time=1.2)
        self.at("two vectors", lead=0.1)
        res = tag(r"\ker(L)=\text{span of these two}", CRUSH).scale(0.85).to_edge(DOWN, buff=0.35)
        self.play(Write(res), run_time=0.8); self.sfx("ding", -12)
        self.at("kernel's a plane")
        tick = Text("checked: A times each = 0", color=GREEN_C).scale(0.38).next_to(res, UP, buff=0.15)
        self.pop(tick)
        self.done(); self.clear()

    def transpose(self):
        self.beat("transpose")
        h = Text("Corollary 5.11", color=GREY_B).scale(0.45).to_edge(UP)
        self.play(FadeIn(h), run_time=0.4)
        A = Matrix(A35, h_buff=0.75).scale(0.65).move_to(LEFT * 3.2)
        self.play(FadeIn(A), run_time=0.5)
        self.at("rank of A equals", lead=0.1)
        eq = MathTex(r"\text{rank}(A) = \text{rank}(A^T)").scale(0.95).to_edge(DOWN, buff=0.8)
        self.play(Write(eq), run_time=1.0)
        self.at("Flip the matrix", lead=0.1)
        AT = Matrix(np.array(A35).T.tolist(), h_buff=0.75).scale(0.62).move_to(RIGHT * 3.2)
        self.play(TransformFromCopy(A, AT), run_time=1.2)
        self.at("this A has rank three", lead=0.1)
        c1 = tag(r"\text{rank}(A)=3", KEEP).scale(0.8).next_to(A, UP)
        c2 = tag(r"\text{rank}(A^T)=3", KEEP).scale(0.8).next_to(AT, UP)
        self.pop(c1); self.pop(c2)
        self.at("Its kernel is just zero", lead=0.1)
        k = tag(r"A^T\text{ is }5\times 3:\ \dim(\ker)=3-3=0", CRUSH).scale(0.8).next_to(AT, DOWN, buff=0.3)
        self.pop(k); self.sfx("ding", -12)
        self.done(); self.clear()

    def poly(self):
        self.beat("poly")
        p, top = self.build_press(label="d/dx", pos=LEFT * 3.4 + DOWN * 0.6, gap=1.6)
        self.play(FadeIn(p), run_time=0.5)
        self.at("P three to P two", lead=0.1)
        inp = MathTex("a x^3 + b x^2 + c x +", "d").scale(0.9).next_to(p, UP, buff=0.35)
        self.play(Write(inp), run_time=1.0)
        self.at("Crushed: the constants", lead=0.1)
        bin_ = VGroup(Rectangle(width=1.4, height=0.9, color=CRUSH), Text("crushed", color=CRUSH).scale(0.32)).move_to(RIGHT * 0.6 + DOWN * 2.3)
        bin_[1].next_to(bin_[0], DOWN, buff=0.08)
        self.play(FadeIn(bin_), inp[1].animate.set_color(CRUSH), run_time=0.4)
        self.sfx("slam", -10)
        self.play(inp[1].animate.move_to(bin_[0]), run_time=0.7)
        d1 = tag(r"\dim(\ker)=1", CRUSH).scale(0.75).next_to(bin_, RIGHT)
        self.pop(d1)
        self.at("every quadratic", lead=0.1)
        out = MathTex("3a x^2 + 2b x + c", color=KEEP).scale(0.9).move_to(RIGHT * 3.3 + UP * 0.9)
        self.play(TransformFromCopy(inp[0], out), run_time=0.9)
        d3 = tag(r"\dim(\text{range})=3", KEEP).scale(0.75).next_to(out, DOWN)
        self.pop(d3)
        self.at("One plus three", lead=0.1)
        eq = MathTex("1", "+", "3", "=", "4", r"=\dim(P_3)").scale(1.0).to_corner(UR).shift(DOWN * 0.3)
        eq[0].set_color(CRUSH); eq[2].set_color(KEEP)
        self.play(Write(eq), run_time=1.0); self.sfx("ding", -12)
        self.done(); self.clear()

    def next54(self):
        self.beat("next")
        h = Text("Coming up: 5.4", weight=BOLD).scale(0.6).to_edge(UP)
        self.play(FadeIn(h), run_time=0.4)
        self.at("just the zero vector", lead=0.2)
        c1 = MathTex(r"\ker(L)=\{\mathbf 0\}", r"\iff", r"\text{one-to-one}").scale(0.95).move_to(UP * 1.0)
        c1[0].set_color(CRUSH)
        dots = VGroup(*[Dot([x, -0.4, 0], radius=0.07, color=CRUSH) for x in np.linspace(-2, 2, 7)])
        self.play(Write(c1), FadeIn(dots), run_time=1.0)
        self.at("L is onto", lead=0.4)
        c2 = MathTex(r"\text{range}(L)=W", r"\iff", r"\text{onto}").scale(0.95).move_to(DOWN * 1.4)
        c2[0].set_color(KEEP)
        plate = Ellipse(width=4.6, height=0.9, color=GREY_B).move_to(DOWN * 2.6)
        pc = pancake(1.0).move_to(plate)
        self.play(Write(c2), FadeIn(plate), FadeIn(pc), run_time=0.8)
        self.play(pc.animate.stretch_to_fit_width(4.4), run_time=0.8)
        self.done(); self.clear()

    def callback(self):
        self.beat("callback")
        co = coaster(2.2).shift(DOWN * 0.9)
        pc = pancake(1.5).next_to(co, LEFT, buff=0.6).align_to(co[0], DOWN)
        stick = Line(DOWN * 0.45, UP * 0.45, color=CRUSH, stroke_width=6).next_to(pc, UP, buff=0.0)
        self.play(FadeIn(co), FadeIn(pc), run_time=0.6)
        self.at("ask the pancake question", lead=0.1)
        self.play(Create(stick), run_time=0.4)
        self.at("How big is one stick")
        q1 = Text("how big is one stick?", color=CRUSH).scale(0.55).move_to(UP * 2.3 + LEFT * 1.6)
        self.play(Write(q1), run_time=0.7)
        self.at("how many sticks")
        q2 = Text("how many sticks?", color=KEEP).scale(0.55).next_to(q1, DOWN, aligned_edge=LEFT).shift(RIGHT * 1.8)
        self.play(Write(q2), run_time=0.7)
        f = face(pc, k=1.6)
        self.play(FadeIn(f), run_time=0.3)
        wink = face(pc, wink=True, k=1.6)
        self.play(Transform(f, wink), run_time=0.25); self.sfx("pop", -8)
        self.done(pad=1.2)
        self.clear(rt=0.8)
