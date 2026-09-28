# Origin BA and JasperSoft: what the portal replaces today

Status as of 2026-09-28, after the parity build-out on `feature/assistant`. It says
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
| Saved views | Yes | Builder definitions (never SQL); owner, private or organization-wide, folders; refused past 200 per org, never silently deleted |
| Dashboards | Yes | Up to 8 tiles, cross-filtering, drill to the explorer, owner, visibility and folders, 50 per org |
| Scheduled delivery | Partly | Daily, weekly, monthly email of a saved view as **PDF, Excel or CSV**, with its saved filters; missed runs caught up once; Send now. **Needs:** the hourly runner deployed, SMTP configured |
| Exports | Partly | Excel from explorer and dashboards, CSV from SQL and assistant answers (formula-safe), server-side PDF on schedules. On-screen PDF buttons still use the browser print dialog |
| Alerts | Partly | Thresholds on the home KPIs, emailed on breach. Not on arbitrary views |
| Input controls / prompts | Yes | Any saved filter can be asked for when the view opens (Report parameters: value lists narrowed by the answers above them, date ranges, saved defaults for schedules) |
| Formatted, paginated reports (JRXML) | No | Letters and statements live in Jaspersoft and the separate letter-print app |
| Security | Mostly | Roles, workstream grants, org isolation, **row-level security within an org** (per-user rules on a column, fail-closed; raw SQL, the assistant and data quality refused to restricted users; schedules keep the creator's rules), OIDC sign-in with IdP group mapping (role, client, access groups, row rules synced at every sign-in; removal from every group deactivates the account), audit log. **No** SAML |
| Ownership and sharing | Yes | Owner on every view, dashboard and schedule; private items; only owner or admin edits; folders for views and dashboards |
| Per-client branding | Yes | An organization's `branding` block in `config/portal_organizations.json` (`brand`: name, tagline, `logo_src` a path the portal serves; `theme`: accent colours) is merged over the default for that organization; its logo sits beside Origin's in the header and heads its PDFs. Invalid colours and outside logos are ignored |
| Embedding | Yes | A saved view's "Embed" action makes a signed link (at most a day) and an iframe snippet: that one view, with its creator's current access, framed only by the sites in `EMBED_ALLOWED_ORIGINS` (`api/embed.py`, `tests/test_embed.py`). No API keys for other systems yet |
| Observability | Partly | Request id on every response, one log line per request, 500s name a reference. No error-reporting service or metrics yet |
| Performance at scale | Partly | Row counts from statistics, 5-minute result cache. First visits over multi-million-row canvases are slow (25 s on Ellensburg); pre-aggregates are a scale-plan item |

## Order to close the gaps

1. **Deploy the schedule runner and SMTP** (infrastructure; Shankar). Without the hourly
   `python -m api.report_schedule_runner` and SMTP settings, schedules and alerts save but
   never send. The Docker image needs `openpyxl` and `reportlab` (already in
   `deploy/requirements-api.txt`).
2. Done 2026-09-28: owners and private items; report parameters; row-level security.
3. **Server-side PDF for on-screen exports** (S): reuse the schedule PDF renderer for the
   explorer and dashboard PDF buttons, so a PDF looks the same wherever it comes from.
4. Done 2026-09-28: folders.
5. **SAML** (M), for identity providers without OIDC.
6. **Pre-aggregated tables** for the heavy ready-to-run reports (see the dbt repo's
   `docs/LARGE_CLIENT_SCALE_PLAN.md`).
7. **Formatted reports** (L): decide whether letters and statements move into the portal
   or stay in the letter-print app with the portal linking to them.
8. Done 2026-09-28: embedding.

## Known risks

- `xlsx@0.18.5` (SheetJS) carries published advisories for reading crafted files. The portal
  only writes workbooks, which those advisories do not cover; move to SheetJS's own
  distribution when the export code is next touched.
