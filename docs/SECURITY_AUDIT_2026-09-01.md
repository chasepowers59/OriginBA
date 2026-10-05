# Client-isolation and security audit — 2026-09-01

Read-only audit of `OriginBA-3` (API + portal) and `originba_dbt` (reporting layer).
The fence bypasses below were **executed against the validator code**, not reasoned
about. Nothing was modified during the audit.

Standing rules and the isolation model: `.claude/skills/originba-security/SKILL.md`.

---

## CRITICAL — all four FIXED 2026-09-01

Fixed the same day, each with the failing test written first. Evidence below is
kept as written so the regression tests can be traced back to the attack.

| # | Fix | Test |
| --- | --- | --- |
| C1 | `_SCOPE_FENCES` is now a TOTAL mapping engine→fence in `database_routes`; an unknown engine is refused, not waved through. The legacy path gets `validate_oracle_cisadm_scope` (CISADM only, same Oracle escape-hatch and secrets guards). | `LegacyOracleEngineFenceTests` — every engine fences, the eight audited bypasses blocked, legacy `*_RPT_CURR` still served |
| C2 | `warehouse_url()` returns **None** for an Oracle-backed org, an unknown org, and any client without its own key; `SHARED_WAREHOUSE_ORGS` is `{dev}`; `DEFAULT_URL` deleted; `_pool` raises rather than letting psycopg2 fall back to libpq defaults. | `tests/test_warehouse_isolation.py` (7) |
| C3 | All three `/dq/*` routes now `require_permission("portal:read")` and scope with `require_org_for_data`; the shared `default.json` ack bucket is gone. | `tests/test_dq_route_scoping.py` (4) |
| C4 | The secrets guard is per TABLE, not per name: `SELECT *` blocked on `ci_pay_tndr`, `ci_per`, `ci_acct`, `ci_acct_apay`, and whole-row projection (`row_to_json(t)`, `to_jsonb(t)`, `t::text`, `CAST(t AS text)`) blocked when the alias resolves to one of them. | `SecretsProjectionTests` (4) |

Verified live against the running API after the fix:
`SELECT micr_id FROM cisadm.ci_pay_tndr` → 400 · `SELECT row_to_json(t) FROM
cisadm.ci_pay_tndr t` → 400 · `SELECT * FROM cisadm.ci_per` → 400 ·
`SELECT 1 AS n FROM cisadm.ci_acct` → 200.

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

## HIGH — ALL SIX FIXED (H1, H2, H4, H5 on 2026-09-01; H3 and H6 verified
## fixed 2026-09-02 — H3 blocks all six attacks the finding named, H6 stores the
## token HttpOnly via a same-origin route)

| # | Fix | Test |
| --- | --- | --- |
| H1 | `_require_data_source_manage` now requires `data_source:manage` UNCONDITIONALLY; the settings token is a second factor layered on top, never an alternative. The connection test no longer returns the driver error (it distinguished "no listener" from "wrong password" from "no route" — a network probe); the detail goes to the server log. Dead `_require_settings_token` helper deleted. | `tests/test_data_source_authz.py` (6) |
| H4 | `snapshot_catalog.is_protected_column` drops MICR/WEB_PASSWD/ALERT_INFO/EXT_ACCT_ID from `allowed_fields()`, so the governed query API refuses them whatever a catalog declares; the two `*ALERT_INFO` fields were removed from `output/catalog_cisadm.json`; and the catalog generator skips them so regeneration cannot reintroduce them. Legitimate alert columns (ALERT_COUNT, OPEN_ALERT_COUNT, LATEST_ALERT_*) are untouched. | `tests/test_catalog_secrets.py` (5) |

| H2 | The three credential fallbacks are gone. The vault's `_legacy` entry now belongs to exactly one org named by `PORTAL_LEGACY_VAULT_ORGANIZATION` (unset = nobody); the global DEMO_*/DB_USER keys serve only `SHARED_CREDENTIAL_ORGS` (`{demo}`); and `demo_db.env_connection_config` raises for a client whose own keys are missing instead of reaching for the shared ones. | `tests/test_credential_isolation.py` (8) |
| H5 | Both routes now audit what they actually ran: `sample-rows` records a preview, `raw-sql` records `raw_sql_run` with the statement. (This one was self-inflicted — the access-audit sweep pasted the query route's detail block into two routes that have no `body`.) | `tests/test_access_audit.py` (8) |

Verified: `build_query(dimensions=['ALERT_INFO'])` on the real cisadm snapshot →
`Invalid dimension: ALERT_INFO`, with the five legitimate alert columns still allowed.
Every real client org still resolves its OWN credentials (checked across all eight);
an unknown org resolves none. `sample-rows` returns 200 and writes its audit row.

### As found (all six fixed above; kept as the original evidence)

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

- **M1 FIXED** Unqualified `pg_catalog` names (`pg_class`, `pg_database`,
  `pg_stat_activity`, `pg_user`, `pg_roles`, `pg_settings`) were allowed; only the
  qualified form was blocked. `_PG_CATALOG_OBJECT` now matches the bare names too,
  bounded on both sides so a column like "Page Count" cannot trip it.
- **M2 FIXED** `dblink`, `dblink_connect`, `pg_read_file`, `lo_import`, `pg_sleep` were
  all allowed — the Postgres fence had no function deny-list where the Oracle one does.
  `_PG_DANGEROUS_FUNCTION` now covers remote links, file reads, large-object import,
  sleeps and backend control.
- **M3 FIXED 2026-09-02** `/health` disclosed the full client roster unauthenticated,
  because `ENVIRONMENT` is set in no deployment file so `is_production()` is always
  False. The fix is the DIRECTION of the default, not another platform name: detail now
  requires `is_development()`, affirmative proof, so an unrecognised environment
  discloses nothing. `tests/test_auth_config_and_catalog.py`.
- **M4** The audit log has no tenant dimension — rows carry a process-wide
  `client_id`, so an admin's action in one tenant is indistinguishable from another.
- **M5 FIXED 2026-09-02** Workstream RBAC called `get_snapshot()` without an org,
  always hitting the dbt catalog; for a cisadm org every lookup missed and restricted
  users were denied everything, their own grants included. `snapshot_workstream()` now
  takes the caller's `effective_organization_id()`.
  `tests/test_snapshot_access_by_shape.py` — note in there: patching
  `catalog_name_for_org` makes the test pass against the BROKEN code, because it also
  answers the `organization_id=None` call.
- **M6 CONTROL ADDED 2026-09-02, still requires configuring** Scheduled reports and
  KPI alerts validate recipient *shape* only — a report CSV can be mailed to any
  external address on a cadence. `PORTAL_ALLOWED_RECIPIENT_DOMAINS` now enforces an
  allow-list (exact domain, so `origin.local` cannot admit
  `origin.local.attacker.example`) and is INERT until an operator sets it. Setting it
  per deployment is the remaining work.
- **M7 FIXED 2026-09-02** `PORTAL_AUTH_DISABLED` yielded a full admin with tenant
  switching and a literal dev JWT secret, and nothing checked where it was running.
  `auth_disabled()` now requires `is_development()` — affirmative proof, not the
  absence of proof of production, because `is_production()` is False for an
  unrecognised environment and Render sets none of the markers. `ENVIRONMENT` is
  documented in `deploy/api.env.example`; `tests/conftest.py` declares the suite.
- **M8** The dbt secrets test is name-based (`%micr%`, `%passwd%`…), so a Title-Case
  rename would pass it; its `depends_on` omits `stg_account` and `stg_person_contact`.
  Today's catalogs are clean.
- **M9 FIXED 2026-09-02** CORS uses `allow_credentials=True` with an env-extensible
  origin list, and `PORTAL_CORS_ORIGINS=*` would echo any origin with credentials.
  A wildcard is now DROPPED rather than honoured, and entries must look like an origin
  (`scheme://host[:port]`). `tests/test_open_access_and_cors.py`.

## LOW

L1 **CORRECTED 2026-09-02** CLAUDE.md claimed `git push` was in the settings deny list;
it is not (the list denies curl/wget/nc/scp/rsync only). The doc now states it as a
RULE rather than an enforced deny, and names the entry to add if enforcement is
wanted. The behaviour was already correct — push commands are handed to the user —
but the file asserted a guard that does not exist.
L2 Committed local-fixture password literals (no client credentials).
L3 The real client slice sits untracked on disk with live secrets; gitignored, but no
pre-commit or git hook exists, so `git add -f` bypasses the only barrier.
L4 `ui/chart.tsx` interpolates chart config colors into CSS via
`dangerouslySetInnerHTML` (stock shadcn) — safe while configs are constants.
L5 No CSP, HSTS or `X-Frame-Options`.
L6 **ANSWERED 2026-09-02** `ci/jrxml-smoke.yml` sits outside `.github/workflows/` and
never runs — deliberately. It needs ORACLE_DSN and JRS_URL inside a private VCN, which
a GitHub-hosted runner cannot reach, so activating it would redden CI on every .jrxml
or .sql push without gaining coverage. The reason and the activation path (a
self-hosted runner in the VCN) are now documented in the file itself.

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

---

## Production-readiness round — 2026-10-05

A read-only audit of production hardening (headers, sign-in, sessions, errors, logging,
embeds, uploads), the HTTP isolation harness widened to every stored object, and a walk of
the portal with sign-in ON as a reader and an editor. Branch `portal/round-10`.

### Fixed, each with its test

| Finding | Fix | Pinned by |
| --- | --- | --- |
| A route could ship without any permission check; rule 6 was enforced route by route | The app's own route table is walked: every route is PUBLIC with its reason, SESSION_ONLY, or authenticated AND gated; no route takes an organization from the request; a planted unguarded route proves the check bites | `tests/test_route_guards.py` |
| Isolation was proven for saved views only | Dashboards, notes, alerts, schedules (and run-now), embed links, letter runs, content packs and the admin surfaces, tried by CityCorp users with the organization header forged to Ellensburg: 67 of 67 held | `scripts/check_tenant_isolation.py` |
| Driver and mail-server text reached users on nine routes (the SQL workspace for every role; the data-source save path, the H1 leak back on a second path) | `api/public_errors.py`: a connection failure reads as the unreachable note with the request's reference; any other message keeps its first line with hosts, addresses and connection strings removed; a static rule refuses any broad `except` that returns raw exception text | `tests/test_public_errors.py` |
| Tests could resolve real client credentials (the app loaded `.env` on import; the lookup falls back to the process environment); a failing assertion printed CityCorp's TEST credentials into a local session log | No `.env` under `ENVIRONMENT=test`; conftest strips secret-shaped keys; the credential test isolates the environment and asserts without printing. The printed value went to no file, commit or push; rotating that TEST password is the owner's call | `tests/test_credential_isolation.py`, `tests/conftest.py` |
| Sign-in timing listed accounts (an unknown email skipped PBKDF2) | A dummy check does the same work | `tests/test_auth_hardening.py` |
| A token outlived a password change | Tokens carry a fingerprint of the password hash, checked on every request; a change or an admin reset retires older tokens; change-password returns a fresh token | `tests/test_auth_hardening.py`, harness |
| A token's `typ` was never checked | Only `typ: access` opens a session (the embed secret is shared) | `tests/test_auth_hardening.py` |
| Change-password had no attempt limit | Limited like sign-in | `tests/test_auth_hardening.py` |
| Sign-ins were not audited | `login` and `login_failed` (with IP) in the audit trail; the failure row commits before the 401 | `tests/test_auth_hardening.py`, harness |
| No security headers on the API; docs and schema public; localhost:3000 always an allowed origin | nosniff, deny framing, no-referrer, deny-all CSP, HSTS outside development; docs only in development; localhost origins only in development | `tests/test_production_headers.py` |
| The app set only frame headers | nosniff, Referrer-Policy, Permissions-Policy, HSTS on every page; CSP adds base-uri, object-src, form-action; `poweredByHeader: false` | `src/lib/publicPaths.test.ts` |
| An expired session left every panel reading "Invalid or expired token" | A 401 (with a session, on a page that needs one) returns to sign-in with `next` and a "session ended" note | `src/lib/sessionExpiry.test.ts` |
| Open redirect after sign-in (`?next=` used as given) | `lib/safeNext`, same-site paths only (round 9) | `src/lib/safeNext.test.ts` |
| A page the menu hides rendered when its address was typed | The shell applies the navigation's rule to the page itself | `src/lib/pageAccess.test.tsx` |
| No root-layout error screen | `src/app/global-error.tsx` | — |

### Remaining, in order of risk (not done in this round, with the reason)

Items 4 to 8 of the original list were closed on 2026-10-05 in round 11 (next section). Still open:

1. **Login and route rate limits are per process and keyed on the proxy's address.** Needs a shared store (the state Postgres) and the deployment's trusted-proxy setting (`--forwarded-allow-ips`), both deployment decisions.
2. **No `script-src` CSP.** A nonce-based policy needs the color-mode inline script and Next's own scripts nonced; worth doing deliberately with a full regression, not inside a round.
3. **Session token in sessionStorage** (readable by script) alongside the HttpOnly copy. Moving the browser to cookie-only auth changes every request path.
4. **No breached-password check** (the policy refuses a short list of common passwords offline); Ori's spend caps are opt-in.

## Round 11 — 2026-10-05: the ledger items that needed no deployment decision

| Was | Now | Proof |
| --- | --- | --- |
| Sign-out cleared only the browser; a copied token kept the session until it expired | Tokens carry an id; `POST /auth/logout` records it (`portal_revoked_tokens`, pruned at expiry) and it never opens a session again. Other sessions continue. The app calls it before clearing the browser | `tests/test_sessions_and_passwords.py`, `src/lib/logout.test.ts`, harness; live: the old token answers "You signed out of this session" |
| New passwords needed 8 characters; PBKDF2 at 260k | 12 characters, not the email, not a common one, wherever a password is SET (change, admin create, admin reset); 600k iterations, older hashes upgraded at sign-in | `tests/test_sessions_and_passwords.py`, harness |
| Embed links could not be withdrawn and were signed with the session secret | `embed_key()` (own secret or derived, never the session one); every link recorded per organization and served only while its record stands; the owner or an admin lists and turns off links in the embed dialog | `tests/test_embed.py`, harness (CityCorp cannot list or turn off an Ellensburg link, header forged); live |
| No request size cap | `BodySizeLimit` 2 MB (`PORTAL_MAX_BODY_BYTES`), declared or chunked, 413 before any route runs | `tests/test_request_limits.py` |
| No rate limits on the SQL workspace, explorer queries, Ori, PDF exports, the public embed route | Per-person sliding windows (per address on the embed route), 429 with a sentence and Retry-After; a test fails if one of those routes loses its limit | `tests/test_request_limits.py` |
| Exports were not audited | PDFs recorded by the API; CSV and Excel reported by the browser's download helpers; action `export` under the organization being viewed | `tests/test_export_audit.py`; live |
| Audit rows kept SQL literals (customer names, account numbers) | `sql_for_audit` keeps the statement's shape, values as ? | `tests/test_audit_hygiene.py` |
| The request log's org= was the header as sent | The organization actually served | `tests/test_audit_hygiene.py` |
| The route-guard test saw only /health under FastAPI 0.140+ (lazy included routers), so it passed without checking | The walk follows included routers on both versions; a floor test stops an empty walk passing | `tests/test_route_guards.py` |
