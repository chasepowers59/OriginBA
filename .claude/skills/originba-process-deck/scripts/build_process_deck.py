#!/usr/bin/env python3
"""Build an Origin-styled process deck (the DV_App_Overview look) from a JSON spec, on the
reference deck's own layouts, so the blue gradient background, fonts and footer are the real ones.

    python3 .claude/skills/originba-process-deck/scripts/build_process_deck.py spec.json out.pptx

Slide types (see SKILL.md and examples/sample_spec.json): title, section, statement, process,
roadmap, cards, table, bullets. A process slide is a grid of cream nodes (col, row) joined by
cream arrows; node kinds: step (cream), manual (cream with an orange tag: by hand, a failure, a constraint), accent (orange pill), card (white sheet with
a green header), note (small cream text).
"""
from __future__ import annotations

import copy
import json
import pathlib
import sys

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from textfit import fit   # noqa: E402  every label is measured against its box; an overflow fails the build

HERE = pathlib.Path(__file__).resolve().parent
TEMPLATE = HERE.parent / "assets" / "origin_blue_template.pptx"
# the reference deck's palette (theme + slide fills), measured 2026-09-28
BLUE, CREAM, GREY, ORANGE, TAN, GREEN, WHITE = "0B3D7A", "F5EFE9", "4C5D69", "FFA418", "DBD3CC", "1D6F42", "FFFFFF"
FOOTER = "@2026, Origin Utility, Inc / Proprietary & Confidential / Internal Use Only"
# the process grid of the reference: 4 columns of 4.30" nodes at 5.36" pitch, rows 2.0" apart
GRID_X0, GRID_PITCH_X, NODE_W, NODE_H = 0.81, 5.36, 4.30, 1.55
GRID_Y0, GRID_PITCH_Y = 2.20, 2.05
LAYOUT = {"title": 0, "section": 2, "statement": 11, "blank": 9}


def rgb(h: str) -> RGBColor:
    return RGBColor.from_string(h)


def _clear_slides(prs: Presentation) -> None:
    sldIdLst = prs.slides._sldIdLst
    for sldId in list(sldIdLst):
        prs.part.drop_rel(sldId.rId)
        sldIdLst.remove(sldId)


def _text(shape, runs, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE, margin=0.12):
    """runs: list of paragraphs; each paragraph a list of (text, size_pt, color, bold)."""
    tf = shape.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(margin); tf.margin_top = tf.margin_bottom = Inches(0.06)
    first = True
    for para in runs:
        p = tf.paragraphs[0] if first else tf.add_paragraph(); first = False
        p.alignment = align; p.space_after = Pt(6)
        for text, size, color, bold in para:
            r = p.add_run(); r.text = text; r.font.size = Pt(size); r.font.bold = bold; r.font.color.rgb = rgb(color)


def _box(slide, x, y, w, h, fill, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid(); s.fill.fore_color.rgb = rgb(fill); s.line.fill.background(); s.shadow.inherit = False
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = radius
    return s


def _title(slide, text, y=0.42, size=60):
    t = slide.shapes.add_textbox(Inches(0.81), Inches(y), Inches(20.4), Inches(1.05))
    _text(t, [[(text, size if len(text) <= 40 else 46, CREAM, False)]], anchor=MSO_ANCHOR.TOP, margin=0.0)


def _footer(slide, text):
    t = slide.shapes.add_textbox(Inches(5.52), Inches(11.71), Inches(10.95), Inches(0.5))
    _text(t, [[(text, 10.5, CREAM, True)]], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.TOP, margin=0.0)


def _kicker(slide, label):
    if not label:
        return
    b = _box(slide, 0.81, 1.55, 0.6, 0.5, ORANGE, radius=0.3)
    _text(b, [[(label, 16, BLUE, True)]], align=PP_ALIGN.CENTER, margin=0.0)


def _arrow_segments(slide, pts, color=CREAM, width_pt=2.75):
    """Polyline of straight connectors, arrowhead on the last segment."""
    for i in range(len(pts) - 1):
        (x1, y1), (x2, y2) = pts[i], pts[i + 1]
        c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
        c.line.color.rgb = rgb(color); c.line.width = Pt(width_pt)
        if i == len(pts) - 2:
            ln = c.line._get_or_add_ln()
            tail = etree.SubElement(ln, "{http://schemas.openxmlformats.org/drawingml/2006/main}tailEnd")
            tail.set("type", "triangle"); tail.set("w", "med"); tail.set("len", "med")


def _node_rect(n):
    x = n.get("x", GRID_X0 + n.get("col", 0) * GRID_PITCH_X); y = n.get("y", GRID_Y0 + n.get("row", 0) * GRID_PITCH_Y)
    return x, y, n.get("w", NODE_W), n.get("h", NODE_H)


def _draw_node(slide, n):
    x, y, w, h = _node_rect(n); kind = n.get("kind", "step")
    title, body = n.get("title", ""), n.get("body", "")
    if kind == "accent":
        ph = n.get("h", 0.62 if len(title) <= 40 else 0.9)
        b = _box(slide, x, y, w, ph, ORANGE, radius=0.5)
        _text(b, [[(title, 17, BLUE, True)]], align=PP_ALIGN.CENTER, margin=0.1)
    elif kind == "card":
        h = n.get("h", 2.9); w = n.get("w", 2.28)
        _box(slide, x, y, w, h, WHITE, radius=0.08)
        _box(slide, x, y, w, 0.36, GREEN, shape=MSO_SHAPE.ROUND_2_SAME_RECTANGLE, radius=0.3)
        grid = slide.shapes.add_table(3, 4, Inches(x + 0.14), Inches(y + 0.5), Inches(w - 0.28), Inches(0.96)).table
        for r in grid.rows:
            r.height = Inches(0.32)
            for c in r.cells:
                c.fill.solid(); c.fill.fore_color.rgb = rgb(WHITE); c.text = ""
        lbl = slide.shapes.add_textbox(Inches(x + 0.06), Inches(y + 1.6), Inches(w - 0.12), Inches(h - 1.7))
        _text(lbl, [[(title, 17, BLUE, True)]] + ([[(body, 12, GREY, False)]] if body else []), align=PP_ALIGN.CENTER, margin=0.05)
    elif kind == "note":
        t = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        _text(t, [[(title, 16, CREAM, True)]] + ([[(body, 14, CREAM, False)]] if body else []), anchor=MSO_ANCHOR.TOP, margin=0.0)
    else:
        b = _box(slide, x, y, w, h, CREAM)
        paras = [[(title, 25 if len(title) < 22 else 21, BLUE, True)]]
        if body:
            paras.append([(body, 20 if len(body) < 60 else 16, GREY, False)])
        _text(b, paras)
        if kind == "manual":   # same container as every other node; the orange tag carries the meaning
            _tag(slide, x + w - 0.1, y - 0.42, n.get("tag", "by hand"))


def _tag(slide, right, y, label):
    """A small orange pill anchored by its right edge: by hand, failure, waits, human."""
    w = 0.3 + 0.1 * len(label)
    b = _box(slide, right - w, y, w, 0.34, ORANGE, radius=0.5)
    _text(b, [[(label, 11, BLUE, True)]], align=PP_ALIGN.CENTER, margin=0.04)
    return b


def _edge(slide, nodes, a, b, via=None):
    """via: an optional [x, y] waypoint the arrow bends through (to route around other nodes)."""
    ax, ay, aw, ah = _node_rect(nodes[a]); bx, by, bw, bh = _node_rect(nodes[b])
    if via:
        vx, vy = via
        ah_ = nodes[a].get("h", 0.62 if nodes[a].get("kind") == "accent" else ah)
        start = (ax + aw / 2, ay + ah_ + 0.1) if vy > ay else (ax + aw / 2, ay - 0.1)
        if vy < by or vy > by + bh:   # the waypoint is above or below B: come straight down (or up) into its middle
            end = (bx + bw / 2, by - 0.1) if vy < by else (bx + bw / 2, by + bh + 0.1)
            if vx and abs(vx - start[0]) > 0.5:   # leave A sideways and run the vertical in the channel at vx (around whatever sits above A)
                side = (ax + aw + 0.1, ay + ah_ / 2) if vx > ax else (ax - 0.1, ay + ah_ / 2)
                _arrow_segments(slide, [side, (vx, side[1]), (vx, vy), (end[0], vy), end]); return
            _arrow_segments(slide, [start, (start[0], vy), (end[0], vy), end]); return
        end = (bx - 0.1, by + bh / 2) if vx < bx else (bx + bw + 0.1, by + bh / 2)
        _arrow_segments(slide, [start, (start[0], vy), (vx, vy), (vx, end[1]), end] if abs(vx - start[0]) > 0.05 else [start, (start[0], vy), end])
        return
    ah = nodes[a].get("h", 0.62 if nodes[a].get("kind") == "accent" else ah); bh = nodes[b].get("h", 0.62 if nodes[b].get("kind") == "accent" else bh)
    acx, acy, bcx, bcy = ax + aw / 2, ay + ah / 2, bx + bw / 2, by + bh / 2
    gap = 0.1
    if abs(acy - bcy) < 0.3:                                   # same row: straight, left to right or right to left
        pts = [(ax + aw + gap, acy), (bx - gap, bcy)] if bx > ax else [(ax - gap, acy), (bx + bw + gap, bcy)]
    elif abs(acx - bcx) < 0.3:                                 # same column: straight down or up
        pts = [(acx, ay + ah + gap), (bcx, by - gap)] if by > ay else [(acx, ay - gap), (bcx, by + bh + gap)]
    elif by > ay:                                              # elbow: down from A, across into B's side
        side = bx - gap if bx > ax else bx + bw + gap
        pts = [(acx, ay + ah + gap), (acx, bcy), (side, bcy)]
    else:                                                      # elbow: up from A, across into B's side
        side = bx - gap if bx > ax else bx + bw + gap
        pts = [(acx, ay - gap), (acx, bcy), (side, bcy)]
    _arrow_segments(slide, pts)


def slide_process(prs, s, footer):
    sl = prs.slides.add_slide(prs.slide_layouts[LAYOUT["blank"]])
    _title(sl, s["title"]); _kicker(sl, s.get("kicker")); _footer(sl, footer)
    nodes = {n["id"]: n for n in s.get("nodes", [])}
    for n in s.get("nodes", []):
        _draw_node(sl, n)
    for e in s.get("edges", []):
        if isinstance(e, dict):
            _edge(sl, nodes, e["from"], e["to"], e.get("via"))
        else:
            _edge(sl, nodes, e[0], e[1])
    if s.get("proofs"):   # a strip of white pills: what the stage proves before it counts as done
        t = sl.shapes.add_textbox(Inches(0.81), Inches(9.35), Inches(3.0), Inches(0.5))
        _text(t, [[("Proofs", 16, CREAM, True)]], margin=0.0)
        px = 2.4
        for p in s["proofs"]:
            w = 0.25 + 0.115 * len(p)
            _chip(sl, px, 9.3, w, 0.55, p, fill=WHITE, size=14); px += w + 0.25
    if s.get("missing"):   # the by-hand counterpart of proofs: a strip of tan pills, what the old way never had
        t = sl.shapes.add_textbox(Inches(0.81), Inches(9.35), Inches(3.0), Inches(0.5))
        _text(t, [[("Missing", 16, CREAM, True)]], margin=0.0)
        px = 2.4
        for p in s["missing"]:
            w = 0.25 + 0.115 * len(p)
            _chip(sl, px, 9.3, w, 0.55, p, fill=WHITE, size=14); px += w + 0.25
    if s.get("legend"):
        t = sl.shapes.add_textbox(Inches(0.81), Inches(10.75), Inches(20), Inches(0.6))
        _text(t, [[(s["legend"], 14, CREAM, False)]], anchor=MSO_ANCHOR.TOP, margin=0.0)
    if s.get("notes"):
        sl.notes_slide.notes_text_frame.text = s["notes"]
    return sl


def slide_roadmap(prs, s, footer):
    sl = prs.slides.add_slide(prs.slide_layouts[LAYOUT["blank"]])
    _title(sl, s["title"]); _kicker(sl, s.get("kicker")); _footer(sl, footer)
    steps = s["steps"]; n = len(steps); pitch = 4.15 if n <= 5 else (20.4 / n); w = min(3.79, pitch - 0.36)
    for i, st in enumerate(steps):
        x = 0.81 + i * pitch; current = st.get("current", False)
        b = _box(sl, x, 6.67, w, 3.1, ORANGE if current else CREAM, radius=0.1)
        paras = [[(st["title"], 24, BLUE, True)]]
        if st.get("owner"):
            paras.append([(st["owner"], 18, BLUE if current else GREY, False)])
        if st.get("body"):
            paras.append([(st["body"], 18, BLUE if current else GREY, False)])
        _text(b, paras, anchor=MSO_ANCHOR.TOP)
        c = sl.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x + w / 2 - 0.45), Inches(5.32), Inches(0.9), Inches(0.9))
        c.fill.solid(); c.fill.fore_color.rgb = rgb(CREAM if current else ORANGE); c.line.fill.background(); c.shadow.inherit = False
        _text(c, [[(str(i + 1), 24, BLUE, True)]], align=PP_ALIGN.CENTER, margin=0.0)
    if s.get("intro"):
        t = sl.shapes.add_textbox(Inches(0.81), Inches(2.3), Inches(20), Inches(2.6))
        _text(t, [[(s["intro"], 24, CREAM, False)]], anchor=MSO_ANCHOR.TOP, margin=0.0)
    return sl


def slide_cards(prs, s, footer):
    sl = prs.slides.add_slide(prs.slide_layouts[LAYOUT["blank"]])
    _title(sl, s["title"]); _kicker(sl, s.get("kicker")); _footer(sl, footer)
    cards = s["cards"]; cols = s.get("cols", 3 if len(cards) > 4 else min(len(cards), 4)); rows = -(-len(cards) // cols)
    w = (20.4 - (cols - 1) * 0.5) / cols
    def _card_h(c):   # estimated from wrapped lines at the card's width, so long lines never spill past the box
        cpl = max(int((w - 0.7) * 6.4), 20)   # 22pt Calibri: about 6.4 characters per inch
        lines = sum(-(-len(line) // cpl) for line in c.get("lines", []))
        return 1.35 + 0.42 * lines + 0.12 * len(c.get("lines", [])) + (2.1 if c.get("stat") else 0.0)
    h = min((8.9 - (rows - 1) * 0.5) / rows, max(_card_h(c) for c in cards))   # sized to the fullest card, never taller than the page allows
    top = 2.0 + max(0.0, (8.9 - rows * h - (rows - 1) * 0.5) / 2)   # the block sits centred in the body, not stranded at the top
    for i, c in enumerate(cards):
        x = 0.81 + (i % cols) * (w + 0.5); y = top + (i // cols) * (h + 0.5)
        b = _box(sl, x, y, w, h, ORANGE if c.get("accent") else CREAM, radius=0.08)
        paras = []
        if c.get("stat"):
            paras += [[(c["stat"], 60, BLUE, True)], [(c.get("stat_label", ""), 18, GREY, False)]]
        paras += [[(c["heading"], 30, BLUE, True)]] + [[(line, 22, BLUE if c.get("accent") else GREY, False)] for line in c.get("lines", [])]
        _text(b, paras, anchor=MSO_ANCHOR.TOP, margin=0.35)
    return sl


def slide_bullets(prs, s, footer):
    sl = prs.slides.add_slide(prs.slide_layouts[LAYOUT["blank"]])
    _title(sl, s["title"]); _kicker(sl, s.get("kicker")); _footer(sl, footer)
    cols = s["columns"]; w = (20.4 - (len(cols) - 1) * 0.5) / len(cols)
    h = min(8.9, 1.6 + 1.05 * max(len(c["items"]) for c in cols))   # sized to the longest column
    for i, c in enumerate(cols):
        x = 0.81 + i * (w + 0.5)
        b = _box(sl, x, 2.0, w, h, CREAM, radius=0.08)
        paras = [[(c["heading"], 30, BLUE, True)]] + [[("•  " + it, 21, GREY, False)] for it in c["items"]]
        _text(b, paras, anchor=MSO_ANCHOR.TOP, margin=0.35)
    return sl


def slide_table(prs, s, footer):
    sl = prs.slides.add_slide(prs.slide_layouts[LAYOUT["blank"]])
    _title(sl, s["title"]); _kicker(sl, s.get("kicker")); _footer(sl, footer)
    cols, rows = s["columns"], s["rows"]
    rh = min(s.get("row_h", 0.85), 8.9 / (len(rows) + 1))   # row_h lets a short, dense table fill the body
    shape = sl.shapes.add_table(len(rows) + 1, len(cols), Inches(0.81), Inches(2.0), Inches(20.4), Inches(rh * (len(rows) + 1)))
    tbl = shape.table
    widths = s.get("widths") or [20.4 / len(cols)] * len(cols)
    for j, wd in enumerate(widths):
        tbl.columns[j].width = Inches(wd)
    for j, c in enumerate(cols):
        cell = tbl.cell(0, j); cell.fill.solid(); cell.fill.fore_color.rgb = rgb(BLUE)
        cell.text = ""; _text(cell, [[(c, 22, CREAM, True)]], margin=0.15)
    for i, row in enumerate(rows, start=1):
        for j, v in enumerate(row):
            cell = tbl.cell(i, j); cell.fill.solid(); cell.fill.fore_color.rgb = rgb(CREAM)
            cell.text = ""; _text(cell, [[(str(v), s.get("font", 19), GREY if j else BLUE, j == 0)]], margin=0.15)
    for i, r in enumerate(tbl.rows):
        r.height = Inches(min(rh, 0.85) if i == 0 else rh)   # the header never grows with the body rows
    return sl


def slide_title(prs, s, footer):
    sl = prs.slides.add_slide(prs.slide_layouts[LAYOUT["title"]])
    ph = sl.placeholders[0]; ph.text = s["title"]
    if s.get("subtitle"):
        t = sl.shapes.add_textbox(Inches(4.31), Inches(8.3), Inches(12.68), Inches(1.0))
        _text(t, [[(s["subtitle"], 24, CREAM, False)]], align=PP_ALIGN.CENTER, margin=0.0)
    return sl


def slide_section(prs, s, footer):
    sl = prs.slides.add_slide(prs.slide_layouts[LAYOUT["section"]])
    sl.placeholders[0].text = s["title"]
    for ph in sl.placeholders:
        if ph.placeholder_format.idx == 10:
            ph.text = s.get("kicker", "")
    return sl


def slide_statement(prs, s, footer):
    sl = prs.slides.add_slide(prs.slide_layouts[LAYOUT["blank"]])
    _title(sl, s["title"], y=1.2, size=44)
    t = sl.shapes.add_textbox(Inches(0.81), Inches(3.4), Inches(20.4), Inches(7))
    _text(t, [[(line, 26, CREAM, False)] for line in s["lines"]], anchor=MSO_ANCHOR.TOP, margin=0.0)
    _footer(sl, footer)
    return sl


def _chip(slide, x, y, w, h, text, fill=WHITE, color=BLUE, size=16, bold=False):
    b = _box(slide, x, y, w, h, fill, radius=0.35)
    _text(b, [[(text, size, color, bold)]], align=PP_ALIGN.CENTER, margin=0.08)
    return b


def slide_layers(prs, s, footer):
    """Stacked bands, one per layer, each with a label and a row of chips; a thin arrow between bands."""
    sl = prs.slides.add_slide(prs.slide_layouts[LAYOUT["blank"]])
    _title(sl, s["title"]); _kicker(sl, s.get("kicker")); _footer(sl, footer)
    bands = s["bands"]; gap = 0.45; h = min(1.75, (8.9 - gap * (len(bands) - 1)) / len(bands)); y = 2.0
    for i, b in enumerate(bands):
        box = _box(sl, 0.81, y, 20.4, h, CREAM, radius=0.1)
        lab = sl.shapes.add_textbox(Inches(1.1), Inches(y), Inches(4.4), Inches(h))
        _text(lab, [[(b["label"], 24, BLUE, True)]] + ([[(b["sub"], 15, GREY, False)]] if b.get("sub") else []), margin=0.0)
        items = b.get("items", []); cw = (15.2 - 0.3 * (len(items) - 1)) / max(len(items), 1); ch = min(1.05, h - 0.4)
        for j, it in enumerate(items):
            _chip(sl, 5.7 + j * (cw + 0.3), y + (h - ch) / 2, cw, ch, it, fill=WHITE, size=15)
        if i < len(bands) - 1:
            _arrow_segments(sl, [(11.0, y + h + 0.06), (11.0, y + h + gap - 0.06)])
        y += h + gap
    return sl


def slide_compare(prs, s, footer):
    """Rows of before -> after pairs under two column headings; both cream, the after side leads in bold blue."""
    sl = prs.slides.add_slide(prs.slide_layouts[LAYOUT["blank"]])
    _title(sl, s["title"]); _kicker(sl, s.get("kicker")); _footer(sl, footer)
    left, right = s.get("headings", ["By hand", "Now"])
    for x, txt in ((0.81, left), (11.6, right)):
        t = sl.shapes.add_textbox(Inches(x), Inches(2.15), Inches(9.6), Inches(0.5))
        _text(t, [[(txt, 22, CREAM, True)]], margin=0.0, anchor=MSO_ANCHOR.TOP)
    rows = s["rows"]; gap = 0.3; h = min(1.45, (8.0 - gap * (len(rows) - 1)) / len(rows)); y = 2.8
    for r in rows:
        a = _box(sl, 0.81, y, 9.6, h, CREAM, radius=0.1)
        _text(a, [[(r["before"], 18, GREY, False)]], margin=0.3)
        b = _box(sl, 11.6, y, 9.6, h, CREAM, radius=0.1)
        _text(b, [[(r["after"], 18, BLUE, True)]] + ([[(r["proof"], 15, GREY, False)]] if r.get("proof") else []), margin=0.3)
        _arrow_segments(sl, [(10.55, y + h / 2), (11.5, y + h / 2)])
        y += h + gap
    return sl


def slide_timebar(prs, s, footer):
    """One row per activity: a cream bar proportional to the days it took by hand, an orange bar for the hours it takes now."""
    sl = prs.slides.add_slide(prs.slide_layouts[LAYOUT["blank"]])
    _title(sl, s["title"]); _kicker(sl, s.get("kicker")); _footer(sl, footer)
    rows = s["rows"]; max_days = max(r["before_days"] for r in rows); scale = 13.2 / max_days   # inches per working day
    t = sl.shapes.add_textbox(Inches(6.4), Inches(2.05), Inches(13.2), Inches(0.45))
    _text(t, [[("Working days by hand (cream) against hours now (orange), drawn to the same scale", 18, CREAM, False)]], margin=0.0, anchor=MSO_ANCHOR.TOP)
    gap = 0.3; h = min(1.35, (7.7 - gap * (len(rows) - 1)) / len(rows)); y = 2.7
    for r in rows:
        lab = sl.shapes.add_textbox(Inches(0.81), Inches(y), Inches(5.3), Inches(h))
        _text(lab, [[(r["label"], 20, CREAM, True)]] + ([[(r["note"], 14, CREAM, False)]] if r.get("note") else []), margin=0.0)
        bw = r["before_days"] * scale
        b = _box(sl, 6.4, y + 0.05, bw, h * 0.42, CREAM, radius=0.3)
        blabel = r.get("before_label", f'{r["before_days"]} working days')
        if bw >= 3.2:
            _text(b, [[(blabel, 16, BLUE, True)]], margin=0.2)
        else:   # too short a bar to hold its label: write it beside the bar instead
            bt = sl.shapes.add_textbox(Inches(6.4 + bw + 0.15), Inches(y + 0.05), Inches(8), Inches(h * 0.42))
            _text(bt, [[(blabel, 15, CREAM, True)]], margin=0.0)
        aw = max(0.28, r["after_hours"] / 8.0 * scale)
        a = _box(sl, 6.4, y + 0.05 + h * 0.42 + 0.1, aw, h * 0.42, ORANGE, radius=0.3)
        at = sl.shapes.add_textbox(Inches(6.4 + aw + 0.15), Inches(y + 0.05 + h * 0.42 + 0.1), Inches(8), Inches(h * 0.42))
        _text(at, [[(r["after_label"], 15, CREAM, True)]], margin=0.0)
        y += h + gap
    if s.get("legend"):
        t = sl.shapes.add_textbox(Inches(0.81), Inches(10.75), Inches(20), Inches(0.6))
        _text(t, [[(s["legend"], 14, CREAM, False)]], anchor=MSO_ANCHOR.TOP, margin=0.0)
    return sl


def slide_donut(prs, s, footer):
    """A native doughnut chart of one classification (left) beside a stat and its reading (right)."""
    from pptx.chart.data import CategoryChartData
    from pptx.enum.chart import XL_CHART_TYPE
    sl = prs.slides.add_slide(prs.slide_layouts[LAYOUT["blank"]])
    _title(sl, s["title"]); _kicker(sl, s.get("kicker")); _footer(sl, footer)
    parts = [p for p in s["parts"] if p["value"]]
    cd = CategoryChartData(); cd.categories = [p["label"] for p in parts]; cd.add_series(s.get("series", "count"), [p["value"] for p in parts])
    gf = sl.shapes.add_chart(XL_CHART_TYPE.DOUGHNUT, Inches(0.81), Inches(2.0), Inches(9.4), Inches(9.0), cd); ch = gf.chart
    ch.has_legend = False; ch.has_title = False
    ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"; cns = "{http://schemas.openxmlformats.org/drawingml/2006/chart}"
    for el in (ch._chartSpace, ch._chartSpace.find(cns + "chart").find(cns + "plotArea")):   # transparent over the gradient
        spPr = el.find(cns + "spPr")
        if spPr is None:
            spPr = etree.SubElement(el, cns + "spPr")
        for c in list(spPr): spPr.remove(c)
        etree.SubElement(spPr, ns + "noFill"); ln = etree.SubElement(spPr, ns + "ln"); etree.SubElement(ln, ns + "noFill")
    plot = ch.plots[0]
    hole = plot._element.find(cns + "holeSize")
    if hole is None:
        hole = etree.SubElement(plot._element, cns + "holeSize")
    hole.set("val", "55")
    plot.has_data_labels = True; dl = plot.data_labels; dl.show_value = True; dl.show_category_name = False
    dl.font.size = Pt(20); dl.font.bold = True; dl.font.color.rgb = rgb(BLUE)
    for pt, part in zip(plot.series[0].points, parts):
        pt.format.fill.solid(); pt.format.fill.fore_color.rgb = rgb(part.get("fill", CREAM)); pt.format.line.fill.background()
    # legend as chips, one per class, in the class colour
    y = 2.3
    for part in s["parts"]:
        fill = part.get("fill", CREAM)
        _chip(sl, 10.8, y, 2.6, 0.55, f'{part["label"]}  {part["value"]}', fill=fill, color=CREAM if fill in (GREEN, BLUE) else BLUE, size=15)
        t = sl.shapes.add_textbox(Inches(13.6), Inches(y), Inches(7.6), Inches(0.6))
        _text(t, [[(part.get("means", ""), 15, CREAM, False)]], margin=0.0)
        y += 0.8
    if s.get("stat"):
        b = _box(sl, 10.8, y + 0.4, 10.4, 2.6, CREAM, radius=0.08)
        _text(b, [[(s["stat"], 48, BLUE, True)], [(s.get("stat_label", ""), 18, GREY, False)]], anchor=MSO_ANCHOR.MIDDLE, margin=0.35)
    if s.get("legend"):
        t = sl.shapes.add_textbox(Inches(0.81), Inches(10.75), Inches(20), Inches(0.6))
        _text(t, [[(s["legend"], 14, CREAM, False)]], anchor=MSO_ANCHOR.TOP, margin=0.0)
    return sl


def slide_chevrons(prs, s, footer):
    """A left-to-right chain of chevrons (stages), a description under each, an optional band of notes below."""
    sl = prs.slides.add_slide(prs.slide_layouts[LAYOUT["blank"]])
    _title(sl, s["title"]); _kicker(sl, s.get("kicker")); _footer(sl, footer)
    st = s["stages"]; n = len(st); overlap = 0.35; w = (20.4 + overlap * (n - 1)) / n; y = 3.1; h = 1.8
    for i, stage in enumerate(st):
        x = 0.81 + i * (w - overlap)
        shape = sl.shapes.add_shape(MSO_SHAPE.PENTAGON if i == 0 else MSO_SHAPE.CHEVRON, Inches(x), Inches(y), Inches(w), Inches(h))
        shape.fill.solid(); shape.fill.fore_color.rgb = rgb(ORANGE if stage.get("accent") else CREAM); shape.line.fill.background(); shape.shadow.inherit = False
        shape.adjustments[0] = 0.32
        _text(shape, [[(stage["title"], 22, BLUE, True)]] + ([[(stage["sub"], 14, GREY if not stage.get("accent") else BLUE, False)]] if stage.get("sub") else []), align=PP_ALIGN.CENTER, margin=0.5)
        t = sl.shapes.add_textbox(Inches(x + 0.3), Inches(y + h + 0.3), Inches(w - overlap - 0.5), Inches(2.6))
        _text(t, [[(line, 16, CREAM, False)] for line in stage.get("lines", [])], anchor=MSO_ANCHOR.TOP, margin=0.0)
    if s.get("notes"):
        items = s["notes"]; cw = (20.4 - 0.4 * (len(items) - 1)) / len(items)
        for j, it in enumerate(items):
            b = _box(sl, 0.81 + j * (cw + 0.4), 7.4, cw, 2.1, CREAM, radius=0.08)
            _text(b, [[(it["title"], 20, BLUE, True)], [(it["body"], 15, GREY, False)]], anchor=MSO_ANCHOR.TOP, margin=0.3)
    if s.get("legend"):
        t = sl.shapes.add_textbox(Inches(0.81), Inches(10.75), Inches(20), Inches(0.6))
        _text(t, [[(s["legend"], 14, CREAM, False)]], anchor=MSO_ANCHOR.TOP, margin=0.0)
    return sl


def slide_steps(prs, s, footer):
    """Numbered steps in two columns, each a cream box with an orange number, a title and detail lines: the step-by-step visual."""
    sl = prs.slides.add_slide(prs.slide_layouts[LAYOUT["blank"]])
    _title(sl, s["title"]); _kicker(sl, s.get("kicker")); _footer(sl, footer)
    steps = s["steps"]; cols = s.get("cols", 2); rows = -(-len(steps) // cols); gap = 0.25
    w = (20.4 - gap * (cols - 1)) / cols; h = (8.85 - gap * (rows - 1)) / rows
    body_pt = s.get("body_pt", 15 if rows <= 5 else 13.5)
    for i, st in enumerate(steps):
        c, r = (i // rows, i % rows) if s.get("fill", "column") == "column" else (i % cols, i // cols)
        x = 0.81 + c * (w + gap); y = 2.0 + r * (h + gap)
        _box(sl, x, y, w, h, CREAM, radius=0.08)
        o = sl.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x + 0.22), Inches(y + 0.22), Inches(0.5), Inches(0.5))
        o.fill.solid(); o.fill.fore_color.rgb = rgb(ORANGE); o.line.fill.background(); o.shadow.inherit = False
        _text(o, [[(str(i + 1), 15, BLUE, True)]], align=PP_ALIGN.CENTER, margin=0.0)
        t = sl.shapes.add_textbox(Inches(x + 0.85), Inches(y + 0.1), Inches(w - 1.05), Inches(h - 0.2))
        _text(t, [[(st["title"], 19, BLUE, True)]] + [[(line, body_pt, GREY, False)] for line in st.get("lines", [])], anchor=MSO_ANCHOR.TOP, margin=0.0)
    if s.get("legend"):
        t = sl.shapes.add_textbox(Inches(0.81), Inches(10.95), Inches(20), Inches(0.5))
        _text(t, [[(s["legend"], 14, CREAM, False)]], anchor=MSO_ANCHOR.TOP, margin=0.0)
    return sl


def _side_point(n, side):
    x, y, w, h = n["x"], n["y"], n["w"], n["h"]
    return {"right": (x + w, y + h / 2), "left": (x, y + h / 2), "top": (x + w / 2, y), "bottom": (x + w / 2, y + h)}[side]


def _facing(a, b):
    """Which side of a faces b, from their centres: the larger displacement wins."""
    acx, acy = a["x"] + a["w"] / 2, a["y"] + a["h"] / 2; bcx, bcy = b["x"] + b["w"] / 2, b["y"] + b["h"] / 2
    dx, dy = bcx - acx, bcy - acy
    if abs(dx) >= abs(dy):
        return ("right", "left") if dx > 0 else ("left", "right")
    return ("bottom", "top") if dy > 0 else ("top", "bottom")


def _edge_free(slide, nodes, e):
    """An orthogonal arrow between free-layout nodes: sides chosen from geometry unless given, optional waypoints and a label."""
    a, b = nodes[e["from"]], nodes[e["to"]]
    via = [tuple(v) for v in e.get("via", [])]
    if via:
        fa = e.get("from_side") or _facing(a, {"x": via[0][0], "y": via[0][1], "w": 0, "h": 0})[0]
        tb = e.get("to_side") or _facing(b, {"x": via[-1][0], "y": via[-1][1], "w": 0, "h": 0})[0]
    else:
        fa, tb = _facing(a, b); fa = e.get("from_side", fa); tb = e.get("to_side", tb)
    p0, p1 = _side_point(a, fa), _side_point(b, tb)
    if via:
        pts = [p0] + via + [p1]
    elif fa in ("right", "left") and tb in ("left", "right"):
        pts = [p0, p1] if abs(p0[1] - p1[1]) < 0.05 else [p0, ((p0[0] + p1[0]) / 2, p0[1]), ((p0[0] + p1[0]) / 2, p1[1]), p1]
    elif fa in ("top", "bottom") and tb in ("top", "bottom"):
        pts = [p0, p1] if abs(p0[0] - p1[0]) < 0.05 else [p0, (p0[0], (p0[1] + p1[1]) / 2), (p1[0], (p0[1] + p1[1]) / 2), p1]
    elif fa in ("right", "left"):
        pts = [p0, (p1[0], p0[1]), p1]
    else:
        pts = [p0, (p0[0], p1[1]), p1]
    _arrow_segments(slide, pts, width_pt=e.get("width", 2.25))
    if e.get("label"):
        mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
        if "label_at" in e or len(pts) > 2:   # a routed edge: the label sits where the spec says, else above the middle bend
            mid = pts[len(pts) // 2] if len(pts) > 2 else (mx, my)
            lx, ly = e.get("label_at", (mid[0] + 0.1, mid[1] - 0.42))
            t = slide.shapes.add_textbox(Inches(lx), Inches(ly), Inches(e.get("label_w", 3.2)), Inches(0.4))
            _text(t, [[(e["label"], 11, CREAM, True)]], anchor=MSO_ANCHOR.BOTTOM, margin=0.0)
        elif abs(p0[1] - p1[1]) < 0.05:   # a straight horizontal edge: the label centred just above the line
            t = slide.shapes.add_textbox(Inches(mx - 0.6), Inches(my - 0.34), Inches(1.2), Inches(0.3))
            _text(t, [[(e["label"], 11, CREAM, True)]], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.BOTTOM, margin=0.0)
        else:   # a straight vertical edge: the label just right of the line
            t = slide.shapes.add_textbox(Inches(mx + 0.07), Inches(my - 0.15), Inches(1.2), Inches(0.3))
            _text(t, [[(e["label"], 11, CREAM, True)]], anchor=MSO_ANCHOR.MIDDLE, margin=0.0)


def _draw_free_node(slide, n):
    x, y, w, h = n["x"], n["y"], n["w"], n["h"]; kind = n.get("kind", "step"); title, body = n.get("title", ""), n.get("body", "")
    tp, bp = n.get("title_pt", 14), n.get("body_pt", 11)
    if kind in ("step", "data", "stop", "domain", "accent", "gate"):
        pad = 0.24 if kind in ("step", "data") else (w * 0.32 if kind == "gate" else 0.16)   # a diamond's usable width is the middle third
        paras = [(title, tp if kind in ("step", "data") else n.get("title_pt", 11 if kind != "accent" else 12), True)] + ([(body, bp if kind == "step" else 9.5, False)] if body and kind in ("step", "data") else [])
        sizes = fit(paras, w - pad, (h - 0.12) if kind in ("step", "data") else None, f"{n['id']} ({title[:30]})")
        tp = sizes[0]; bp = sizes[1] if len(sizes) > 1 else bp
        n = dict(n, title_pt=tp)
    if kind == "group":   # an outline with a label, drawn first so nodes sit on it
        g = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
        g.fill.background(); g.line.color.rgb = rgb(CREAM); g.line.width = Pt(1.5); g.adjustments[0] = 0.04; g.shadow.inherit = False
        t = slide.shapes.add_textbox(Inches(x + 0.18), Inches(y + 0.05), Inches(w - 0.36), Inches(0.45))
        _text(t, [[(title, 14, CREAM, True)]] + ([[(body, 11, CREAM, False)]] if body else []), anchor=MSO_ANCHOR.TOP, margin=0.0)
    elif kind == "gate":
        d = slide.shapes.add_shape(MSO_SHAPE.DIAMOND, Inches(x), Inches(y), Inches(w), Inches(h))
        d.fill.solid(); d.fill.fore_color.rgb = rgb(ORANGE); d.line.fill.background(); d.shadow.inherit = False
        _text(d, [[(title, n.get("title_pt", 11), BLUE, True)]], align=PP_ALIGN.CENTER, margin=0.02)
    elif kind == "data":   # a table: the same flat cream box as a step, centred, so nothing on the page pretends to be 3-D
        c = _box(slide, x, y, w, h, CREAM, radius=0.1)
        _text(c, [[(title, tp, BLUE, True)]] + ([[(body, bp, GREY, False)]] if body else []), align=PP_ALIGN.CENTER, margin=0.05)
    elif kind == "domain":
        _chip(slide, x, y, w, h, title, fill=WHITE, size=n.get("title_pt", 11), bold=True)
    elif kind == "accent":
        b = _box(slide, x, y, w, h, ORANGE, radius=0.5)
        _text(b, [[(title, n.get("title_pt", 12), BLUE, True)]], align=PP_ALIGN.CENTER, margin=0.08)
    elif kind == "note":
        t = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        _text(t, [[(title, 12, CREAM, True)]] + ([[(body, 11, CREAM, False)]] if body else []), anchor=MSO_ANCHOR.TOP, margin=0.0)
    elif kind == "stop":   # where a failed gate lands: a small cream box, the legend says what happens next
        b = _box(slide, x, y, w, h, CREAM, radius=0.2)
        _text(b, [[(title, n.get("title_pt", 10), BLUE, True)]], align=PP_ALIGN.CENTER, margin=0.04)
    else:   # step
        b = _box(slide, x, y, w, h, CREAM, radius=0.1)
        paras = [[(title, tp, BLUE, True)]] + ([[(body, bp, GREY, False)]] if body else [])
        _text(b, paras, align=PP_ALIGN.CENTER if n.get("center") else PP_ALIGN.LEFT, margin=0.12)
        if n.get("tag"):
            _tag(slide, x + w - 0.08, y - 0.3, n["tag"])
    if n.get("num") is not None and kind not in ("group", "note"):   # step badge: reading order at a glance
        o = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x - 0.14), Inches(y - 0.14), Inches(0.34), Inches(0.34))
        o.fill.solid(); o.fill.fore_color.rgb = rgb(ORANGE); o.line.fill.background(); o.shadow.inherit = False
        _text(o, [[(str(n["num"]), 10, BLUE, True)]], align=PP_ALIGN.CENTER, margin=0.0)


def slide_diagram(prs, s, footer):
    """A free-layout flow diagram: nodes at x/y/w/h in inches (step, gate, data, domain, group, accent, note) and orthogonal arrows."""
    sl = prs.slides.add_slide(prs.slide_layouts[LAYOUT["blank"]])
    _title(sl, s["title"]); _kicker(sl, s.get("kicker")); _footer(sl, footer)
    nodes = {n["id"]: n for n in s["nodes"]}
    for n in s["nodes"]:
        if n.get("kind") == "group":
            _draw_free_node(sl, n)
    for n in s["nodes"]:
        if n.get("kind") != "group":
            _draw_free_node(sl, n)
    for e in s.get("edges", []):
        _edge_free(sl, nodes, e)
    if s.get("legend"):
        t = sl.shapes.add_textbox(Inches(0.81), Inches(s.get("legend_y", 10.95)), Inches(20.4), Inches(0.5))
        _text(t, [[(s["legend"], 12, CREAM, False)]], anchor=MSO_ANCHOR.TOP, margin=0.0)
    return sl


BUILDERS = {"layers": slide_layers, "compare": slide_compare, "title": slide_title, "section": slide_section, "statement": slide_statement, "process": slide_process,
            "roadmap": slide_roadmap, "cards": slide_cards, "bullets": slide_bullets, "table": slide_table,
            "timebar": slide_timebar, "donut": slide_donut, "chevrons": slide_chevrons, "steps": slide_steps, "diagram": slide_diagram}


def build(spec: dict, out: pathlib.Path) -> pathlib.Path:
    prs = Presentation(str(TEMPLATE)); _clear_slides(prs)
    footer = spec.get("footer", FOOTER)
    for s in spec["slides"]:
        BUILDERS[s["type"]](prs, s, footer)
    out.parent.mkdir(parents=True, exist_ok=True); prs.save(str(out))
    _declare_jpg(out)
    return out


def _declare_jpg(path: pathlib.Path) -> None:
    """python-pptx keeps the template's .jpg media but declares only jpeg: add the jpg default
    content type (the pptx skill's validate.py flags it; PowerPoint tolerates it)."""
    import shutil, tempfile, zipfile
    with zipfile.ZipFile(path) as z:
        ct = z.read("[Content_Types].xml").decode()
        if 'Extension="jpg"' in ct or not any(n.lower().endswith(".jpg") for n in z.namelist()):
            return
        items = [(i, z.read(i.filename)) for i in z.infolist()]
    ct = ct.replace("<Default ", '<Default Extension="jpg" ContentType="image/jpeg"/><Default ', 1)
    tmp = pathlib.Path(tempfile.mkstemp(suffix=".pptx")[1])
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for info, data in items:
            z.writestr(info, ct.encode() if info.filename == "[Content_Types].xml" else data)
    shutil.move(str(tmp), str(path))


def main() -> int:
    spec = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = build(spec, pathlib.Path(sys.argv[2]))
    print(f"wrote {out} ({len(spec['slides'])} slides)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
