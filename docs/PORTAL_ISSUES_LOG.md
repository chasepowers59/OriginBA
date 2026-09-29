# Portal issues log

The one place a portal finding is written down: what is open (with how to reproduce), what
was fixed (with the commit and the test that pins it), and decisions. Add the entry when you
find the issue. Skill: `.claude/skills/originba-portal-qa`. Never paste real client data here.

## Open

| Found | Issue | Reproduce / where | Next step |
| --- | --- | --- | --- |
| 2026-09-29 | The "INT_DEV (internal dev CISADM)" organization reads the demo25 Postgres warehouse (identical build stamp), not INT_DEV | Settings > System health: `dev` and `demo25` stamps are equal | Point `dev` at the INT_DEV in-database warehouse or rename the label |
| 2026-09-29 | Home shows two question boxes: Ask Ori and "Ask a question / Everyday utility metrics" (the governed-metric search), which Ori already tries first | Home page, below Ori | Decide with the UI review: fold the governed search into Ori or label it as vetted metrics |
| 2026-09-29 | `scripts/jaspersoft/jrs_repository.py job-run` calls `POST /rest_v2/jobs/<id>/run`, which JasperReports Server 10.0 does not have (404) | Any job-run against prod or test | Remove or rebuild the command (task queued); JRS 10 has no REST run-now |
| 2026-09-29 | `.env` line 17 (`JAVA_HOME`) has an unquoted value with a space; `set -a; . ./.env` prints `command not found` in zsh | `set -a && . ./.env` | Quote the value (owner's file; never print it) |
| 2026-09-28 | The opening report of a >1M-row canvas is still slow on the first visit to any report other than the warmed opening one (~25 s at Ellensburg for rpt_billed_charge) | Explorer, pick a second ready-to-run report on rpt_billed_charge | Pre-aggregates, with exactness tests (plan in progress) |

## Fixed

| Found | Issue | Fix | Pinned by |
| --- | --- | --- | --- |
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
