---
name: originba-portal-qa
description: How to test the Origin BA portal end to end and not be fooled — the local stack, the four browser specs (crawl, accessibility, pixels, Ori), the known false failures, verifying against Ellensburg's real warehouse without printing secrets, and the issues log every finding goes into. Load before any portal QA, bug hunt or release check.
---

# Portal QA: run it, trust it, log it

## The local stack (what each organization really reads)

`.claude/launch.json` in /Users/chase/originba_dbt: `portal-api` (8010, uvicorn **without
--reload**: restart it after any backend edit or you are testing old code), `portal-ui` (3001,
Next dev, hot reload), `portal-api-stub` (Ori with `ASSISTANT_MODEL=stub`, zero tokens).

| Org id | Picker label | Reads |
| --- | --- | --- |
| `ellensburg` | Ellensburg | Oracle in-database dbt warehouse `ORIGINBA_REPORTING` on the Ellensburg 25.4 TEST instance (VPN). Real client data: the local default org |
| `demo25` | Demo 25.4 | local Postgres demo warehouse. NOT a comparison source (below) |
| `dev` | INT_DEV (internal dev CISADM) | the SAME Postgres as demo25 (identical build stamp), despite its label |
| citycorp, college_station, fond_du_lac, newark, odessa, demo | client names | Oracle, no dbt warehouse yet: pages say the warehouse is not built |

A browser with no active organization sends no `X-Organization-Id` and reads the default
(Ellensburg). The API log shows `org=-` for those requests; that is not a bug.

## Ellensburg only (Chase, 2026-09-29)

"Stop using Demo25's data and stick to only using Ellensburg": every check, live verification
and measured number uses Ellensburg. The specs take their organization from `e2e/org.ts`
(`E2E_ORG`, default `ellensburg`; `CRAWL_ORGS` for several). With the VPN down, say the check
could not run; never fall back to demo25. Letters included: they read raw CISADM through
the org's own Oracle connection. Moving the checks found the data-quality worklist refusing Oracle organizations
(docs/PORTAL_ISSUES_LOG.md).

## Desktop web only (Chase, 2026-09-29)

The portal ships as a desktop web app, not a phone app: the Playwright config has one
project, `desktop` (1440 x 900), and the phone-only specs are gone (in git history).

## The specs (apps/analytics-portal/e2e/, Playwright with the installed Chrome)

| Spec | Command | Time |
| --- | --- | --- |
| Crawl: every route on Ellensburg | `npx playwright test e2e/crawl.spec.ts` | ~4 min, 56 visits |
| Accessibility (axe, WCAG 2.1 AA) incl. every Settings tab | `npx playwright test e2e/a11y.spec.ts` (`COLOR_SCHEME=dark` for dark) | ~1 min |
| Pixels (local baselines, Ellensburg; retake after a rebuild) | `npx playwright test e2e/visual.spec.ts` | ~1 min |
| Ori (naming, the home panel with stubbed routes), data quality, library | `npx playwright test e2e/ori.spec.ts e2e/ori-findings.spec.ts e2e/dq.spec.ts e2e/library.spec.ts` | ~1 min |
| Stale-data notice (live: none; stubbed stale: named on every page) | `npx playwright test e2e/freshness.spec.ts` | ~10 s |
| Letters (Ellensburg May 2026 rows, PDF preview, 366-day refusal; a run from a one-day window with the creator's Approve disabled, then cancelled; approve and release with stubbed answers only; a cold month is tens of seconds over the VPN) | `npx playwright test e2e/letters.spec.ts` | ~1 min |

Unit suites: `cd /Users/chase/OriginBA-3 && ENVIRONMENT=test python3 -m pytest tests -q`,
`cd apps/analytics-portal && npx tsc --noEmit && npx vitest run`.

## False failures (recognise them, then re-run just that page)

- `Execution context was destroyed ... navigation` during a crawl: you edited a frontend file
  and hot reload navigated the page. Do not edit UI files while a crawl runs.
- `ERR_CONNECTION_REFUSED` / failed API calls on a burst of pages: the API was restarted.
- A pixel diff after an intended UI change: open `e2e/.out/results/<test>/…-diff.png`, confirm
  the red is ONLY the intended change, then `--update-snapshots -g "<page>"`. Never refresh a
  baseline you have not looked at.
- A crawl or test red because a red TDD run wrote into `data/analytics_portal/*.json`: tests
  must patch store paths to a temp dir (see tests/test_row_security.py). `git status data/`
  after every run.

## Measuring on real data without printing secrets

Load the API's own environment from launch.json inside Python and never print it:
parse `runtimeArgs[1]` of `portal-api` with shlex, set `os.environ` for `KEY=VALUE` tokens, then
call the API functions directly (e.g. `api.snapshot_explorer.cached_query`,
`api.data_version.data_version`). Ellensburg needs the VPN. Say which org and engine a
number came from; Ellensburg is Oracle, not a local Postgres copy (a correction made 2026-09-29).

## Output and data safety

`e2e/.out/` is gitignored: Ellensburg screenshots show real customer names and amounts. Never
paste them into docs, commits or chat. Test fixtures are fabricated.

## Every finding goes in the log

`docs/PORTAL_ISSUES_LOG.md`: open issues (with how to reproduce), fixed ones (with the commit
and the test that pins them), and decisions. Add the entry when you find it, not at the end.
