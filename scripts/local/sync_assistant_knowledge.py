#!/usr/bin/env python3
"""Copy the C2M knowledge the assistant reasons with from the dbt repo's skills.

The assistant's system prompt carries the same skills a Claude Code session loads when it
writes CISADM SQL: the SQL traps, the functional architecture, the body of knowledge. They
are maintained in originba_dbt/.claude/skills and copied here so the API image is
self-contained. Run after the skills change; regenerate_all does not know about this yet.

    python3 scripts/local/sync_assistant_knowledge.py            # ORIGINBA_DBT_DIR or ../originba_dbt
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[2]
DBT = Path(os.environ.get("ORIGINBA_DBT_DIR") or HERE.parent / "originba_dbt")
OUT = HERE / "api" / "assistant_knowledge"
SOURCES = {
    "cisadm-sql.md": ".claude/skills/cisadm-sql/SKILL.md",
    "c2m-functional-architect.md": ".claude/skills/c2m-functional-architect/SKILL.md",
    "c2m-body-of-knowledge.md": ".claude/skills/c2m-functional-architect/references/functional-architect-bok.md",
}


def main() -> int:
    if not DBT.exists():
        print(f"originba_dbt not found at {DBT}; set ORIGINBA_DBT_DIR", file=sys.stderr)
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    for name, rel in SOURCES.items():
        src = DBT / rel
        text = src.read_text()
        (OUT / name).write_text(f"<!-- GENERATED from originba_dbt/{rel} by scripts/local/sync_assistant_knowledge.py; do not edit -->\n\n{text}")
        print(f"  {name:32} {len(text):>7} chars  <- {rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
