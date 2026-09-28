# Origin BA and JasperSoft: what the portal replaces today

Status as of 2026-09-28, after the crawl-and-refinement pass on `feature/assistant`. It says
what a utility gets from JasperSoft Server that the Origin BA portal does, partly does, or
does not do yet, and the order to close the gaps. Evidence is the code; each row names where.

## Where the portal already goes further

- **Natural-language answers.** The assistant writes and runs read-only SQL over the
  reporting canvases, shows every query, streams its progress, and each answer can be
  charted, downloaded as CSV, or saved as a view. Plain "how much" questions are answered by
  the vetted metrics first, at no model cost. Jaspersoft has nothing comparable.
- **One money rule.** Every total the portal shows counts only frozen, non-cancelled money
  (`api/money_rules.py`, checked by `tests/test_money_rules.py`).
- **Proof of the numbers.** Canvases are reconciled to the client's own database and the
  legacy snapshot tables; the assistant says how far a figure can be trusted.
- **Data quality worklist** with the action to take in CIS for each finding.

## Capability matrix

| Capability | Status | Where / what is missing |
| --- | --- | --- |
| Ad hoc exploration | Yes | Explorer per canvas, visual builder, SQL workspace (read-only, fenced) |
| Saved views | Yes | Builder definitions (never SQL); refused past 200 per org, never silently deleted |
| Dashboards | Yes | Up to 8 tiles, cross-filtering, drill to the explorer, 50 per org |
| Scheduled delivery | Partly | Daily, weekly, monthly email of a saved view as **PDF, Excel or CSV**, with its saved filters; missed runs caught up once; Send now. **Needs:** the hourly runner deployed, SMTP configured |
| Exports | Partly | Excel from explorer and dashboards, CSV from SQL and assistant answers (formula-safe), server-side PDF on schedules. On-screen PDF buttons still use the browser print dialog |
| Alerts | Partly | Thresholds on the home KPIs, emailed on breach. Not on arbitrary views |
| Input controls / prompts | Partly | Filters and date presets on every view; no prompted or cascading parameters on open |
| Formatted, paginated reports (JRXML) | No | Letters and statements live in Jaspersoft and the separate letter-print app |
| Security | Partly | Roles, workstream grants (the assistant respects them), org isolation, OIDC sign-in, audit log. **No** row-level security within an org, no SAML, no IdP group-to-role mapping |
| Ownership and sharing | No | Views and dashboards are org-wide; no owner, no private items, no folders |
| Per-client branding | No | One brand for all orgs; the org name is swapped |
| Embedding / API keys | No | OpenAPI docs are on; no embed SDK, API keys only for `/nlq` |
| Observability | Partly | Request id on every response, one log line per request, 500s name a reference. No error-reporting service or metrics yet |
| Performance at scale | Partly | Row counts from statistics, 5-minute result cache. First visits over multi-million-row canvases are slow (25 s on Ellensburg); pre-aggregates are a scale-plan item |

## Order to close the gaps

1. **Deploy the schedule runner and SMTP** (infrastructure; Shankar). Without the hourly
   `python -m api.report_schedule_runner` and SMTP settings, schedules and alerts save but
   never send. The Docker image needs `openpyxl` and `reportlab` (already in
   `deploy/requirements-api.txt`).
2. **Owners and private items** for views and dashboards (M): an owner field, "only me /
   my organization" sharing, and a folder per workstream.
3. **Prompted parameters** on saved views (M): mark a filter as "ask when opened", with
   a value list from the canvas; cascading lists after that.
4. **Server-side PDF for on-screen exports** (S): reuse the schedule PDF renderer for the
   explorer and dashboard PDF buttons, so a PDF looks the same wherever it comes from.
5. **Row-level security within an org** (L): a per-user filter (division, service type)
   applied by the query builder to every canvas that carries the column.
6. **IdP group-to-role mapping, then SAML** (M).
7. **Pre-aggregated tables** for the heavy ready-to-run reports (see the dbt repo's
   `docs/LARGE_CLIENT_SCALE_PLAN.md`).
8. **Formatted reports** (L): decide whether letters and statements move into the portal
   or stay in the letter-print app with the portal linking to them.
9. **Per-client branding and embedding** (M each), when a client asks.

## Known risks

- `xlsx@0.18.5` (SheetJS) carries published advisories for reading crafted files. The portal
  only writes workbooks, which those advisories do not cover; move to SheetJS's own
  distribution when the export code is next touched.
