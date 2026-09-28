"""Build profile/banner.svg.

The facade on the right is the Hawa Mahal, Jaipur's palace of 953 windows,
drawn with the same rounded squares GitHub uses for its contribution graph.

Run once after editing the text below:
    python3 scripts/banner.py
"""

from __future__ import annotations

import random
from pathlib import Path

from theme import (
    FONT_STACK, IVORY, LEVEL_1, LEVEL_2, LEVEL_3, LEVEL_4, LILAC, MARIGOLD,
    NIGHT, esc, font_face_css,
)

# ---- Edit your text here -------------------------------------------------
NAME = "Tarun Singh Gohil"
ROLE = "Full-stack & AI engineer"
PITCH = [
    "Python and Django backends, React and TypeScript frontends,",
    "and LLM features built to hold up in production.",
]
STATUS = "Jaipur, the Pink City. Open to full-stack and AI roles."
# --------------------------------------------------------------------------

W, H = 1200, 380
CELL, GAP = 9, 3
PITCH_PX = CELL + GAP
COLS, ROWS = 40, 22
ORIGIN_X = W - 44 - COLS * PITCH_PX + GAP   # right-aligned facade
BASE_Y = H - 34                              # ground line

# Tiers of the facade: (first row, last row, first col, last col), rows counted from the ground.
TIERS = [
    (0, 6, 0, 39),
    (7, 10, 2, 37),
    (11, 13, 6, 33),
    (14, 16, 10, 29),
    (17, 18, 14, 25),
    (19, 20, 17, 22),
    (21, 21, 19, 20),
]


def facade_cells() -> dict[tuple[int, int], str]:
    """Return {(row, col): kind} where kind is 'wall', 'cornice', 'dome' or 'lamp'."""
    cells: dict[tuple[int, int], str] = {}
    for r0, r1, c0, c1 in TIERS:
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                cells[(r, c)] = "cornice" if r == r1 and r1 != 21 else "wall"
    # Small domes (chhatris) on the shoulders of each tier.
    for (r0, r1, c0, c1), (_, _, n0, n1) in zip(TIERS, TIERS[1:]):
        row = r1 + 1
        for c in (c0, c0 + 1, c1 - 1, c1):
            if c < n0 or c > n1:
                cells[(row, c)] = "dome"
    # Arched entrance at the centre of the ground floor.
    for r in range(0, 3):
        for c in range(18, 22):
            cells.pop((r, c), None)
    for c in (19, 20):
        cells.pop((3, c), None)
    # A few lit windows.
    rng = random.Random(953)
    walls = [k for k, v in cells.items() if v == "wall" and 2 <= k[0] <= 18]
    for key in rng.sample(walls, 14):
        cells[key] = "lamp"
    return cells


def cell_colour(kind: str, row: int, col: int, rng: random.Random) -> str:
    if kind == "lamp":
        return MARIGOLD
    if kind == "cornice":
        return LEVEL_4
    if kind == "dome":
        return LEVEL_3
    # Brighter towards the centre, like sandstone catching the last light.
    centre = 1 - abs(col - 19.5) / 20
    x = rng.random() * 0.7 + centre * 0.45
    if x > 0.85:
        return LEVEL_4
    if x > 0.6:
        return LEVEL_3
    if x > 0.35:
        return LEVEL_2
    return LEVEL_1


def build() -> str:
    rng = random.Random(1799)  # Hawa Mahal was completed in 1799
    cells = facade_cells()

    rows_svg = []
    lamps_svg = []
    for row in range(ROWS + 1):
        rects = []
        for col in range(COLS):
            kind = cells.get((row, col))
            if not kind:
                continue
            x = ORIGIN_X + col * PITCH_PX
            y = BASE_Y - (row + 1) * PITCH_PX + GAP
            colour = cell_colour(kind, row, col, rng)
            rect = f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{colour}"/>'
            if kind == "lamp":
                delay = round(rng.uniform(0, 4), 2)
                lamps_svg.append(
                    f'<rect class="lamp" style="animation-delay:{2 + delay}s" x="{x}" y="{y}" '
                    f'width="{CELL}" height="{CELL}" rx="2" fill="{MARIGOLD}"/>'
                )
            else:
                rects.append(rect)
        if rects:
            rows_svg.append(
                f'<g class="row" style="animation-delay:{row * 0.07:.2f}s">{"".join(rects)}</g>'
            )

    facade_w = COLS * PITCH_PX - GAP
    glow_cx = ORIGIN_X + facade_w / 2
    lamp_glow_delay = (ROWS + 1) * 0.07

    left = 64
    pitch_lines = "".join(
        f'<text x="{left}" y="{252 + i * 30}" class="pitch">{esc(line)}</text>'
        for i, line in enumerate(PITCH)
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="title desc">
<title id="title">{esc(NAME)}, {esc(ROLE)}</title>
<desc id="desc">{esc(' '.join(PITCH))} {esc(STATUS)} Illustration: the Hawa Mahal in Jaipur drawn as a contribution graph.</desc>
<style>
{font_face_css()}
text{{font-family:{FONT_STACK}}}
.name{{font-size:62px;font-weight:700;fill:{IVORY};letter-spacing:-1.2px}}
.role{{font-size:28px;font-weight:400;fill:{LEVEL_4}}}
.pitch{{font-size:19px;font-weight:400;fill:{LILAC}}}
.status{{font-size:16px;font-weight:400;fill:{IVORY};opacity:.82}}
.row{{animation:rise .6s cubic-bezier(.2,.7,.2,1) both}}
.lamp{{animation:flicker 5s ease-in-out infinite alternate}}
.lamps{{animation:rise .8s ease-out both;animation-delay:{lamp_glow_delay:.2f}s}}
.dot{{animation:pulse 2.4s ease-in-out infinite}}
@keyframes rise{{from{{opacity:0;transform:translateY(6px)}}to{{opacity:1;transform:none}}}}
@keyframes flicker{{0%,60%{{opacity:1}}80%{{opacity:.55}}100%{{opacity:.9}}}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.35}}}}
@media (prefers-reduced-motion:reduce){{.row,.lamp,.lamps,.dot{{animation:none}}}}
</style>
<defs>
<radialGradient id="dusk" cx="{glow_cx / W:.3f}" cy="0.95" r="0.55">
<stop offset="0" stop-color="{LEVEL_3}" stop-opacity=".28"/>
<stop offset="1" stop-color="{LEVEL_3}" stop-opacity="0"/>
</radialGradient>
</defs>
<rect width="{W}" height="{H}" rx="18" fill="{NIGHT}"/>
<rect width="{W}" height="{H}" rx="18" fill="url(#dusk)"/>
<g>{"".join(rows_svg)}</g>
<g class="lamps">{"".join(lamps_svg)}</g>
<rect x="{ORIGIN_X - 16}" y="{BASE_Y + 2}" width="{facade_w + 32}" height="2" rx="1" fill="{LEVEL_2}" opacity=".7"/>
<text x="{left}" y="146" class="name">{esc(NAME)}</text>
<text x="{left}" y="194" class="role">{esc(ROLE)}</text>
{pitch_lines}
<circle class="dot" cx="{left + 6}" cy="{H - 50}" r="5" fill="{MARIGOLD}"/>
<text x="{left + 22}" y="{H - 44}" class="status">{esc(STATUS)}</text>
</svg>
"""


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "profile" / "banner.svg"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size / 1024:.1f} KB)")
