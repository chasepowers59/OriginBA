# Client-isolation and security audit — 2026-09-01

Read-only audit of `OriginBA-3` (API + portal) and `originba_dbt` (reporting layer).
The fence bypasses below were **executed against the validator code**, not reasoned
about. Nothing was modified during the audit.

Standing rules and the isolation model: `.claude/skills/originba-security/SKILL.md`.

---

## CRITICAL

### C1 — The SQL workspace has no fence on the legacy Oracle engine
`api/database_routes.py:112-118`. `_validate()` runs the syntax check, then applies a
scope fence **only** for `postgres` and `oracle_dbt`. Engine `oracle` — any org whose
catalog is not `dbt` — falls through with no schema fence, no dictionary/dblink fence
and **no secrets guard** (`_enforce_secrets` is only reachable from `_enforce_scope`,
`sql_workspace_validator.py:170`).

`database:sql` is held by role `user`, the lowest role (`api/auth/permissions.py:25`).
Per `config/portal_organizations.json`, six of eight orgs are on that engine: `demo`,
`citycorp`, `odessa`, `fond_du_lac`, `college_station`, `newark`.

Executed against the live validator — all ALLOWED on that path:

```
SELECT micr_id FROM cisadm.ci_pay_tndr
SELECT username FROM dba_users
SELECT sid FROM v$session
SELECT * FROM sys.user$
SELECT * FROM cisadm.ci_acct@remote
SELECT utl_http.request('http://…') FROM dual
SELECT * FROM scott.emp
```

**Impact:** any user at those six clients can read bank routing numbers, web
passwords and the data dictionary, and make outbound HTTP from the database host.
**Fix:** route the `oracle` branch through `validate_oracle_reporting_scope`, which
already blocks every one of the above.

### C2 — Every organization falls back to one shared warehouse
`api/warehouse_db.py:50-55`. `warehouse_url()` returns `WAREHOUSE_DATABASE_URL_<ORG>`,
else the global `WAREHOUSE_DATABASE_URL`, else a hardcoded `DEFAULT_URL` (`:29`).
`warehouse_configured()` therefore returns True for every input, so
`require_org_for_data` can never refuse a misconfigured org. Executed:

```
citycorp        configured=True  url=…/originba_training
ellensburg      configured=True  url=…/originba_training
nonexistent_org configured=True  url=…/originba_training
None            configured=True  url=…/originba_training
```

`render.yaml:26` sets only the global key — no per-org URLs — so this is the shipped
configuration. A second live path proves it end to end:
`api/executive_dashboard.py:199-220` runs `_refresh_insight()` through the warehouse
for any org including Oracle ones, reporting another tenant's row counts.
**Fix:** `warehouse_url(org)` must raise when no per-org URL exists; drop
`DEFAULT_URL` and the unsuffixed fallback for every org except `dev`.

### C3 — `/dq/*` is unpermissioned and reaches the shared warehouse
`api/dq_routes.py:80-90` (also `:154`, `:170`). `dq_findings` has **no**
`require_permission` call, uses `ctx.organization_id` rather than the effective org,
and calls `warehouse_connection(org)`. A user with no org gets `org=None` → the global
warehouse plus a shared `data/dq_acks/default.json`. An Oracle-backed org has no
Postgres warehouse, so its DQ findings — row-level account and premise identifiers —
come from whatever the global URL points at, i.e. another tenant.
**Fix:** `ctx.require_permission("portal:read")` + `require_org_for_data(ctx)`, and
return `configured: False` when the org's engine is not postgres.

### C4 — The secrets guard is defeated by whole-row projection
`api/sql_workspace_validator.py:111-129` blocks the column *names* and blocks `*` on
`CI_PAY_TNDR`. It does not block projecting the row as a value. Executed — ALLOWED on
the Postgres path, each returning `MICR_ID` verbatim:

```
SELECT row_to_json(t) FROM cisadm.ci_pay_tndr t
SELECT to_jsonb(t)    FROM cisadm.ci_pay_tndr t
SELECT t::text        FROM cisadm.ci_pay_tndr t
```

Quoting and case ARE caught. Separately the star rule names only `ci_pay_tndr`, so
`SELECT * FROM cisadm.ci_per` (`web_passwd`, `web_passwd_ans`) and
`SELECT * FROM cisadm.ci_acct` (`alert_info`) are allowed.
**Fix:** extend the star rule to `ci_per`, `ci_acct`, `ci_acct_apay`; reject
whole-row composites over secret-bearing tables. The durable fix is a database grant
with column-level SELECT that excludes those columns.

---

## HIGH

| # | Finding | Evidence |
| --- | --- | --- |
| H1 | `verify_settings_token()` returns **True when `PORTAL_SETTINGS_TOKEN` is unset** (the default), and `_require_data_source_manage` accepts it *instead of* the permission — so any `user` can repoint their org's database, and `POST /portal/data-source/test` with an arbitrary DSN is a blind internal-network prober from the API host. | `data_source_store.py:273-277`, `data_source_routes.py:44-52,124` |
| H2 | `load_config(org)` falls back to a `_legacy` single-org payload for any org with no vault entry, routing org A's queries to whatever DB that names. Same shape for global credential fallbacks. | `data_source_store.py:183-188`, `organizations.py:104-109`, `demo_db.py:52-62` |
| H3 | `snapshots:raw_sql` scopes by *substring presence* of the allowed table — a comment mentioning it suffices. Executed: MICR read via subquery, UNION, `DBA_USERS`, and `@dblink` all allowed. Admin-only and currently unreachable (H5), hence HIGH. | `raw_sql_validator.py:35` |
| H4 | `ALERT_INFO` is a governed `role: dimension` in the cisadm catalog, so `POST /snapshots/…/query` returns it for any `user` — while the SQL workspace explicitly fences the same column. The two policies disagree. | `output/catalog_cisadm.json`, `query_builder.py:109` |
| H5 | `snapshot_sample_rows` and `snapshot_raw_sql` reference a `body` that does not exist in their signature → the query runs, the caller gets a 500, and the audit event is never written. | `snapshot_explorer.py:411-412,494-495` |
| H6 | The JWT is written to a **non-HttpOnly** cookie alongside sessionStorage, valid for the full 8-hour token life with no revocation. The only consumer is the SSR path, which reads it server-side and would work with HttpOnly. | `apps/analytics-portal/src/lib/auth.ts:53-66` |

---

## MEDIUM

- **M1** Unqualified `pg_catalog` names (`pg_class`, `pg_database`, `pg_stat_activity`,
  `pg_user`, `pg_roles`, `pg_settings`) are allowed; only the qualified form is
  blocked. `pg_database` enumerates other clients' database names.
- **M2** `dblink`, `dblink_connect`, `pg_read_file`, `lo_import`, `pg_sleep` are all
  allowed — the Postgres fence has no function deny-list where the Oracle one does.
- **M3** `/health` discloses the full client roster unauthenticated, because
  `ENVIRONMENT` is set in no deployment file so `is_production()` is always False.
- **M4** The audit log has no tenant dimension — rows carry a process-wide
  `client_id`, so an admin's action in one tenant is indistinguishable from another.
- **M5** Workstream RBAC calls `get_snapshot()` without an org, always hitting the
  dbt catalog; for a cisadm org every lookup misses and restricted users are denied
  everything. Fails closed, but is not evaluating the right data.
- **M6** Scheduled reports and KPI alerts validate recipient *shape* only — a report
  CSV can be mailed to any external address on a cadence.
- **M7** `PORTAL_AUTH_DISABLED` yields a full admin with tenant switching and a
  literal dev JWT secret; nothing checks `is_production()` on that path.
- **M8** The dbt secrets test is name-based (`%micr%`, `%passwd%`…), so a Title-Case
  rename would pass it; its `depends_on` omits `stg_account` and `stg_person_contact`.
  Today's catalogs are clean.
- **M9** CORS uses `allow_credentials=True` with an env-extensible origin list;
  `PORTAL_CORS_ORIGINS=*` would echo any origin with credentials.

## LOW

L1 CLAUDE.md claims `git push` is in the settings deny list — it is not.
L2 Committed local-fixture password literals (no client credentials).
L3 The real client slice sits untracked on disk with live secrets; gitignored, but no
pre-commit or git hook exists, so `git add -f` bypasses the only barrier.
L4 `ui/chart.tsx` interpolates chart config colors into CSS via
`dangerouslySetInnerHTML` (stock shadcn) — safe while configs are constants.
L5 No CSP, HSTS or `X-Frame-Options`.
L6 `ci/jrxml-smoke.yml` sits outside `.github/workflows/` and never runs.

---

## Already solid — do not re-fix

Tenant override is admin-only, registry-validated and never used as a connection
detail · no route takes an org id from a request body · token claims are not trusted
(role/org/permissions re-read per request) · JWT algorithm pinned, secret >=32 chars
· PBKDF2-SHA256 260k iterations with login rate limiting · OIDC state signed and TTL
bounded, id_token verified RS256 against JWKS with audience+issuer, SSO cannot mint
an admin, token returned in the URL fragment · the governed query builder binds every
value and allow-lists every identifier · store-layer org filtering is complete on
reads AND deletes, with uuid4 ids so an upsert cannot hijack another org's row ·
connection pools keyed by resolved URL/DSN with transaction-scoped schema pinning ·
dbt staging genuinely drops `micr_id`, `alert_info`, the `CI_PER` credentials and
`ext_acct_id` · nothing sensitive has ever been committed (history scanned).

## Gaps in enforcement

1. `_resolve_active_organization` — the most isolation-critical function — has **zero
   tests**; no test anywhere sends `X-Organization-Id`.
2. No HTTP-layer cross-org test exists for any resource. The `*_org_scoped` tests
   prove the store filters when handed an org id, not that the route passes the
   caller's real one. `saved_dashboards.py` and `dq_routes.py` have no test file.
3. The fence tests cover none of the bypasses that actually work (C1, C4, M1, M2),
   and never assert the engine→validator routing where C1 lives.
4. `deploy.yml` selects the dbt secrets test only when one of its five ref'd models
   changed; the all-clients override does not include it.
5. `api-ci.yml` path filters exclude `scripts/`, `deploy/`, `apps/`, `output/` — a
   catalog regeneration that reintroduces a secret column runs no security test.
6. Every `originba_dbt/scripts/audit_*.py` is hand-run; CI invokes none of them, and
   **no script in either repo performs a secrets/PII scan**.
7. No pre-commit config and no git hooks in either repo.
8. Until this audit, no security or isolation skill existed in either repo.

## Not verified

Whether `dblink`/`postgres_fdw` are installed in the client warehouses, and what
grants the warehouse and Oracle connection roles actually hold. Those determine the
real blast radius of C1, C4, M1 and M2 — the validators are the only barrier that
could be measured. **A workspace role holding column-restricted SELECT on
`cisadm`+`reporting` would neutralise most of the CRITICAL findings independently of
the regex layer, and is worth confirming first.**
