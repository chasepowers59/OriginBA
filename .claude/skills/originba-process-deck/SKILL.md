---
name: originba-process-deck
description: Build Origin-styled process and architecture decks (the DV_App_Overview look Reed uses) from a JSON spec -- blue gradient slides, cream rounded nodes with cream arrows, orange callouts, spreadsheet cards, numbered roadmap, cards, tables -- on the reference deck's own layouts. Use for internal documentation of any OriginBA / SmartCity process, an end-to-end flow, a roadmap, or a "what is automated" story; the deployment deck under jaspersoft/docs/deployment_deck is the worked example.
---

# Origin process decks

The look is Reed's `DV_App_Overview.pptx` (2026-09-24), measured: 22" x 12.37" slides on a blue
gradient background, title in light 60pt cream at the top left, cream (`F5EFE9`) rounded nodes
4.30" x 1.55" on a 4-column grid (5.36" pitch, 2.05" row pitch) with a bold dark-blue (`0B3D7A`)
25pt title and grey (`4C5D69`) 20pt body, tan (`DBD3CC`, the reference deck's darker cream) fills for by-hand steps, failures and the 'before' side of a compare (no dark-grey fills anywhere: grey is body text only), thin cream arrows (2.75pt, triangle head), orange
(`FFA418`) pills for constraints and pain points, white "spreadsheet" cards with a green
(`1D6F42`) header for artifacts, numbered orange circles over cream boxes for a roadmap (the
current step inverted), and the footer `@2026, Origin Utility, Inc / Proprietary & Confidential
/ Internal Use Only` centred at the bottom. Section markers are small orange pills (S1, S2).

## Build

```bash
python3 .claude/skills/originba-process-deck/scripts/build_process_deck.py spec.json out.pptx
```

The generator opens `assets/origin_blue_template.pptx` (the reference deck, whose layouts carry the
background image, theme and fonts), removes its slides and adds ours, so the result is on the real
template, not an imitation. Slide types and their spec keys:

| type | keys |
| --- | --- |
| `title` | `title`, `subtitle` |
| `section` | `title`, `kicker` (the template's transition layout) |
| `statement` | `title`, `lines[]` (a paragraph each) |
| `process` | `title`, `kicker`, `nodes[]`, `edges[]`, `legend`, `notes` |
| `roadmap` | `title`, `kicker`, `intro`, `steps[{title, owner, body, current}]` |
| `cards` | `title`, `cards[{heading, lines[], accent, stat, stat_label}]`, `cols`; `stat` is a big-number callout above the heading (results slides) |
| `timebar` | `title`, `rows[{label, note, before_days, before_label, after_hours, after_label}]`, `legend`: a cream bar per activity for the days it took by hand and an orange bar for the hours it takes now, drawn to one scale |
| `donut` | `title`, `parts[{label, value, fill, means}]`, `stat`, `stat_label`, `legend`: a native doughnut chart (transparent over the gradient) with a chip legend and a stat box; zero-value parts appear in the legend only |
| `diagram` | `title`, `nodes[{id, x, y, w, h, kind, title, body, tag}]`, `edges[{from, to, via[[x,y]], from_side, to_side, label, label_at}]`, `legend`: a free-layout flow diagram. Kinds: `step` (cream box), `gate` (orange diamond, a check that stops the run), `data` (cream cylinder, a table), `domain` (white chip), `group` (cream outline with a label, drawn behind), `accent`, `note`. Arrows leave and enter on the sides that face each other, orthogonal, unless `via` waypoints are given. The two deployment flow diagrams in `jaspersoft/docs/deployment_deck/visuals/` are the worked examples |
| `steps` | `title`, `steps[{title, lines[]}]`, `cols` (2), `fill` (column or row), `body_pt`, `legend`: numbered cream boxes in columns, an orange number each; the step-by-step visual (8 to 10 steps) |
| `chevrons` | `title`, `stages[{title, sub, lines[], accent}]`, `notes[{title, body}]`: a left-to-right chevron chain (the promotion path), a description under each stage, a band of cream notes below |
| `bullets` | `title`, `columns[{heading, items[]}]` |
| `table` (`font` sets the body size for dense tables) | `title`, `columns[]`, `rows[[]]`, `widths[]` (inches, sum 20.4) |

Colour system (one rule, every slide): every container is cream, every chip or pill is white, orange is the highlight (kicker, accent pill, current roadmap step, the `tag` on a manual node), blue is titles and grey is body text. Nothing else is filled.

A process node: `{"id", "col", "row"}` on the grid or `{"x", "y", "w", "h"}` in inches, `title`,
`body`, and `kind`: `step` (cream, the automated thing), `manual` (cream with an orange `tag`, default "by hand": a scheduled or hand
step), `accent` (orange pill, a constraint), `card` (white sheet, an artifact), `note` (cream
text). Edges are `["from", "to"]` (straight when aligned, elbow otherwise) or
`{"from", "to", "via": [x, y]}` to route around something. Keep node bodies under about 60
characters (the generator drops to 16pt past that) and never more than 4 columns x 2 rows of
nodes plus one wide row underneath, which is what fits.

## QA

LibreOffice is not on this Mac; render through PowerPoint (a `save as PDF` AppleScript with
`activate` and short delays; the first call after a cold start can time out, run it again), then
`pdftoppm -jpeg -r 80` and look at every slide. Check text overflow, arrows crossing nodes, empty
space on card slides (the generator sizes cards to their content), and the pptx skill's
`validate.py`. Keep the spec in the repo next to the deck so the deck is regenerable.

## Worked example

`jaspersoft/docs/deployment_deck/spec.json` -> `jaspersoft/docs/OriginBA_Automated_Deployment.pptx`,
the end-to-end documentation of the automated BA deployment (2026-09-28), with the written version
in `jaspersoft/docs/ba_automated_deployment_end_to_end.md`.
