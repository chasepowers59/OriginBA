# OriginBA Analytics Portal POC

OriginBA-branded internal proof-of-concept for exploring governed Oracle snapshot tables through a modern web UI instead of Jaspersoft Ad Hoc. **Demo database only** — no client DB routing in this phase.

## Architecture

```
Next.js (apps/analytics-portal)  →  FastAPI (api/app.py)  →  Oracle demo (DEMO_* .env)
```

- **Lite builder:** pick allowlisted dimensions, measures, and date range; server builds governed SQL.
- **Premade reports:** curated presets per snapshot from `output/snapshot_explorer_catalog.json`.
- **No raw SQL** from the browser; no client picker.

## Prerequisites

1. Demo snapshots loaded on the demo database (active 7 + consolidation 12 QA reference: `deploy/snapshot_rollout_logs/demo/`).
2. `.env` at repo root with demo credentials:

```env
DEMO_DB_USER=...
DEMO_DB_PASSWORD=...
DEMO_ORACLE_DSN=smartcity-db-demo.example.com:1521/SERVICE
ORACLE_CLIENT_LIB_DIR=/path/to/instantclient   # if thick mode required
DB_THICK_MODE=1                                 # optional
```

3. Python deps (from repo root, venv recommended):

```bash
pip install -r pipeline/requirements.txt
```

4. Generate / refresh catalog metadata:

```bash
python3 scripts/build_snapshot_explorer_catalog.py
```

## Run locally

**Terminal 1 — API**

```bash
cd /path/to/OriginBA-3
uvicorn api.app:app --reload --port 8000
```

**Terminal 2 — Frontend**

```bash
cd apps/analytics-portal
cp .env.local.example .env.local
npm install
npm run dev
```

Open **http://localhost:3000** — branded as **OriginBA Snapshot Explorer**.

## POC snapshots (5 tabs)

| Snapshot | Workstream |
|---|---|
| `WORKFLOW_QUEUE_RPT_CURR` | common |
| `BSEG_BILLED_USAGE_RPT_CURR` | billing |
| `FT_RPT_CURR` | finance |
| `CASE_PREM_CONTACT_RPT_CURR` | customer_ops |
| `OPS_EXCEPTION_RPT_CURR` | common |

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | API + demo DB config status |
| GET | `/snapshots` | List POC snapshots |
| GET | `/snapshots/{id}/metadata` | Dimensions, measures, premade reports |
| POST | `/snapshots/{id}/query` | Run governed aggregate query |

Example query body:

```json
{
  "dimensions": ["ENTRY_STATUS_DESC"],
  "measures": [{"field": "*", "agg": "count"}],
  "filters": [
    {"field": "TD_CRE_DTTM", "op": "between", "value": ["2025-01-01", "2025-06-01"]},
    {"field": "QUEUE_SOURCE", "op": "eq", "value": "TODO"}
  ],
  "limit": 500
}
```

## Tests

```bash
python3 -m unittest tests.test_query_builder -v

# Optional live demo tests (VPN + API running):
ORIGINBA_LIVE_DEMO_TESTS=1 python3 -m unittest tests.test_live_demo_api -v
```

## Non-goals (POC)

- Client database connections (newark, citycorp, etc.)
- Drag-and-drop Ad Hoc canvas
- Cross-snapshot joins
- PDF/Excel export (keep Jaspersoft for formal outputs)
- Replacing all 104 Standard Offering reports

## Related docs

- [snapshot_client_reporting_guide.md](../sql/performance/snapshots/docs/snapshot_client_reporting_guide.md)
- [snapshot_explorer_catalog.json](../output/snapshot_explorer_catalog.json)
