# Standard Offering Release 26 deck and visuals

Where everything from the 2026-09-28 documentation work lives, and how to regenerate it.

| What | Path | Regenerate with |
| --- | --- | --- |
| The deck (24 slides) | `jaspersoft/docs/OriginBA_Automated_Deployment.pptx` | `python3 .claude/skills/originba-process-deck/scripts/build_process_deck.py jaspersoft/docs/deployment_deck/spec.json <out.pptx>` |
| Its spec | `jaspersoft/docs/deployment_deck/spec.json` | edit, then rebuild |
| Written companion | `jaspersoft/docs/ba_automated_deployment_end_to_end.md` | by hand |
| The two flow diagrams and the two object tables, standalone | `visuals/Standard_Offering_and_Database_Steps.pptx`, `visuals/spec.json` | `visuals/visuals.py` is the single source; the deck spec imports the same objects |
| Editable draw.io source (two pages, hover tooltips, hidden Commands and Checks layers) | `visuals/deployment_flows.drawio` | `python3 .claude/skills/originba-drawio-visuals/scripts/spec_to_drawio.py visuals/spec.json -o visuals/deployment_flows.drawio` |
| PNG and SVG exports (XML embedded, reopen in draw.io) | `visuals/*.drawio.png`, `visuals/*.drawio.svg` | `/Applications/draw.io.app/Contents/MacOS/draw.io -x -f png -e -b 20 -s 2 -p <page> -o <out> visuals/deployment_flows.drawio` |

Skills that carry the rules (palette, one colour system, gate formatting, the text-fit guard, QA on 2x
export crops): `.claude/skills/originba-process-deck/SKILL.md` and `.claude/skills/originba-drawio-visuals/SKILL.md`.
The draw.io MCP server is registered in `.mcp.json`; draw.io Desktop 31.5.3 is installed for exports.

Facts the diagrams state were checked against the scripts on 2026-09-28: rolling window 3 months rebuilt
and 24 kept on every table (6-month variants at CityCorp and Odessa), baseline seeds the retained 24 months,
schedule twice daily from 10:00 and 16:00 UTC with a 30-minute stagger, eight parallel baseline jobs, and
which domain reads each CMS view (from the packaged domain schemas).
