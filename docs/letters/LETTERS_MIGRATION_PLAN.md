# Letters and statements move into the portal

Decision (Chase, 2026-09-29): collections letters and customer statements are built inside the
Origin BA portal; the separate letter-print app (/Users/chase/originba-letterprint, Spring Boot +
JasperReports 7 + a Next.js review UI) will not be used. This plan is the port. Status per phase
is kept at the bottom.

## What the letter app does today

- **Data (done):** 14 SQL files per dialect (`service/src/main/resources/sql/{oracle,postgres}/`)
  run by `LetterRepository.java`, batched under one filter (date window or one CC_ID): ~11 round
  trips, ~7 s for a month at Ellensburg. A letter is a CI_CC row with `print_letter_sw='Y'`, tied
  to its process by the event completed on the letter date; the CI_FT balance is keyed by the
  letter, not the account; NSF letters go CI_CC_CHAR -> CI_ADJ -> CI_PAY_TNDR.ADJ_ID (never
  MICR_ID); late fees are CI_ADJ LPC rows. A backlog endpoint counts letters C2M raised but never
  extracted.
- **Types and wording (done):** `specs/letters.yml`, 10 types matched by contact type, template,
  then description pattern; per-client wording/branding filled for demo25 and Odessa only.
  `LetterComposer.java` writes the text (CISADM stores none).
- **Rendering (done):** one JRXML 7 letter (`templates/letter.jrxml`) with IMb via barcode4j;
  Odessa's seven JRS 10 templates fed by C2M's XML extract; the Code 128 + Luhn remit scan line on
  the late notice only.
- **Review UI (done, read-only):** filters, search, sort, PDF beside its data, runs, mailing.
- **Runs (partial):** single-thread executor, H2 + PDFs on disk, no retention.
- **Mail loop (stubbed):** A-Qua export/import with synthetic fixed-width layouts; IMb shape check.
- **Missing entirely:** authentication, organization isolation, approval, audit; EBILL routes not
  excluded from mailing; the letter-to-process link unverified at most Oracle clients; Odessa's
  letter codes pending.
- **Statements:** the bill side was deleted (`e572ff9`); its SQL and DATA_RULES are recoverable
  from `e572ff9^`. `reports/billing_customer_statement.jrxml` here is an unusable JR6 draft.

## Decisions for the port

- **Render with reportlab** (already in the API image). JRXML coordinates are points, as are
  reportlab's, so `letter.jrxml` ports position for position; DejaVu Sans keeps line breaks.
  reportlab 4.4.5 has `usps4s.USPS_4State` (IMb) and `code128`; the USPS-B-3200 example
  (tracking 01234567094987654321, routing 01234567891) encodes to
  `AADTFFDFTDADTAADAATFDTDDAAADDTDTTDAFADADDDTFFFDDTTTADFAAADFTDAADA` - the golden test. A Java
  sidecar (second image, JVM, service auth) and JRS REST (per-client reachability, seconds per
  render) cost more; WeasyPrint needs native libraries and has no IMb.
- **Read raw CISADM** per organization through the portal's own connections (Postgres orgs: the
  `cisadm` landing schema; Oracle orgs: `CISADM.`-qualified names, so the pooled session is never
  altered). Never reuse `execute_query`
  for letters: it stops at 5,000 rows silently (a month of Ellensburg events is 23,157); fetch
  all with a ceiling that raises.
- **dbt adds `rpt_collection_letter`** (one row per letter: type, process, arrears, next action,
  cut date, balance as of the letter, printed date; no names or addresses) for analytics, backlog
  and parity; a portal test asserts the letter list matches it. The print path stays on raw data
  (freshness, and the reporting layer deliberately drops names, addresses and bill totals).
- **Security:** org only from `require_org_for_data`; ids validated `^(CC|ADJ)-\d{1,14}$`;
  permissions `letters:read`, `letters:generate`, `letters:approve` (not by the run's creator),
  `letters:release`; restricted (row-rule) users refused; every preview, PDF, run, approval,
  release, export and import audited with ids and counts only; `Cache-Control: no-store`; no PDFs
  on container disk; run manifests in the org store with retention; letters SQL run through the
  reporting-scope validators; synthetic fixtures only; never write `LETTER_PRINT_DTTM`.

## Phases (tests first in every phase)

0. **Prepare:** push the letter app's 4 unpushed commits; capture parity goldens from the Java app
   (demo25 2022; Ellensburg over VPN); keep its sample PDFs as visual references.
1. **demo25 collections letters: list, preview, PDF** - `api/letters/{catalog,composer,source,
   repository,render,routes}.py`, `api/letters/sql/postgres/*.sql`, `config/letters.yml`, DejaVu
   fonts; `src/app/letters/page.tsx`, `src/components/letters/*`, nav entry behind `letters:read`.
   Tests: catalog (incl. the "budget activated" regression), composer, repository (single letter
   == same letter in the list; balance by letter; row ceiling raises), SQL fence, routes
   (403/422/404/503, audit without names, no-store), render (one page, address in the #10 window,
   no client strings in the specimen), demo25 parity (skipped without the DB URL), vitest.
2. **Oracle clients, late fees, NSF, branding** - `sql/oracle/*.sql`, `oracledb` in the image,
   Odessa/Ellensburg wording; Ellensburg counts match the golden at ~10 s database time.
3. **Runs and approval** - draft -> approved -> released, frozen manifest, four-eyes rule.
4. **Mail loop and barcodes** - fixed-width specs, A-Qua export/import, USPS golden, Luhn vectors,
   EBILL exclusion.
5. **Odessa forms, statements, retirement** - Odessa late-notice form (tear line at 544 pt, scan
   line), statements from `e572ff9^`, then archive the letter app and move its docs here.

## Risks

Layout drift from the City-approved Odessa form; the deployed API may not reach client VPNs;
long runs on a stateless two-worker API without a job queue; silent truncation if the generic
query path is reused; PII accumulating in portal state; the letter app's unpushed commits lost
at retirement.

## Open questions for Chase

1. Does Odessa's JRS + C2M XML extract stay the production print path, or does the portal replace it?
2. Is operating model A (C2M's extract keeps stamping LETTER_PRINT_DTTM) confirmed?
3. Who approves runs: client editors only, or Origin platform admins too? (Default applied in
   phase 3: editors and admins, never the run's creator.)
4. Where are released PDFs stored, and for how long? (Default applied in phase 3: nowhere. The print
   file is rebuilt from CISADM on every download and only the run's manifest is kept.)
5. Is a "customer statement" a reprint of one bill, or an account statement over a date range?
6. Should the letter-type mapping become a dbt seed beside rpt_collection_letter?
7. Should EBILL routes be excluded from the mailing file?
8. When do the real A-Qua layouts and Odessa's letter codes arrive?

## Status

| Phase | State |
| --- | --- |
| 0 | not started |
| 1 | merged: `/portal/letters` list, preview and PDF for Postgres orgs behind `letters:read` (editor, admin); `/letters` (window picker, search, type and status filters, sort, PDF preview beside the data behind it, Download PDF), nav entry never for row-restricted people; `e2e/letters.spec.ts` ran on demo25. The `rpt_collection_letter` parity test is still to do |
| 2 | on `feature/letters-oracle`: `sql/oracle/*.sql` (the letter app's SQL, `CISADM.`-qualified), the dialect picked from the org's engine, one `SET TRANSACTION READ ONLY`, NUMBER as Decimal, Oracle orgs served (no connection or unreachable: 503; other engines: 501). Ellensburg May 2026: 3,171 letters (1,499 contacts + 1,672 late fees), the same ids as the letter app's `letters.sql` and `late_fees.sql`; 5.0 s database time warm, 20-45 s wall over the VPN (the candidate-process events and services are ~62,000 rows each); a cold `CI_FT` made the balances query 45-60+ s, hence a 120 s call timeout. PDFs one page, address in the window (839 letters checked). `e2e/letters.spec.ts` runs on Ellensburg. Not done: Ellensburg/Odessa wording and branding, `oracledb` in the deployed image, late fees and NSF wording at real clients |
| 3 | on `feature/letter-runs`: `POST /portal/letters/runs` freezes a window's letters (optionally by type and printed status) into a draft run: ids, counts by type and a fingerprint per letter (a hash of everything the page prints: words, amounts, dates, address; never the words themselves) in the org store (`letter_runs`). `approve` (letters:approve) only from draft and never by the creator (403); `release` (letters:release) only from approved: every letter is read again and a changed or missing one refuses the release (409, with the counts) so the run is redrafted; otherwise ONE PDF in manifest order, built in memory and streamed, and the run is marked released (who, when, pages); a released run downloads again under the same check; `cancel` (creator or admin) from draft or approved. Every create, approve, release, download, refused release and cancel is audited with ids and counts. The Letters page has a Runs area (create from the letters shown, the runs table, Approve disabled with the four-eyes reason for its creator). Tests: `tests/test_letters_runs.py`, `src/lib/letterRuns.test.ts`, `e2e/letters.spec.ts` (the stubbed approve/release path passed; the live Ellensburg create has not run yet, see docs/PORTAL_ISSUES_LOG.md) |

Phase 3 defaults, each the owner's to change: **who approves** is anyone with `letters:approve`
(editors and admins) except the run's creator, matched by user id or email; **retention** keeps
the last 200 runs per organization (`MAX_RUNS`), the oldest released or cancelled run makes room,
and a new draft is refused while 200 are still open; a run holds at most **5,000 letters**
(`MAX_RUN_LETTERS`: ~4 ms and ~3 KB a page rendered in memory; a month at Ellensburg is ~3,200); a
run's filters are letter type and printed status only (a search could carry a customer's name into
the store); the print stamp C2M adds after mailing (`LETTER_PRINT_DTTM`) is not part of a letter's
fingerprint, so a stamped letter still downloads again.
