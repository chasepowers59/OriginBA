# Portal: security hardening, Soul Palette V2.1, enterprise features, Demo 25.4

30 commits, fast-forward onto `main` (0 behind, no conflicts).

> **Merging this auto-deploys the API.** `render.yaml` has `branch: main` with
> `autoDeploy: true`. Read the *Deploy notes* at the bottom before merging — two env
> vars need to exist, and one behaviour change will take orgs offline if they don't.

---

## 1. Security — every CRITICAL and HIGH from the 2026-09-01 audit

A read-only isolation audit of both repos found 4 CRITICAL and 6 HIGH issues. All are
fixed, each with the failing test written first, and the bypasses are now regression
tests. Full evidence: `docs/SECURITY_AUDIT_2026-09-01.md`.

**CRITICAL**

- **C1 — the legacy Oracle SQL path had no fence at all.** `_validate` fenced only
  `postgres` and `oracle_dbt`, so six of eight orgs — with `database:sql` held by the
  lowest role — reached `MICR_ID`, `DBA_USERS`, `V$SESSION`, other schemas, `@dblink`
  and `UTL_HTTP`. Engine→fence is now a *total* mapping; an unknown engine is refused
  rather than waved through.
- **C2 — every org fell back to one shared warehouse.** `warehouse_url()` ended at a
  global key and then a hardcoded default, so `warehouse_configured()` was true for
  every input including Oracle orgs and non-existent org names. Now returns `None`
  unless the org genuinely has a warehouse; only `dev` may use the shared key.
- **C3 — `/dq/*` was unpermissioned** and used the caller's home org rather than the
  effective one, reaching that shared warehouse. Now requires `portal:read` and
  `require_org_for_data`.
- **C4 — the secrets guard was defeated by whole-row projection.** Blocking column
  *names* did nothing against `row_to_json(t)`, and the `SELECT *` rule covered only
  the tender table. The guard is now per table across all four secret-bearing tables.

**HIGH**

- **H1** the settings token was accepted *instead of* `data_source:manage`, and
  `verify_settings_token()` returns true when the token is unset (the default) — so
  any user could repoint their org's database. The connection test also returned raw
  driver errors, making it a network probe. Both closed.
- **H2** three credential fallbacks let one tenant inherit another's connection.
  Sharing is now explicit and defaults to nobody.
- **H3** snapshot-scoped raw SQL was scoped by *substring presence* — a comment naming
  the table satisfied it. Now parses FROM/JOIN targets.
- **H4** `ALERT_INFO` was a queryable `dimension` in the cisadm catalog while the SQL
  fence blocked the same column. Protected columns are now dropped at `allowed_fields()`,
  in the catalog, and in the generator.
- **H5** two routes referenced a `body` they never took — they ran the query, then
  500'd, and skipped their audit write.
- **H6** the JWT sat in a JS-readable cookie for 8 hours. Now set `httpOnly` by a
  same-origin route, clamped to the token's own life.
- **M1/M2** the Postgres fence gained the unqualified-catalog rule and function
  deny-list the Oracle fence always had.

Also: `.github/workflows/api-ci.yml` — the Python suite was **never gated by CI**.
It now runs on every change to `api/`, `tests/` or `config/`.

## 2. Soul Palette V2.1

Reed's palette adopted **verbatim** (37 tokens, both columns, nothing redefined) plus
7 additive portal tokens. Spec: `docs/design/` (HTML + Markdown + paste-ready CSS).

The value ramp had a real bug: an HSL hue sweep rendered mid-range bars **vivid
magenta and violet**. It now interpolates in Oklab between two palette tokens, ending
at the palette's own `over` red so the suite has one red. 205 hardcoded Tailwind
colour classes across 39 files became tokens, and `audit-brand.mjs` now fails the
build on any Tailwind palette class.

## 3. Enterprise features (all tests-first)

OIDC SSO (Azure AD, JIT provisioning as role `user` — SSO never mints admins) ·
scheduled report delivery + KPI threshold alerts on one hourly runner · true `.xlsx`
export · access audit covering report runs, SQL executes and fence refusals ·
annotations · portal-state backup script · Aptos brand font · accessibility pass.

Plus the UX review backlog closed out end to end, and a lean/dedupe pass that removed
675 lines while adding 655.

## 4. Demo 25.4 warehouse

New `demo25` org: a full census of PDEMODB_DEMO (23ai) — 4.79M landing rows, all 200
source tables, zero schema drift.

- **Merge path proven at volume:** fed a real CDC delta, incremental merged 1,210 FTs
  and 395 billed charges, and incremental-over-delta equals full-refresh with **zero
  rows different in either direction** — the first time that has been demonstrated
  against a 3.5M-row fact.
- **A real bug surfaced:** two GL extract batches broke the assumption behind
  `rpt_gl` showing a run number alone. The canvas now carries `GL Extract Batch Code`
  (the remedy the test's own comment prescribed), and the test inverts rather than
  being deleted. This unblocked 11 skipped models — the whole financial chain.
- Cloud copy: 933,884 rows, 289 MB, **38/38 canvases populated**, and all five
  protected columns verified at 0 through the Supabase API.

**Known open finding:** `assert_billable_charge_grain` fails on 2 charges where a
charge-level calc amount sits on line-grain rows and would double-count. The remedy is
a restructure of a contracted revenue canvas — deliberately left for a decision rather
than changed quietly.

---

## Deploy notes — read before merging

1. **`WAREHOUSE_DATABASE_URL_DEMO25`** must exist on the API service, or the new org
   reports "not configured". Transaction pooler, port **6543**, host **`aws-1`**:
   `postgresql://postgres.hvnfyulgwpjpeeowzuni:<pw>@aws-1-us-east-2.pooler.supabase.com:6543/postgres`

2. **C2 changes behaviour: a client org no longer inherits the shared warehouse URL.**
   Only `dev` may use the unsuffixed `WAREHOUSE_DATABASE_URL`. Any other Postgres-backed
   org needs its own `WAREHOUSE_DATABASE_URL_<ORG>` or it will correctly report itself
   unconfigured. This is the fix, not a regression — but it is the one change that can
   take an org offline on deploy.

3. **H2 changes behaviour the same way for Oracle credentials.** A client with no
   `<ORG>_DB_*` keys no longer falls back to the global `DEMO_DB_*`. Note the live
   `/health` currently reports `configured_organizations: []`, so the deployed
   environment may already be missing per-org Oracle credentials — worth checking
   alongside the new variable.

4. Optional: `OIDC_*` (SSO) and `SMTP_*` (scheduled delivery / alerts) are inert until
   set. `python -m api.report_schedule_runner` wants an hourly cron.

**Verification:** 143 backend tests (14 skipped), 47 frontend tests, `tsc` clean,
brand audit clean across 103 files.
