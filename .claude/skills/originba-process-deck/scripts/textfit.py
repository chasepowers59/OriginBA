"""Fit text to a box by measuring it, so a label can never run past its shape.

Both builders (the pptx process deck and the draw.io converter) call `fit()` for every node label:
it returns the largest point size, no larger than the one asked for, at which the longest unbreakable
word fits the box's inner width AND the wrapped lines fit its height. Below `MIN_PT` it raises, so a
box that is simply too small fails the build instead of shipping an overflow (the defect Chase caught
on 2026-09-28: D1_USAGE_SCALAR_DTL_RPT_CURR spilling into the page on both sides of its box).

Measurement is Arial from the system font files, the face both outputs render with.
"""
from __future__ import annotations

import math
from functools import lru_cache

from PIL import ImageFont

FONTS = {True: "/System/Library/Fonts/Supplemental/Arial Bold.ttf", False: "/System/Library/Fonts/Supplemental/Arial.ttf"}
MIN_PT = 7.0
PT_PER_IN = 72.0


class DoesNotFit(ValueError):
    pass


@lru_cache(maxsize=None)
def _font(pt: float, bold: bool):
    return ImageFont.truetype(FONTS[bold], size=max(1, int(round(pt * 4))))   # measured at 4x for precision


def width_in(text: str, pt: float, bold: bool) -> float:
    """Rendered width of `text` in inches at `pt` points."""
    return _font(pt, bold).getlength(text) / 4.0 / PT_PER_IN


def lines_needed(text: str, pt: float, bold: bool, inner_w: float) -> int:
    """Greedy word wrap, the way the renderers do it."""
    lines, cur = 1, ""
    for word in text.split():
        cand = (cur + " " + word).strip()
        if width_in(cand, pt, bold) <= inner_w or not cur:
            cur = cand
        else:
            lines += 1; cur = word
    return lines


def fit(paras: list[tuple[str, float, bool]], inner_w: float, inner_h: float | None, where: str) -> list[float]:
    """paras: (text, requested_pt, bold) per paragraph. Returns one point size per paragraph, each no larger than
    requested, scaled down together until every longest word fits the width and the stacked lines fit the height."""
    scale = 1.0
    while True:
        sizes = [p[1] * scale for p in paras]
        wide_ok = all(width_in(w, s, p[2]) <= inner_w for p, s in zip(paras, sizes) for w in p[0].split())
        if inner_h is None:
            tall_ok = True
        else:
            height = sum(lines_needed(p[0], s, p[2], inner_w) * s * 1.2 / PT_PER_IN for p, s in zip(paras, sizes))
            tall_ok = height <= inner_h
        if wide_ok and tall_ok:
            return sizes
        if min(sizes) <= MIN_PT:
            raise DoesNotFit(f"{where}: text does not fit its box even at {MIN_PT}pt; widen the box or shorten the text")
        scale *= 0.94
