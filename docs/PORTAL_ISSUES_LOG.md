# Portal issues log

The one place a portal finding is written down: what is open (with how to reproduce), what
was fixed (with the commit and the test that pins it), and decisions. Add the entry when you
find the issue. Skill: `.claude/skills/originba-portal-qa`. Never paste real client data here.

## Open

| Found | Issue | Reproduce / where | Next step |
| --- | --- | --- | --- |
| 2026-09-29 | Locally, the "INT_DEV (internal dev CISADM)" organization shows demo25 data: the local launch config sets `WAREHOUSE_DATABASE_URL` (the `dev` org's key) to the demo25 database. In the cloud deployment it is INT_DEV | Settings > System health: `dev` and `demo25` stamps are equal | Owner's call: point the local key at an INT_DEV copy, or accept the alias locally |
| 2026-09-29 | `scripts/jaspersoft/jrs_repository.py job-run` calls `POST /rest_v2/jobs/<id>/run`, which JasperReports Server 10.0 does not have (404) | Any job-run against prod or test | Remove or rebuild the command (task queued); JRS 10 has no REST run-now |
| 2026-09-29 | `.env` line 17 (`JAVA_HOME`) has an unquoted value with a space; `set -a; . ./.env` prints `command not found` in zsh | `set -a && . ./.env` | Quote the value (owner's file; never print it) |
| 2026-09-29 | Explorer: "Combined total" and "X leads at N% of the total" add different units (kWh + therms + gallons) when the breakdown is the unit of measure | Explorer, billed usage by unit of measure | UI-1: suppress total and share when a unit column is a dimension (ResultsPanel, businessLabels) |
| 2026-09-29 | Charts: the value ramp paints small categories dark red, so red reads as "bad" for ordinary rows; mid-ramp bars look mauve | Any explorer bar chart | UI-2: DECISION (palette rule is cross-app): one hue per series, red only for negatives/thresholds |
| 2026-09-29 | Explorer: "All dates" chip while the date inputs still show a window; aged balance says "No data" under a large record count and offers a widen that cannot widen | Ellensburg aged balance explorer | UI-3: sync inputs to the applied window; confirm the query drops it |
| 2026-09-29 | One thing, eight names (report, canvas, reporting table, domain, data model, pack, workstream, process); nav "Explore" opens the builder; two library taxonomies with different counts | Nav, library, workstreams | UI-4: DECISION: one glossary and one grouping |
| 2026-09-29 | Engineering text on business screens: "contracted models", "0 tokens", "Trusted data domain", table names, "UOM", Fernet / PORTAL_SETTINGS_TOKEN | Footer, home, explorer header, settings | UI-5: plain-language copy; lineage behind the IT-review disclosure |
| 2026-09-29 | Explorer overflows at 320 px: the export row does not wrap (page 347 px wide); the crawl's overflow check misses it | Any /explore at small-phone | UI-6: wrap + one Export menu; crawl measures the widest element |
| 2026-09-29 | Detail tables: amounts left-aligned, "Total Total Balance", invisible row hover in light theme | Explorer detail table | UI-9: right-aligned tabular numbers, no duplicate prefix, token hover |
| 2026-09-29 | Explorer: results buried under a 3,300 px list of report cards below 1280 px; Save/Pin at the bottom of the rail | Explorer at laptop width | UI-10: titles-only rail, results first when stacked, save in the result toolbar |
| 2026-09-29 | Dates, numbers and money are formatted differently page to page; odd tick steps; "12:00 AM" on date-only values | Everywhere | UI-16: DECISION + one formatter set in format.ts |
| 2026-09-29 | Slow Ellensburg explorer pages (17-32 s) show only a grey skeleton | Ellensburg billed usage, billed charge, GL | UI-20: "Running…" with elapsed time and cancel |
| 2026-09-29 | A missing KPI trend value is labelled "Unknown" by the backend; charts now say "Not recorded" | api/kpi_runner.py trend_from_rows | use "Not recorded" |
| 2026-09-29 | The server PDF still prints "No rows in this window." under a card that failed to load (its note now says why) | api/report_schedules.py sections_to_pdf | no "No rows" line when the section note reports a failure |
| 2026-09-29 | The frontend skill still describes long axis labels as skipped ticks (preserveStartEnd); since 552cde49 that applies only to date/ordered axes | .claude/skills/originba-frontend/SKILL.md | update the chart section |
| 2026-09-29 | UI-5 remainder: "canvas", "UOM", table names and "tenant" still appear in some screens; per-answer token line shows to all users | explorer, builder, Ori answers | second copy pass; tokens for admins only |
| 2026-09-28 | The opening report of a >1M-row canvas is still slow on the first visit to any report other than the warmed opening one (~25 s at Ellensburg for rpt_billed_charge) | Explorer, pick a second ready-to-run report on rpt_billed_charge | Pre-aggregates, with exactness tests (plan in progress) |

## Fixed

| Found | Issue | Fix | Pinned by |
| --- | --- | --- | --- |
| 2026-09-29 | SQL workspace results ~50 px tall on phone; builder says "on the left" when the panel is above | UI-19: 666774bf | e2e/phone-workspaces.spec.ts |
| 2026-09-29 | B-13 privacy: GET /portal/saved-views filters by visibility only, not by the caller's workstream grant (same shape as B-11) | 2eb212b3 | tests/test_bug_hunt_fixes.py |
| 2026-09-29 | B-12: the dashboard PDF shows a failed card as "No value" / "No rows" | 76c0acce | src/lib/dashboardPdf.test.ts |
| 2026-09-29 | B-11: content-pack export includes dashboards the caller's workstream grants withhold (definitions only) | 0dfe87ac | tests/test_content_packs.py |
| 2026-09-29 | B-7: a saved-view alert reads an empty window (SUM NULL) as all-clear and resets a breach | 93223292 | tests/test_view_alerts.py |
| 2026-09-29 | B-6: scheduled PDFs from Postgres orgs print Decimal money unformatted, left-aligned, with no chart | 7971e2be | tests/test_pdf_export.py |
| 2026-09-29 | B-5: SSO row rules from two groups AND together (Water AND Sewer = no rows); a matching unrestricted group is overridden | e305f3b9 | tests/test_oidc_group_map.py |
| 2026-09-29 | Library is a 10,000 px (22,000 on phone) scroll; rail above the title on phones; two search boxes | 36797f76 | e2e/library.spec.ts, src/lib/libraryLayout.test.ts |
| 2026-09-29 | Data quality: every row shows a green "Done" that reads as a status; 10 px, ~20 px target | 3fd723e4 | e2e/dq.spec.ts |
| 2026-09-29 | Donut colours repeat past 5 slices; nulls show as a dash | 2b326ded, 552cde49 | src/lib/chartLayout.test.ts |
| 2026-09-29 | Zero and single-category results look broken (dashed "No trend data", $0-$4 axis, one "Unknown" bar, "leads at 100%") | 2b326ded, 552cde49 | src/lib/chartLayout.test.ts |
| 2026-09-29 | Explorer charts hide half their labels; 15-character cut makes look-alike labels | 2b326ded, 552cde49 | src/lib/chartLayout.test.ts |
| 2026-09-29 | KPI spark charts: 8.5 px labels, second line clipped, overlaps at 320 px | 2b326ded, 552cde49 | src/lib/chartLayout.test.ts |
| 2026-09-29 | B-10: uvicorn's default access log still prints /embed/<token> (credential) in full | f32ead4c | tests/test_deploy_access_log.py |
| 2026-09-29 | B-9: a warm pass that fails is never retried until the next rebuild (stamp marked warmed before building) | f32ead4c | tests/test_bug_hunt_fixes.py |
| 2026-09-29 | B-8: the cache warmer thread dies on the first unexpected error (catalog read, org list) and never warms again | f32ead4c | tests/test_bug_hunt_fixes.py |
| 2026-09-29 | B-4 privacy: GET /kpi-alerts returns alerts on other people's private views and ungranted canvases (title, recipients, last value) | f32ead4c | tests/test_bug_hunt_fixes.py |
| 2026-09-29 | B-3: an embed drops the view's saved window, scope and ready-to-run report filters (shows all-time, whole canvas, unbounded on a public route) | f32ead4c | tests/test_bug_hunt_fixes.py |
| 2026-09-29 | B-2: a connection outage's "not connected" summary is cached under the build stamp and shown for up to 12 h after the warehouse is back | f32ead4c | tests/test_bug_hunt_fixes.py |
| 2026-09-29 | B-1 security: creating an embed link never checks the creator's workstream grant, so a billing-only editor can publish debt data they cannot open | f32ead4c | tests/test_bug_hunt_fixes.py |
| 2026-09-29 | Home: two question boxes (Ori and the six-field governed-metric form); starter chips cut mid-row | UI-17: vetted-metric form folded under Ori (open for restricted readers), eyebrow "Vetted metrics" | e2e/ori.spec.ts |
| 2026-09-29 | On phones the organization switcher and the "viewing another client" warning disappear | UI-12: 3a8fbb68 | e2e/shell.spec.ts |
| 2026-09-29 | The floating Ask Ori button covers content, worst on phones | UI-11: 3a8fbb68 | e2e/shell.spec.ts |
| 2026-09-29 | Every canvas declared `default_date_preset: "last_12_months"` but the explorer ignored the string and opened on an unlisted 180-day window; no date chip was ever highlighted | 72c0d1a0 | tests/fixtures/date_presets.json (both suites) |
| 2026-09-29 | Saved-view alert values came back as Decimal; the JSON alert store would refuse them on the first real run | 8cf3cf47 | tests/test_view_alerts.py |
| 2026-09-29 | Settings > Users & access: role, organization and group dropdowns had no accessible name; the admin activity list scrolled out of keyboard reach | b931a4b6 | e2e/a11y.spec.ts (every Settings tab) |
| 2026-09-29 | The request log wrote embed-link tokens (credentials) in the path | 9ae7be1d | tests/test_system_health.py |
| 2026-09-29 | Chart axis on small counts printed "0 0 1 2 2 2 3" | ea0e925c | tests/test_dashboard_pdf.py |
| 2026-09-29 | Warmer log lines scrolled away; nobody could tell whether warming ran | 471dcdbb | tests/test_cache_warmer.py |
| 2026-09-28 | Security review findings (critical, high, medium, low) | bab40204, de26e216, e07ebfec | tests/test_security_review_fixes.py, tests/test_row_security.py |
| 2026-09-28 | Red TDD runs wrote alerts and schedules into `data/analytics_portal/` | 1b261080 | tests/test_row_security.py (temp stores) |

## Decisions

- 2026-09-29: the assistant is **Ori** ("Ask Ori, your AI analytics assistant"); words live in `src/lib/ori.ts`.
- 2026-09-29: letters and statements move INTO the portal; the separate letter-print app will not be used.
- 2026-09-29: the hourly schedule runner and SMTP stay parked (not a priority); the UI, correctness and speed come first.
- 2026-09-29: the explorer opens on the catalog's declared window (Last 12 months); switching back to six months is one line in the dbt catalog builder.
