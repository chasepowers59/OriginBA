---
name: originba-security
description: The OriginBA client-isolation and data-protection model — how one tenant is kept out of another's data, what the SQL fences must block, which columns may never surface, and the checks that enforce it. Load before touching auth, org routing, warehouse selection, the SQL workspace, or the reporting catalog.
---

# Client isolation and data protection

Every client's data lives in a different place and must never meet. This file states
the model, the rules that keep it true, and the audited gaps — so a refactor cannot
quietly undo a control. Audited 2026-09-01: the four CRITICAL findings are fixed
and regression-tested; the HIGH findings below are still live.

## The isolation model in one paragraph

A request carries a JWT whose only trusted claim is `sub`. Role, organization,
permissions and `is_active` are re-read from the auth database on every request
(`api/auth/dependencies.py`), so deactivation and org moves take effect immediately.
The caller's organization decides which database answers the query. Admins — and
only admins — may switch tenants with `X-Organization-Id`; for everyone else the
header is ignored, never rejected, and never used as a connection detail.

**An admin is a PLATFORM admin and has no organization of their own** (settled and
enforced 2026-09-02). There is no per-client admin tier: users, access groups and the
audit log are all filtered by `client_id`, which is ONE value for the whole deployment
(`load_portal_config()["client_id"]`), so an admin bound to a client would have been a
deployment-wide superuser wearing that client's name. `_validate_organization_id` now
refuses the combination on both the create and the promote paths — the promote path
mattered, because the panel's role dropdown sent `{role}` alone and the old client
survived. Adding a real client-admin tier means giving `portal_access_groups` and
`portal_audit_log` an organization first; it is a feature with a schema cost, not a
dropdown. Evidence and reasoning: `tests/test_admin_org_isolation.py`.

## The rules

1. **The org comes from the auth context, never the request.** `require_org_for_data(ctx)`
   is the only legitimate source. No route may read an org/client id from a body,
   and a query-param org (data-source management) must be validated against the
   registry AND refused cross-org.
2. **Every store read AND delete filters on `organization_id`.** `list_all()` exists
   only for the cron runner; a route calling it is a cross-tenant leak.
3. **A missing per-org connection is an ERROR, not a fallback.** Falling back to a
   shared warehouse or a shared credential silently serves tenant A's data to tenant
   B. Enforced in all four places (C2, H2): the warehouse URL, the vault's `_legacy`
   entry, the env credential lookup and the Oracle driver. Sharing is EXPLICIT —
   `SHARED_WAREHOUSE_ORGS`, `SHARED_CREDENTIAL_ORGS`,
   `PORTAL_LEGACY_VAULT_ORGANIZATION` — and defaults to nobody.
4. **Every SQL path gets a fence.** Both engines, every route. A branch that
   validates syntax but skips the scope/secrets fence is an open door. Enforced:
   `_SCOPE_FENCES` in `database_routes` is a TOTAL mapping and an unknown engine is
   refused (C1 fixed) — keep it total when you add an engine.
5. **Secrets never leave the source.** `MICR_ID`, `WEB_PASSWD*`, `ALERT_INFO`,
   `EXT_ACCT_ID` are dropped or collapsed in dbt staging, must not appear in any
   reporting canvas or portal catalog, and must be unselectable in the workspace —
   including via `SELECT *` and whole-row projections (C4 fixed). The same rule is
   enforced in the CATALOG: `is_protected_column()` drops them from
   `allowed_fields()`, so the governed query API and the SQL fence agree (H4 fixed).
6. **Permissions gate every data route.** `ctx.require_permission(...)` or
   `Depends(require_permission(...))`. A route with only `get_auth_context` is
   unprotected. (C3 fixed for `/dq/*`.)
7. **A token is an extra factor, never an alternative to a permission.** (H1 fixed;
   the same shape would be a bug anywhere else it appears.)
8. **Real client data never enters git.** Slice files and `docs/screenshots/` are
   gitignored; no hook enforces it, so `git add -f` is the standing risk.
9. **A secret with a default is a published secret.** `bootstrap_admin_password()`
   defaulted to a literal beside a default admin email, and `.env.example` documented
   that same literal — every deployment that skipped the variable shipped an admin
   login readable in this repo, and `must_change_password` does not save it (the
   intruder authenticates, changes the password, locks the operator out). RAISE, as
   `PORTAL_AUTH_SECRET` does. Fixed 2026-09-02, `tests/test_bootstrap_security.py`.
10. **Pin algorithms by allowlist, not by default.** `jwt_algorithm()` passed straight
   into `decode(algorithms=[...])`, so `PORTAL_AUTH_ALGORITHM=none` would have accepted
   UNSIGNED tokens. Anything outside HS256/384/512 now falls back rather than being
   trusted because it was configured. This file previously claimed it was pinned.
11. **An invariant enforced in the service layer is not enforced.** Bootstrap built the
   `User` model directly, so it created the org-bound admin that
   `_validate_organization_id` forbids. When you add a rule, grep for every writer that
   bypasses the function holding it.

## What the fences must block (test these, not just the happy path)

Postgres: internal schemas qualified AND unqualified (`pg_catalog`, `pg_class`,
`pg_database`), `information_schema`, `dblink`, `pg_read_file`, `lo_import`,
`pg_sleep`, multiple statements, comment-hidden qualifiers, UNION to another schema,
CTEs that hide the real target, and whole-row projection (`row_to_json(t)`,
`to_jsonb(t)`, `t::text`) of any table carrying a secret.

Oracle: `ALL_TABLES`/`DBA_*`/`V$*`/`SYS.*`, other schemas, `@dblink`, `UTL_HTTP`,
`XMLTYPE(t)`, `JSON_OBJECT(*)`. Both Oracle fences block all of these:
`validate_oracle_reporting_scope` (in-database, CISADM + ORIGINBA_REPORTING) and
`validate_oracle_cisadm_scope` (legacy, CISADM only).

## An authorization check that resolved against the WRONG CATALOG (2026-09-02)

Fixed, and worth carrying as a shape rather than an incident, because the isolation
model has two catalogs behind it and only one is the development default.

`snapshot_workstream()` called `get_snapshot()` with **no organization_id**, and
`catalog_name_for_org(None)` returns `"dbt"`. So every workstream authorization lookup
resolved against the dbt catalog whichever org the caller was in. The two shapes share
no snapshot ids (`rpt_financial_txn` against `FT_RPT_CURR`), so on the **six legacy
orgs** the lookup missed, returned `""`, and `workstreams_allowed(["finance"], "")` is
False. A user granted `finance` was refused `FT_RPT_CURR` — which declares
`workstream: finance` — and through `filter_nlq_metrics_for_auth` /
`filter_dashboard_for_auth` their metrics and tiles filtered to **empty in silence**,
reading as a broken portal rather than a denial.

It failed CLOSED — a lockout, not a leak. What kept it invisible is the part to
remember: the dev org is a dbt org, and **`"*"` and an empty grant both mean full
access and never reach the workstream comparison at all**, so the two configurations
we develop against cannot see it. When auditing an authz path here, exercise it with a
RESTRICTED grant on a LEGACY org; a full-grant pass proves nothing.

**The obvious mock hides it.** My first test patched `catalog_name_for_org` and PASSED
against the broken code, because that patch answers `"cisadm"` for the
`organization_id=None` call too — silently supplying the argument whose absence is the
entire defect. Patch the org REGISTRY (`api.organizations.get_organization`) instead,
so `catalog_name_for_org(None)` still answers `"dbt"` as in production. See
`tests/test_snapshot_access_by_shape.py`; neither `assert_snapshot_access` nor
`assert_workstream_access` was named in ANY test before it.

## Audited findings (2026-09-01)

**CRITICAL — all four FIXED the same day**, each test-first:
- **C1** every engine now maps to a fence (`_SCOPE_FENCES` is total; unknown engine
  is refused). The legacy `oracle` path uses `validate_oracle_cisadm_scope`.
- **C2** `warehouse_url()` returns None for Oracle orgs, unknown orgs and clients
  with no key of their own; only `dev` may use the shared URL; no hardcoded default;
  `_pool` raises rather than letting psycopg2 guess.
- **C3** `/dq/*` requires `portal:read` and scopes with `require_org_for_data`; no
  shared ack bucket.
- **C4** the secrets guard is per TABLE — `SELECT *` and whole-row projection are
  both blocked on every table carrying a protected column.

**HIGH — H1, H2, H4 and H5 also FIXED:**
- **H1** `data_source:manage` is required unconditionally; the settings token is a
  second factor, never an alternative. The connection test returns a generic failure
  so it cannot be used to probe the internal network.
- **H2** no credential inherits across tenants: the vault's `_legacy` entry belongs to
  one org named by `PORTAL_LEGACY_VAULT_ORGANIZATION` (unset = nobody), the global
  DEMO_*/DB_USER keys serve only `SHARED_CREDENTIAL_ORGS` (`{demo}`), and the driver
  raises for a client with no keys of its own.
- **H4** `is_protected_column()` drops secrets at `allowed_fields()`, so the governed
  query API refuses them whatever a catalog says; the catalog and its generator are
  clean too.
- **H5** `sample-rows` and `raw-sql` audit what they actually ran (they used to 500
  after the query and skip the audit write).

**STILL OPEN — HIGH:** H3 `raw_sql_validator` scopes by substring presence (admin-only);
H6 the JWT is in a non-HttpOnly cookie for 8 hours.
**MEDIUM/LOW:** see the audit document.

Full evidence: `docs/SECURITY_AUDIT_2026-09-01.md`.

## What genuinely holds (do not re-fix)

Tenant override is admin-only and registry-validated · no route takes an org from a
body · token claims are not trusted · JWT algorithm pinned, secret >=32 chars ·
PBKDF2-SHA256 260k + login rate limiting · OIDC state signed, id_token verified with
audience+issuer, SSO cannot mint an admin · the governed query builder binds every
value and allow-lists every identifier · store-layer org filtering is complete on
reads and deletes · connection pools keyed by resolved URL/DSN with transaction-scoped
schema pinning · dbt staging genuinely drops the four secret columns · nothing
sensitive has ever been committed.

## Enforcement gaps to close when you touch this area

- ~~`_resolve_active_organization` has ZERO tests~~ — CLOSED 2026-09-02 in
  `tests/test_admin_org_isolation.py`. The control itself was already correct: a
  non-admin's header is ignored rather than rejected, an unregistered value is
  discarded, and an unknown role cannot switch. It had no coverage, not a defect.
- No HTTP-layer cross-org test exists for any resource; the `*_org_scoped` tests
  prove the store filters, not that the route passes the caller's real org.
- The fence tests now cover C1 and C4, and assert the engine→fence routing. Still
  uncovered: unqualified `pg_catalog` names (M1) and `dblink`/`pg_read_file` (M2).
- `api-ci.yml` path filters exclude `scripts/`, `output/` and `apps/`, so a catalog
  regeneration that reintroduces a secret column runs no security test.
- No pre-commit hook or git hook exists in either repo.

**When you fix one of these, write the test FIRST (repo rule), and add the bypass to
`tests/test_scope_fence_security.py` so it can never come back.**
