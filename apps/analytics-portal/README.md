# Analytics Portal

Next.js UI for governed snapshot exploration, dashboards, and NLQ metrics.

## Local development

```bash
# From repo root — build catalog (required after registry/domain changes)
python3 scripts/build_snapshot_explorer_catalog.py

# API (auto-reloads catalog when output/snapshot_explorer_catalog.json changes)
uvicorn api.app:app --reload --port 8000

# Portal
cd apps/analytics-portal
npm install
npm run dev
```

Set `NEXT_PUBLIC_API_URL=http://localhost:8000` if the API is not on the default host.

## Data source settings (`/settings`)

Users can configure Oracle connectivity in the portal UI. Credentials are:

- Sent to the API over HTTPS only (never stored in `localStorage` or committed to git)
- Encrypted at rest in `output/.portal_data_source.vault` (Fernet)
- Never returned by the API after save (masked user/DSN only)

Optional production hardening in API `.env`:

```bash
# Require this token on X-Portal-Settings-Token for test/save/clear
PORTAL_SETTINGS_TOKEN=your-long-random-secret

# Or supply a fixed Fernet key instead of auto-generated output/.portal_vault_key
PORTAL_DB_ENCRYPTION_KEY=<fernet-key>
```

Generate a Fernet key: `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

## Catalog rebuild and cache

The API loads `output/snapshot_explorer_catalog.json` and **reloads automatically when the file mtime changes**. You do not need to restart uvicorn after `build_snapshot_explorer_catalog.py` if `--reload` is enabled.

If running without reload, call `reload_catalog()` or restart the API process after rebuilding the catalog.

## Report library (`/reports`)

Curated utility report packs (billing close, payments, operations, etc.) are defined in
`scripts/snapshot_portal_config.py` (`REPORT_LIBRARY_PACKS`), included in the catalog build, and
served at `GET /portal/report-library`. Rebuild the catalog after changing packs.

## Validation

```bash
python3 -m unittest tests/test_snapshot_premade_catalog.py
python3 scripts/local/smoke_analytics_portal.py
cd apps/analytics-portal && npm run build
```
