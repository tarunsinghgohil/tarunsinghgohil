"""Shared look for every SVG on the profile.

Palette: Jaipur at dusk. Deep indigo sky, pink sandstone, and the marigold
glow of lamps in the Hawa Mahal windows.

Fonts: Bricolage Grotesque (SIL OFL 1.1, see fonts/OFL.txt), subset to Basic
Latin and embedded as base64. GitHub serves README images through a proxy that
blocks external requests, so an embedded font is the only way to get the same
typography for every viewer.
"""

from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

FONT_DIR = Path(__file__).resolve().parent / "fonts"

NIGHT = "#17122B"      # background
NIGHT_2 = "#221B3D"    # panels, rules
LEVEL_0 = "#2A2344"    # empty cell
LEVEL_1 = "#5A3552"
LEVEL_2 = "#8C4863"
LEVEL_3 = "#C45C74"    # deep rose
LEVEL_4 = "#E7909A"    # Jaipur pink
MARIGOLD = "#F2B544"   # lamp glow, used once per graphic for the highlight
IVORY = "#F6EDE4"      # primary text
LILAC = "#A99BC4"      # secondary text

LEVELS = [LEVEL_0, LEVEL_1, LEVEL_2, LEVEL_3, LEVEL_4]

FONT_STACK = "'Bricolage', 'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"


@lru_cache(maxsize=None)
def _font_b64(weight: int) -> str:
    data = (FONT_DIR / f"bricolage-{weight}.woff2").read_bytes()
    return base64.b64encode(data).decode("ascii")


def font_face_css() -> str:
    """@font-face rules with the fonts inlined as data URIs."""
    rules = []
    for weight in (400, 700):
        rules.append(
            "@font-face{font-family:'Bricolage';font-style:normal;"
            f"font-weight:{weight};"
            f"src:url(data:font/woff2;base64,{_font_b64(weight)}) format('woff2');}}"
        )
    return "".join(rules)


def esc(text: str) -> str:
    """Escape text for SVG."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
