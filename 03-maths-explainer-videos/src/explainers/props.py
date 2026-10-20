"""Cartoon props shared by every explainer. Flat, chunky, readable at phone size.

Colour meaning is fixed across all videos: CRUSH (red) = what gets destroyed / kernel,
KEEP (yellow) = what survives / range.
"""
from manim import *

CRUSH, KEEP = "#ff5a5f", "#ffd166"
BG = "#0e1116"
INK = "#1b1f24"

def latex_template():
    # His TinyTeX has no babel-english; Manim's default preamble needs it. This one doesn't.
    return TexTemplate(preamble=r"\usepackage{amsmath}\usepackage{amssymb}")

def tag(tex, color=WHITE, scale=0.8):
    m = MathTex(tex, color=color).scale(scale)
    m.add_background_rectangle(color=BG, opacity=0.9, buff=0.12)
    return m

def burger(w=2.4):
    return _burger().scale(w / 2.4)          # drawn at 2.4 wide, then scaled whole so it keeps its shape

def _burger(w=2.4):
    bun_top = RoundedRectangle(width=w, height=0.8, corner_radius=0.38, fill_color="#e8a33d", fill_opacity=1, stroke_color=INK, stroke_width=3)
    seeds = VGroup(*[Ellipse(width=0.12, height=0.06, fill_color="#fff4d6", fill_opacity=1, stroke_width=0)
                     .move_to(bun_top.get_center() + [x * w / 2.6, 0.12 + 0.08 * ((i % 2) - 0.5), 0]) for i, x in enumerate([-0.6, -0.25, 0.1, 0.45, 0.75])])
    leaf_pts = [[-w / 2 - 0.05 + i * (w + 0.1) / 10, -0.08 * (-1) ** i, 0] for i in range(11)]
    lettuce = VMobject(stroke_color="#4caf50", stroke_width=10).set_points_smoothly(leaf_pts)
    cheese = Polygon([-w / 2, 0, 0], [w / 2, 0, 0], [w / 2 - 0.2, -0.22, 0], [0.1, -0.12, 0], [-w / 2 + 0.3, -0.25, 0],
                     fill_color="#ffcf33", fill_opacity=1, stroke_color=INK, stroke_width=2)
    patty = RoundedRectangle(width=w * 0.98, height=0.42, corner_radius=0.2, fill_color="#5b3a29", fill_opacity=1, stroke_color=INK, stroke_width=3)
    bun_bot = RoundedRectangle(width=w * 0.96, height=0.42, corner_radius=0.18, fill_color="#d98f2e", fill_opacity=1, stroke_color=INK, stroke_width=3)
    stack = VGroup(bun_top, lettuce, cheese, patty, bun_bot).arrange(DOWN, buff=-0.06)
    seeds.move_to(bun_top.get_center() + UP * 0.1)
    return VGroup(stack, seeds)

def pancake(w=2.4):
    b = burger(w)
    return b.stretch(0.3, dim=1).stretch(1.35, dim=0)

def basketball(r=0.9):
    ball = Circle(radius=r, fill_color="#f28c28", fill_opacity=1, stroke_color=INK, stroke_width=4)
    seams = VGroup(Line(ball.get_left(), ball.get_right()), Line(ball.get_top(), ball.get_bottom()),
                   ArcBetweenPoints(ball.get_top() + LEFT * r * 0.55, ball.get_bottom() + LEFT * r * 0.55, angle=0.9),
                   ArcBetweenPoints(ball.get_top() + RIGHT * r * 0.55, ball.get_bottom() + RIGHT * r * 0.55, angle=-0.9)).set_stroke(INK, 3)
    return VGroup(ball, seams)

def phone(h=1.8):
    body = RoundedRectangle(width=h * 0.5, height=h, corner_radius=0.14, fill_color="#2b2f36", fill_opacity=1, stroke_color="#9aa4b1", stroke_width=3)
    screen = RoundedRectangle(width=h * 0.42, height=h * 0.86, corner_radius=0.08, fill_color="#3c7be0", fill_opacity=1, stroke_width=0)
    return VGroup(body, screen)

def coaster(h=1.8):
    p = phone(h).rotate(PI / 2).stretch(0.55, dim=1)
    crack = VMobject(stroke_color=WHITE, stroke_width=2).set_points_as_corners(
        [p.get_center() + v for v in ([-0.5, 0.1, 0], [-0.15, -0.05, 0], [0.05, 0.12, 0], [0.4, -0.08, 0], [0.6, 0.05, 0])])
    cup = VGroup(Rectangle(width=0.55, height=0.7, fill_color="#f5f5f5", fill_opacity=1, stroke_color=INK, stroke_width=3),
                 Ellipse(width=0.55, height=0.16, fill_color="#6b3e26", fill_opacity=1, stroke_color=INK, stroke_width=2))
    cup[1].move_to(cup[0].get_top())
    cup.next_to(p, UP, buff=-0.08)
    return VGroup(p, crack, cup)

def press(width=3.6, gap=1.6, label="PANCAKE 3000"):
    base = RoundedRectangle(width=width, height=0.35, corner_radius=0.08, fill_color="#b8c2cc", fill_opacity=1, stroke_color=INK, stroke_width=3)
    top = base.copy().set_fill("#d7dee5").shift(UP * (gap + 0.35))
    posts = VGroup(*[Rectangle(width=0.18, height=gap + 1.3, fill_color="#8792a0", fill_opacity=1, stroke_color=INK, stroke_width=2)
                     .move_to(base.get_center() + [s * (width / 2 - 0.12), (gap + 1.3) / 2, 0]) for s in (-1, 1)])
    beam = Rectangle(width=width, height=0.25, fill_color="#8792a0", fill_opacity=1, stroke_color=INK, stroke_width=2).next_to(posts, UP, buff=-0.25)
    handle = Line(beam.get_right(), beam.get_right() + [0.9, 0.7, 0], stroke_width=10, color="#c0392b")
    name = Text(label, weight=BOLD, color=INK).scale(0.28).move_to(top)
    return VGroup(posts, beam, base, top, handle, name)

def face(m, wink=False, k=1.0):
    """Big cartoon eyes that sit ON TOP of a prop (readable even on a flat pancake). wink closes the right one."""
    c, w = m.get_top(), m.width
    r = 0.13 * k * max(0.6, w / 2)
    eye = lambda x: VGroup(Circle(radius=r, fill_color=WHITE, fill_opacity=1, stroke_color=INK, stroke_width=3),
                           Dot(radius=r * 0.45, color=INK).shift(RIGHT * r * 0.25)).move_to(c + [x, r * 0.8, 0])
    eye_l = eye(-w * 0.18)
    eye_r = (Arc(radius=r, start_angle=PI, angle=-PI, stroke_color=WHITE, stroke_width=5).move_to(c + [w * 0.18, r * 0.8, 0])
             if wink else eye(w * 0.18))
    return VGroup(eye_l, eye_r)

def iso_cube(s=1.2):
    """A cube drawn in 2D with its three directions coloured: height red (crushed), width and depth yellow."""
    o = ORIGIN; x = np.array([s, 0, 0]); y = np.array([0, s, 0]); z = np.array([s * 0.55, s * 0.4, 0])
    face_ = lambda a, b, c_, d, col: Polygon(a, b, c_, d, fill_color=col, fill_opacity=1, stroke_color=INK, stroke_width=3)
    front = face_(o, o + x, o + x + y, o + y, "#3a6ea5")
    top = face_(o + y, o + x + y, o + x + y + z, o + y + z, "#5b8fc7")
    side = face_(o + x, o + x + z, o + x + y + z, o + x + y, "#2b5582")
    edges = VGroup(Line(o, o + x, color=KEEP, stroke_width=8), Line(o + x, o + x + z, color=KEEP, stroke_width=8),
                   Line(o, o + y, color=CRUSH, stroke_width=8))
    return VGroup(front, top, side, edges).move_to(ORIGIN)

def dims(m, crushed=False):
    """Width, depth (kept, yellow) and height (red) arrows around a prop."""
    w = Arrow(m.get_corner(DL) + DOWN * 0.25, m.get_corner(DR) + DOWN * 0.25, buff=0, color=KEEP, stroke_width=6)
    d = Arrow(m.get_corner(DR) + DOWN * 0.25, m.get_corner(DR) + DOWN * 0.25 + [0.7, 0.55, 0], buff=0, color=KEEP, stroke_width=6)
    if crushed:
        h = Dot(m.get_left() + LEFT * 0.35, radius=0.1, color=CRUSH)
    else:
        h = Arrow(m.get_corner(DL) + LEFT * 0.3, m.get_corner(UL) + LEFT * 0.3, buff=0, color=CRUSH, stroke_width=6)
    return VGroup(w, d, h)
