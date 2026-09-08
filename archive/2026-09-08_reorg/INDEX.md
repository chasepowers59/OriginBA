# Archive 2026-09-08 (repository reorganization)

Nothing here is deleted; every item was superseded, duplicated, or never referenced, and a
pointer stands at its old path (`ARCHIVED.md` in the parent directory, or `README.md` in an
emptied directory). `tests/test_repo_structure.py` (D2, D7) checks that live code never reads
from here and that every row has its pointer. `jaspersoft/README.md` and `README.md` say where
the current equivalent lives.

| original path | why archived | current equivalent |
| --- | --- | --- |
| `exports/` | `source_of_truth_bundle_2026-03-19` -- a frozen fork of docs that already drifted from `docs/` and `knowledge_base/`; zero references | `docs/`, `knowledge_base/` |
| `docs/claude_handoff/` | 2026-07/08 handoff snapshots; its `mcp/originba_oracle_mcp.py` is byte-identical to `scripts/local/originba_oracle_mcp.py` | `scripts/local/originba_oracle_mcp.py`, `.claude/skills/` |
| `docs/mcp-setup.md`, `mcp.json.example` | the SQLcl-in-Cursor MCP setup (Windows era); the MCP actually served is `scripts/local/originba_oracle_mcp.py` with `prod_enabled: false` | `scripts/local/originba_oracle_mcp.py` |
| `Dockerfile`, `railway.toml`, `.railwayignore` | the Railway image; it COPYs `output/snapshot_explorer_catalog.json`, which the catalog retirement (2026-09-04) deleted, so it has not built since. Railway is retired; Fly and Render build `deploy/Dockerfile.api` | `deploy/Dockerfile.api`, `DEPLOYMENT.md` |
| `deploy/{CityCorp,CityCorpPROD,CollegeStation,Ellensburg,Fondulac,Newark,Odessa}DS.zip` | flat backups of the DataSource exports that live, unpacked and documented, under `deploy/jaspersoft_datasources/clients/` | `deploy/jaspersoft_datasources/clients/` |
| `skills/` | eight 2026-03..06 skills nothing could load; folded into `.claude/skills/originba-*/SKILL.md` | `.claude/skills/` |
| `docs/cowork/skills/` | six Co-work paste-in copies (2026-08-11) of skills that now exist in loadable form | `.claude/skills/originba-*/SKILL.md` |
