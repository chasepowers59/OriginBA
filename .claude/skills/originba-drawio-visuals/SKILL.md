---
name: originba-drawio-visuals
description: Build Origin-styled process flows, deployment diagrams and architecture visuals as native draw.io files (editable by anyone), routed and laid out headlessly with the official draw.io MCP engines, rendered in the browser for QA and exported to PNG/SVG/PDF with draw.io Desktop when it is installed. Use for any OriginBA / SmartCity diagram that has to look professional, stay editable, and match the Origin palette; the two Release 26 deployment flows are the worked examples.
---

# Origin visuals with draw.io

The deck builder (`originba-process-deck`) draws diagrams as PowerPoint shapes. That is right for
slides, but a diagram people will edit, reuse in Confluence or a doc, or refine by hand belongs in
draw.io: one `.drawio` file, editable by anyone, exportable to PNG, SVG or PDF with the XML embedded
so the export stays editable. This skill is how we get there in the Origin look.

## What the draw.io MCP actually is (learned 2026-09-28)

Three different things ship under one name (`jgraph/drawio-mcp`, Apache-2.0):

| Piece | What it does | How we use it |
| --- | --- | --- |
| **MCP tool server** `npx -y @drawio/mcp` (stdio) | Tools `open_drawio_xml`, `open_drawio_mermaid`, `open_drawio_csv` (open a diagram in the draw.io web editor via a `#create=` URL, with optional `postLayout: "elk"` or `routing: "libavoid"`), `list_pages` / `get_page` / `set_page` (edit one page of a local `.drawio`), `search_shapes` (10,000 stencils and brand icons) | Registered in `OriginBA-3/.mcp.json` for interactive sessions. Its **engines** (ELK layout, libavoid routing) run in plain Node with no editor, which is what `scripts/drawio_pass.mjs` calls directly |
| **MCP app server** `https://mcp.draw.io/mcp` (hosted) | Renders diagrams inline in claude.ai / Cursor chat with an "Open in draw.io" button | Not needed for our pipeline |
| **Claude Code plugin** `/plugin marketplace add jgraph/drawio-mcp` | A skill that writes `.drawio` files and shells out to **draw.io Desktop** (`/Applications/draw.io.app/Contents/MacOS/draw.io`) for Mermaid conversion, ELK layout and PNG/SVG/PDF export | We reuse its CLI commands verbatim (below); Desktop is the only way to export images |

The `.drawio` format is plain mxGraphModel XML: `<mxfile><diagram><mxGraphModel><root>` with cells
`0` and `1`, then vertices (`vertex="1"`, an `mxGeometry`) and edges (`edge="1"`, `source`, `target`,
and ALWAYS a child `<mxGeometry relative="1" as="geometry"/>`). Labels are HTML (`html=1`, XML-escaped).
The full references are vendored at `node_modules/@drawio/mcp/src/xml-reference.md` after `npm install`
in this folder; the style reference is `shared/style-reference.md` in the repo.

## The Origin style, as draw.io style strings

Same palette as the deck skill, measured from the reference deck: BLUE `#0B3D7A`, CREAM `#F5EFE9`,
GREY `#4C5D69`, ORANGE `#FFA418`, WHITE `#FFFFFF`. One rule, every diagram: cream containers, white
chips, orange for gates and highlights, blue titles, grey body, cream arrows, on the blue page.
No 3-D shapes (no cylinders, no shadows, no gradients), no grey or tan fills.

| Element | Style string |
| --- | --- |
| Page | `<mxGraphModel adaptiveColors="none" grid="0" page="0" background="#0B3D7A">` |
| Step / table box | `rounded=1;arcSize=10;whiteSpace=wrap;html=1;fillColor=#F5EFE9;strokeColor=none;align=left;spacingLeft=10;fontFamily=Arial;` label `<b><font color="#0B3D7A" style="font-size:19px">Title</font></b><br><font color="#4C5D69" style="font-size:15px">body</font>` |
| Gate (a check that stops the run) | `rhombus;whiteSpace=wrap;html=1;fillColor=#FFA418;strokeColor=none;fontColor=#0B3D7A;fontStyle=1;fontFamily=Arial;` |
| Domain chip | `rounded=1;arcSize=50;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=none;fontColor=#0B3D7A;fontStyle=1;` |
| Accent pill | same as the chip with `fillColor=#FFA418` |
| Group (outline with a label) | `rounded=1;arcSize=6;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#F5EFE9;strokeWidth=1.5;container=1;pointerEvents=0;align=left;verticalAlign=top;spacingLeft=14;fontColor=#F5EFE9;` children carry `parent="<group id>"` and coordinates relative to the group |
| Arrow | `edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;strokeColor=#F5EFE9;strokeWidth=2;endArrow=block;endFill=1;fontColor=#F5EFE9;labelBackgroundColor=none;` |
| Note text | `text;html=1;fillColor=none;strokeColor=none;align=left;verticalAlign=top;fontColor=#F5EFE9;` |

Fonts: Arial (renders identically in the browser viewer, Desktop export and PowerPoint). Sizes are
PowerPoint points × 1.33 (a 14pt title is `font-size:19px`).

## The pipeline

```
spec.json  --spec_to_drawio.py-->  name.drawio  --drawio_pass.mjs route-->  name.drawio (routed)
                                                 --drawio_pass.mjs viewer--> URL, screenshot in the browser pane (QA)
                                                 --draw.io Desktop CLI-----> name.drawio.png / .svg / .pdf (embedded XML)
```

1. **Author the structure.** Start from a process-deck `diagram` spec (nodes with `kind` step / gate /
   data / domain / group / accent / note, edges with `from` / `to` / `label`, optional `via` waypoints and
   `from_side` / `to_side`) so the same JSON drives the slide and the draw.io file.
   `scripts/spec_to_drawio.py spec.json -o out.drawio [--slide "Title"]` converts every `diagram` slide to
   one page (1 inch = 96 px), makes groups real containers, files each edge at the innermost container
   holding both ends, keeps the spec's waypoints as `<Array as="points">` and its sides as exit/entry
   points. Edges without waypoints get draw.io's own orthogonal router, which is right for stacked or
   adjacent boxes.
2. **Route or lay out headlessly, only when there are no containers.** `node scripts/drawio_pass.mjs route
   in.drawio out.drawio` keeps every position and re-routes the edges around the boxes (libavoid, ~1 s);
   `node scripts/drawio_pass.mjs elk in.drawio out.drawio horizontal` re-places the vertices in layered
   order (ELK). Measured 2026-09-28: the libavoid pass reads container children as if their coordinates
   were absolute, so on a diagram with group containers every column's children overlap and it routes the
   wires along the container edges. For hand-placed layouts with groups, keep the spec's waypoints and skip
   the pass; use the passes for flat diagrams (no `group` nodes). Run `npm install` in this folder once.
3. **QA in the browser pane.** `node scripts/drawio_pass.mjs viewer in.drawio` prints a
   `viewer.diagrams.net` lightbox URL; open it with the browser tools, resize the window wide, screenshot.
   `url` prints the `app.diagrams.net` editor URL for hand edits. Look for: an arrow crossing a box, a
   label wrapping mid-word (widen the box), a group label colliding with its first child, an edge that
   libavoid sent the long way round (give that edge `from_side`/`to_side` in the spec or shorten the path).
4. **Export.** With draw.io Desktop installed (`brew install --cask drawio`):
   ```bash
   /Applications/draw.io.app/Contents/MacOS/draw.io -x -f png -e -b 10 -s 2 -o name.drawio.png name.drawio
   /Applications/draw.io.app/Contents/MacOS/draw.io -x -f svg -e -o name.drawio.svg name.drawio
   /Applications/draw.io.app/Contents/MacOS/draw.io -x -f pdf -e -a -o name.drawio.pdf name.drawio   # all pages
   ```
   `-e` embeds the XML (the PNG reopens in draw.io as the editable diagram), `-s 2` doubles the pixel
   density, `-b` is the border. `-p N` picks a page. Without Desktop, the `.drawio` file and the URLs are
   the deliverable; say so rather than screenshotting the viewer as if it were an export.

## Rules

- **Declare structure; let the router route.** Never hand-compute waypoints in XML. If a route is wrong,
  fix the placement or the connection sides, then re-run the pass.
- **Every edge cell has a child mxGeometry**, every label is XML-escaped, no XML comments, unique ids,
  pages stored uncompressed (the passes and `set_page` need plain `<mxGraphModel>`).
- **Facts first.** A diagram states how the system works; check each box against the scripts (the rolling
  window, the schedule, the job list, which domain reads which view) before it ships, the same as a slide.
- **Same spec, both outputs.** When a diagram exists as a slide, generate the draw.io file from the same
  spec so the two cannot drift; commit the `.drawio` beside the PNG.
- **QA every render.** A draw.io export is a picture; look at it before sending it, at full resolution.

## Worked examples

`jaspersoft/docs/deployment_deck/visuals/`: `standard_offering_deployment_flow.drawio` and
`database_deployment_flow.drawio`, generated from `visuals/spec.json` with the two commands above, and the
PowerPoint versions of the same two diagrams beside them.
