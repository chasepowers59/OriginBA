#!/usr/bin/env python3
"""Turn a process-deck `diagram` spec (the same JSON the pptx builder reads) into an Origin-styled
draw.io file: cream boxes, orange gates and pills, white domain chips, cream outlines for groups,
cream orthogonal arrows, on the Origin blue background.

    python3 spec_to_drawio.py spec.json --slide "Database Deployment Flow" -o out.drawio
    python3 spec_to_drawio.py visuals.json -o out.drawio            # one page per diagram slide

Coordinates in the spec are inches on the 22" x 12.37" slide; here 1 inch = 96 px. Groups become
real draw.io containers (children carry coordinates relative to the group), and every edge is filed
at the innermost container holding both ends, which is what the libavoid router and ELK expect.
Edges keep the spec's `via` waypoints and `from_side` / `to_side` (as exit/entry points): a hand-placed
layout with known-good routes should not be re-routed. Edges without waypoints get draw.io's own
orthogonal router, which is right for stacked or adjacent boxes. Run drawio_pass.mjs route (libavoid)
only on diagrams WITHOUT containers: the pass reads child coordinates as absolute, so every column's
children overlap and it routes along the container edges (measured 2026-09-28).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from xml.sax.saxutils import escape

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "originba-process-deck" / "scripts"))
from textfit import fit   # noqa: E402  shared with the pptx builder: an overflow fails the build

PX = 96.0
# the Origin BA app palette (apps/analytics-portal/src/app/globals.css), the same roles as the pptx builder
PAGE, PAGE_FG, CARD, CARD_TITLE, CARD_BODY, CHIP = "#0B1723", "#E6ECF2", "#F2F5F8", "#004B86", "#56636E", "#FFFFFF"
ACCENT, ON_ACCENT, GROUP_LINE = "#006FAC", "#FFFFFF", "#8ACAD4"
FONT = "Arial"


def px(v: float) -> str:
    return f"{round(v * PX, 1):g}"


def pt(size: float) -> str:
    return f"{round(size * 1.33, 1):g}"   # PowerPoint points to CSS pixels


def label(title: str, body: str = "", title_pt: float = 14, body_pt: float = 11, title_color: str = CARD_TITLE, body_color: str = CARD_BODY) -> str:
    t = f'<b><font style="font-size:{pt(title_pt)}px" color="{title_color}">{escape(title)}</font></b>'
    if body:
        t += f'<br><font style="font-size:{pt(body_pt)}px" color="{body_color}">{escape(body)}</font>'
    return escape(t, {'"': "&quot;"})


def style(**kv) -> str:
    base = {"html": 1, "whiteSpace": "wrap", "fontFamily": FONT}
    base.update(kv)
    parts = []
    for k, v in base.items():
        parts.append(k if v is None else f"{k}={v}")
    return ";".join(parts) + ";"


def node_cell(n: dict, parent: str, ox: float, oy: float) -> str:
    kind = n.get("kind", "step")
    x, y, w, h = n["x"] - ox, n["y"] - oy, n["w"], n["h"]
    title, body = n.get("title", ""), n.get("body", "")
    tp, bp = n.get("title_pt", 14), n.get("body_pt", 11)
    if kind in ("step", "data", "stop", "domain", "accent", "gate"):
        pad = 0.24 if kind in ("step", "data") else (w * 0.32 if kind == "gate" else 0.16)
        t0 = tp if kind in ("step", "data") else n.get("title_pt", 12 if kind == "accent" else (10 if kind == "stop" else 11))
        paras = [(title, t0, True)] + ([(body, bp if kind == "step" else 9.5, False)] if body and kind in ("step", "data") else [])
        sizes = fit(paras, w - pad, (h - 0.12) if kind in ("step", "data") else None, f"{n['id']} ({title[:30]})")
        tp = sizes[0]; bp = sizes[1] if len(sizes) > 1 else bp
        n = dict(n, title_pt=tp)
    if kind == "group":
        st = style(rounded=1, arcSize=6, fillColor="none", strokeColor=GROUP_LINE, strokeWidth=1.5, container=1, pointerEvents=0,
                   align="left", verticalAlign="top", spacingLeft=14, spacingTop=4, fontColor=PAGE_FG)
        val = label(title, body, 14, 11, PAGE_FG, PAGE_FG)
    elif kind == "gate":   # side spacing keeps the wrapped label inside the diamond, where blue text is readable
        pad = int(w * PX * 0.16)
        st = style(rhombus=None, fillColor=ACCENT, strokeColor="none", fontColor=ON_ACCENT, fontStyle=1, fontSize=pt(n.get("title_pt", 11)),
                   spacingLeft=pad, spacingRight=pad)
        val = escape(title, {'"': "&quot;"})
    elif kind == "domain":
        st = style(rounded=1, arcSize=50, fillColor=CHIP, strokeColor="none", fontColor=CARD_TITLE, fontStyle=1, fontSize=pt(n.get("title_pt", 11)))
        val = escape(title, {'"': "&quot;"})
    elif kind == "accent":
        st = style(rounded=1, arcSize=50, fillColor=ACCENT, strokeColor="none", fontColor=ON_ACCENT, fontStyle=1, fontSize=pt(n.get("title_pt", 12)))
        val = escape(title, {'"': "&quot;"})
    elif kind == "note":
        st = style(text=None, fillColor="none", strokeColor="none", align="left", verticalAlign="top", fontColor=PAGE_FG)
        val = label(title, body, 12, 11, PAGE_FG, PAGE_FG)
    elif kind == "stop":
        st = style(rounded=1, arcSize=30, fillColor=CARD, strokeColor="none", fontColor=CARD_TITLE, fontStyle=1, fontSize=pt(n.get("title_pt", 10)))
        val = escape(title, {'"': "&quot;"})
    else:   # step and data: the same flat cream box
        centred = kind == "data" or n.get("center")
        st = style(rounded=1, arcSize=10, fillColor=CARD, strokeColor="none", align="center" if centred else "left",
                   verticalAlign="middle", spacingLeft=0 if centred else 10, spacingRight=0 if centred else 8)
        val = label(title, body, tp, bp if kind == "step" else min(bp, 9.5))
    geom = f'<mxGeometry x="{px(x)}" y="{px(y)}" width="{px(w)}" height="{px(h)}" as="geometry"/>'
    if n.get("tooltip"):   # hover text in draw.io: the detail that stays off the picture
        tip = escape(n["tooltip"], {'"': "&quot;"})
        cell = (f'<object id="{n["id"]}" label="{val}" tooltip="{tip}"><mxCell style="{st}" vertex="1" parent="{parent}">{geom}</mxCell></object>')
    else:
        cell = f'<mxCell id="{n["id"]}" value="{val}" style="{st}" vertex="1" parent="{parent}">{geom}</mxCell>'
    if n.get("num") is not None and kind not in ("group", "note"):   # step badge, same parent and frame as the node
        bst = style(ellipse=None, fillColor=ACCENT, strokeColor="none", fontColor=ON_ACCENT, fontStyle=1, fontSize=pt(10), spacing=0)
        cell += (f'<mxCell id="{n["id"]}_n" value="{n["num"]}" style="{bst}" vertex="1" parent="{parent}">'
                 f'<mxGeometry x="{px(x - 0.14)}" y="{px(y - 0.14)}" width="{px(0.34)}" height="{px(0.34)}" as="geometry"/></mxCell>')
    return cell


SIDES = {"right": (1, 0.5), "left": (0, 0.5), "top": (0.5, 0), "bottom": (0.5, 1)}


def facing(n: dict, x: float, y: float) -> str:
    """The side of n that faces the point (x, y): the larger displacement from the centre wins."""
    dx, dy = x - (n["x"] + n["w"] / 2), y - (n["y"] + n["h"] / 2)
    if abs(dx) >= abs(dy):
        return "right" if dx > 0 else "left"
    return "bottom" if dy > 0 else "top"


def inside(n: dict, g: dict) -> bool:
    return (n is not g and n["x"] >= g["x"] - 0.01 and n["y"] >= g["y"] - 0.01
            and n["x"] + n["w"] <= g["x"] + g["w"] + 0.01 and n["y"] + n["h"] <= g["y"] + g["h"] + 0.01)


def innermost_group(n: dict, groups: list[dict]) -> dict | None:
    cands = [g for g in groups if inside(n, g)]
    return min(cands, key=lambda g: g["w"] * g["h"]) if cands else None


def ancestors(nid: str, parent_of: dict) -> list[str]:
    out = []
    while nid in parent_of and parent_of[nid] != "1":
        nid = parent_of[nid]; out.append(nid)
    return out


def diagram_xml(slide: dict) -> str:
    nodes = slide["nodes"]
    groups = [n for n in nodes if n.get("kind") == "group"]
    parent_of: dict[str, str] = {}
    origin: dict[str, tuple[float, float]] = {"1": (0.0, 0.0)}
    for g in sorted(groups, key=lambda g: -g["w"] * g["h"]):   # outer groups first so nesting resolves
        og = innermost_group(g, [x for x in groups if x is not g and x["w"] * x["h"] > g["w"] * g["h"]])
        parent_of[g["id"]] = og["id"] if og else "1"
        origin[g["id"]] = (g["x"], g["y"])
    for n in nodes:
        if n.get("kind") != "group":
            og = innermost_group(n, groups)
            parent_of[n["id"]] = og["id"] if og else "1"
    cells = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
    order = sorted(groups, key=lambda g: -g["w"] * g["h"]) + [n for n in nodes if n.get("kind") != "group"]
    for n in order:
        p = parent_of[n["id"]]; ox, oy = origin[p]
        cells.append(node_cell(n, p, ox, oy))
    by_id = {n["id"]: n for n in nodes}
    for i, e in enumerate(slide.get("edges", [])):
        a, b = e["from"], e["to"]
        anc_a, anc_b = ancestors(a, parent_of), ancestors(b, parent_of)   # innermost container holding both endpoints
        common = next((x for x in anc_a if x in anc_b), "1")
        # edge labels: no wrapping (a wrapped edge label stacks one word per line) and the page colour behind the text
        kv = dict(edgeStyle="orthogonalEdgeStyle", rounded=1, strokeColor=PAGE_FG, strokeWidth=2, endArrow="block", endFill=1,
                  fontColor=PAGE_FG, fontSize=pt(11), fontStyle=1, labelBackgroundColor=PAGE, whiteSpace="nowrap")
        via = [tuple(v) for v in e.get("via", [])]
        fa, tb = e.get("from_side"), e.get("to_side")
        if via and not fa:
            fa = facing(by_id[a], via[0][0], via[0][1])
        if via and not tb:
            tb = facing(by_id[b], via[-1][0], via[-1][1])
        for key, side in (("exit", fa), ("entry", tb)):
            if side:
                sx, sy = SIDES[side]; kv[f"{key}X"] = sx; kv[f"{key}Y"] = sy; kv[f"{key}Dx"] = 0; kv[f"{key}Dy"] = 0
        st = style(**kv)
        val = escape(e.get("label", ""), {'"': "&quot;"})
        ox, oy = origin[common]
        pts = "".join(f'<mxPoint x="{px(vx - ox)}" y="{px(vy - oy)}"/>' for vx, vy in via)
        # a label on a straight edge sits beside the line, not on it: above a horizontal edge, right of a vertical one
        off = ""
        if e.get("label") and not via:
            na, nb = by_id[a], by_id[b]
            horizontal = abs((na["y"] + na["h"] / 2) - (nb["y"] + nb["h"] / 2)) < abs((na["x"] + na["w"] / 2) - (nb["x"] + nb["w"] / 2))
            off = '<mxPoint as="offset" x="0" y="-12"/>' if horizontal else '<mxPoint as="offset" x="18" y="-6"/>'
        inner = (f'<Array as="points">{pts}</Array>' if via else "") + off
        geom = f'<mxGeometry relative="1" as="geometry">{inner}</mxGeometry>' if inner else '<mxGeometry relative="1" as="geometry"/>'
        cells.append(f'<mxCell id="e{i}" value="{val}" style="{st}" edge="1" source="{a}" target="{b}" parent="{common}">{geom}</mxCell>')
    # the picture stands alone outside the deck: title and subtitle above, legend and footer below
    xs = [n["x"] for n in nodes]; ys = [n["y"] + n["h"] for n in nodes]
    left, bottom = min(xs), max(ys)
    tst = style(text=None, fillColor="none", strokeColor="none", align="left", verticalAlign="top", fontColor=PAGE_FG)
    # label() escapes once, which is what an attribute needs; escaping its result again shows raw tags (seen 2026-09-28)
    head = f'<b><font style="font-size:{pt(30)}px">{escape(slide["title"])}</font></b>'
    if slide.get("subtitle"):
        head += f'<br><font style="font-size:{pt(14)}px">{escape(slide["subtitle"])}</font>'
    cells.append(f'<mxCell id="_title" value="{escape(head, {chr(34): "&quot;"})}" style="{tst}" vertex="1" parent="1">'
                 f'<mxGeometry x="{px(left)}" y="{px(0.35)}" width="{px(20.4)}" height="{px(1.3)}" as="geometry"/></mxCell>')
    foot_y = bottom + 0.3
    if slide.get("legend"):
        cells.append(f'<mxCell id="_legend" value="{label(slide["legend"], "", 11, 11, PAGE_FG, PAGE_FG)}" style="{tst}" vertex="1" parent="1">'
                     f'<mxGeometry x="{px(left)}" y="{px(foot_y)}" width="{px(20.4)}" height="{px(0.6)}" as="geometry"/></mxCell>')
        foot_y += 0.55
    footer = slide.get("footer", "Origin Utility, Inc  /  Proprietary and Confidential  /  Internal Use Only")
    cells.append(f'<mxCell id="_footer" value="{label(footer, "", 9, 9, PAGE_FG, PAGE_FG)}" style="{tst}" vertex="1" parent="1">'
                 f'<mxGeometry x="{px(left)}" y="{px(foot_y)}" width="{px(20.4)}" height="{px(0.4)}" as="geometry"/></mxCell>')
    # optional layers, hidden by default: notes for engineers (commands, checks) that never reach the exported picture
    layer_cells = []
    for li, (lname, notes) in enumerate(slide.get("layers", {}).items()):
        lid = f"_layer{li}"
        layer_cells.append(f'<mxCell id="{lid}" value="{escape(lname)}" parent="0" visible="0"/>')
        nst = style(rounded=1, arcSize=8, fillColor=CHIP, strokeColor=ACCENT, strokeWidth=1.5, align="left", verticalAlign="top",
                    spacingLeft=6, fontColor=CARD_TITLE, fontFamily="Courier New")
        for j, note in enumerate(notes):
            v = escape(label(note.get("title", ""), note.get("body", ""), 10, 9), {'"': "&quot;"})
            layer_cells.append(f'<mxCell id="{lid}_{j}" value="{v}" style="{nst}" vertex="1" parent="{lid}">'
                               f'<mxGeometry x="{px(note["x"])}" y="{px(note["y"])}" width="{px(note.get("w", 3.0))}" height="{px(note.get("h", 0.7))}" as="geometry"/></mxCell>')
    cells = cells[:2] + [c for c in layer_cells if 'parent="0"' in c] + cells[2:] + [c for c in layer_cells if 'parent="0"' not in c]
    return f'<mxGraphModel adaptiveColors="none" grid="0" page="0" background="{PAGE}"><root>' + "".join(cells) + "</root></mxGraphModel>"


def mxfile(pages: list[tuple[str, str]]) -> str:
    out = ["<mxfile>"]
    for i, (name, model) in enumerate(pages):
        out.append(f'<diagram id="page{i + 1}" name="{escape(name, {chr(34): "&quot;"})}">{model}</diagram>')
    out.append("</mxfile>")
    return "".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("spec"); ap.add_argument("-o", "--out", required=True); ap.add_argument("--slide", help="title of one diagram slide")
    a = ap.parse_args()
    spec = json.loads(pathlib.Path(a.spec).read_text())
    slides = [s for s in spec["slides"] if s.get("type") == "diagram" and (not a.slide or s["title"] == a.slide)]
    if not slides:
        print("no diagram slides matched", file=sys.stderr); return 1
    pathlib.Path(a.out).write_text(mxfile([(s["title"], diagram_xml(s)) for s in slides]))
    print(f"wrote {a.out}: {len(slides)} page(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
