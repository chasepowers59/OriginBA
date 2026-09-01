---
name: originba-security
description: The OriginBA client-isolation and data-protection model — how one tenant is kept out of another's data, what the SQL fences must block, which columns may never surface, and the checks that enforce it. Load before touching auth, org routing, warehouse selection, the SQL workspace, or the reporting catalog.
---

# Client isolation and data protection

Every client's data lives in a different place and must never meet. This file states
the model, the rules that keep it true, and the audited gaps — so a refactor cannot
quietly undo a control. Audited 2026-09-01; findings marked OPEN are live.

## The isolation model in one paragraph

A request carries a JWT whose only trusted claim is `sub`. Role, organization,
permissions and `is_active` are re-read from the auth database on every request
(`api/auth/dependencies.py`), so deactivation and org moves take effect immediately.
The caller's organization decides which database answers the query. Admins — and
only admins — may switch tenants with `X-Organization-Id`; for everyone else the
header is ignored, never rejected, and never used as a connection detail.

## The rules

1. **The org comes from the auth context, never the request.** `require_org_for_data(ctx)`
   is the only legitimate source. No route may read an org/client id from a body,
   and a query-param org (data-source management) must be validated against the
   registry AND refused cross-org.
2. **Every store read AND delete filters on `organization_id`.** `list_all()` exists
   only for the cron runner; a route calling it is a cross-tenant leak.
3. **A missing per-org connection is an ERROR, not a fallback.** Falling back to a
   shared warehouse or a `_legacy` credential silently serves tenant A's data to
   tenant B. (OPEN: C2/H2 below.)
4. **Every SQL path gets a fence.** Both engines, every route. A branch that
   validates syntax but skips the scope/secrets fence is an open door. (OPEN: C1.)
5. **Secrets never leave the source.** `MICR_ID`, `WEB_PASSWD*`, `ALERT_INFO`,
   `EXT_ACCT_ID` are dropped or collapsed in dbt staging, must not appear in any
   reporting canvas or portal catalog, and must be unselectable in the workspace —
   including via `SELECT *` and whole-row projections. (OPEN: C4/H4.)
6. **Permissions gate every data route.** `ctx.require_permission(...)` or
   `Depends(require_permission(...))`. A route with only `get_auth_context` is
   unprotected. (OPEN: C3.)
7. **A token is an extra factor, never an alternative to a permission.** (OPEN: H1.)
8. **Real client data never enters git.** Slice files and `docs/screenshots/` are
   gitignored; no hook enforces it, so `git add -f` is the standing risk.

## What the fences must block (test these, not just the happy path)

Postgres: internal schemas qualified AND unqualified (`pg_catalog`, `pg_class`,
`pg_database`), `information_schema`, `dblink`, `pg_read_file`, `lo_import`,
`pg_sleep`, multiple statements, comment-hidden qualifiers, UNION to another schema,
CTEs that hide the real target, and whole-row projection (`row_to_json(t)`,
`to_jsonb(t)`, `t::text`) of any table carrying a secret.

Oracle: `ALL_TABLES`/`DBA_*`/`V$*`/`SYS.*`, other schemas, `@dblink`, `UTL_HTTP`,
`XMLTYPE(t)`, `JSON_OBJECT(*)`. The `oracle_dbt` fence blocks all of these today —
the legacy `oracle` path does not (C1).

## Audited findings still OPEN (2026-09-01)

CRITICAL
- **C1** `database_routes._validate` applies a fence only for `postgres` and
  `oracle_dbt`; engine `oracle` (6 of 8 orgs, permission held by role `user`) gets
  none — MICR, `DBA_USERS`, `V$SESSION`, dblink and `UTL_HTTP` are all reachable.
- **C2** `warehouse_db.warehouse_url()` falls back to a global URL and a hardcoded
  default, so `warehouse_configured()` is always True and every org resolves to one
  shared database. `render.yaml` sets only the global key.
- **C3** `/dq/*` has no permission check, uses the home org instead of the effective
  one, and reaches that shared warehouse.
- **C4** The secrets guard blocks column NAMES but not whole-row projection, and its
  `SELECT *` rule names only `ci_pay_tndr` (not `ci_per`, `ci_acct`).

HIGH — H1 settings-token bypass on data-source management (also a blind internal
port scanner); H2 `_legacy` credential fallback; H3 `raw_sql_validator` scopes by
substring presence; H4 `ALERT_INFO` is a queryable dimension in the cisadm catalog;
H5 two routes 500 after querying and skip their audit write; H6 the JWT is in a
non-HttpOnly cookie for 8 hours.

Full evidence, MEDIUM/LOW findings and the "already solid" list:
`docs/SECURITY_AUDIT_2026-09-01.md`.

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

- `_resolve_active_organization` — the most isolation-critical function — has ZERO
  tests. No test anywhere sends `X-Organization-Id`.
- No HTTP-layer cross-org test exists for any resource; the `*_org_scoped` tests
  prove the store filters, not that the route passes the caller's real org.
- The fence tests miss every bypass that actually works (C1, C4, unqualified
  `pg_catalog`, `dblink`).
- `api-ci.yml` path filters exclude `scripts/`, `output/` and `apps/`, so a catalog
  regeneration that reintroduces a secret column runs no security test.
- No pre-commit hook or git hook exists in either repo.

**When you fix one of these, write the test FIRST (repo rule), and add the bypass to
`tests/test_scope_fence_security.py` so it can never come back.**
