# OriginBA portal — deployment (Vercel frontend + container API + Supabase)

The portal is two deployables plus a shared database. Vercel hosts the Next.js
**frontend**; the FastAPI **API** runs as a container (it holds DB connection pools
and, for Oracle orgs, needs Instant Client — neither fits Vercel serverless);
**Supabase** (Postgres) is the shared store for logins and user state.

```
  Browser ──> Vercel (Next.js)  ──HTTPS──>  API container (FastAPI)
                                              ├─ Supabase Postgres  (auth + saved views/dashboards)
                                              ├─ per-client dbt warehouse (Postgres)  ─ the `dev` org is local
                                              └─ per-client C2M Oracle (oracle / oracle_dbt orgs, in-VCN)
```

## One-time setup

### 1. Supabase (login + user-state DB) — PROVISIONED
- Project `psnkxsjpuxgvvjvyenfj` (region us-east-2) is live and the state schema
  `portal_state.records` is **already applied** (deploy/supabase/001_init.sql).
- The API reads/writes it through `PORTAL_AUTH_DATABASE_URL` (or a separate
  `PORTAL_STATE_DATABASE_URL`). Copy the project's **pooled** connection string
  (Dashboard → Connect → port 6543) into the API host env — this is the one secret
  only the owner can supply.
- The **auth tables create themselves** on first API boot (SQLAlchemy) against the
  same URL — no migration needed.
- **RLS advisory:** `portal_state.records` has row-level security disabled. That is
  safe as built — the API reaches it over a direct Postgres connection (which
  bypasses RLS) and the schema is NOT in Supabase's PostgREST-exposed set, so the
  browser/anon key cannot touch it. If you ever expose it to Supabase client
  libraries, enable RLS first: `ALTER TABLE portal_state.records ENABLE ROW LEVEL
  SECURITY;` plus an org-scoped policy.

### 2. API container (Fly.io / Render / Railway / OKE)
- Build `deploy/Dockerfile.api` (Postgres-serving base). For Oracle orgs, rebuild
  FROM an Instant Client base and add `oracledb` to `deploy/requirements-api.txt`.
- Env:
  - `PORTAL_AUTH_DATABASE_URL` = the Supabase connection string
  - `PORTAL_AUTH_SECRET` = a 32+ char random secret (JWT signing)
  - `PORTAL_BOOTSTRAP_ADMIN_EMAIL` / `PORTAL_BOOTSTRAP_ADMIN_PASSWORD`
  - `WAREHOUSE_DATABASE_URL_<ORG>` **per Postgres-backed client** — required. Since
    the 2026-09-01 isolation fix a client org NEVER inherits the unsuffixed
    `WAREHOUSE_DATABASE_URL`; that shared key serves the internal `dev` org only, and
    an org with no key of its own reports "not configured" rather than reading another
    tenant's database. Oracle-backed orgs use `<ORG>_DB_*` and need no warehouse URL.
  - Oracle orgs only: `<ORG>_DB_*` / `<ORG>_ORACLE_DSN`, `DB_THICK_MODE`, `ORACLE_CLIENT_LIB_DIR`
  - OIDC SSO (optional, Azure AD / Entra): set all four of `OIDC_ISSUER`
    (`https://login.microsoftonline.com/<tenant-id>/v2.0`), `OIDC_CLIENT_ID`,
    `OIDC_CLIENT_SECRET`, `OIDC_REDIRECT_URI` (`https://<api-host>/auth/oidc/callback`,
    registered at the IdP) to enable; plus `OIDC_DEFAULT_ORGANIZATION` (org for
    just-in-time provisioned users — always role `user`; SSO never mints admins) and
    `OIDC_POST_LOGIN_URL` (the portal login page, which receives `#sso_token=`).
    The login page shows "Sign in with Microsoft" automatically once `/auth/status`
    reports `oidc_enabled`.
  - Scheduled report delivery (optional): `SMTP_HOST`/`SMTP_PORT`/`SMTP_USERNAME`/
    `SMTP_PASSWORD`/`SMTP_FROM`/`SMTP_STARTTLS`, then add an hourly cron job running
    `python -m api.report_schedule_runner` with the same env (`--dry-run` to verify).
- Expose HTTPS; note the URL (e.g. `https://originba-api.fly.dev`).
- Move saved views/dashboards off local JSON to Supabase before scaling past one
  replica (schema in 001_init.sql; the store code is the one remaining backend task —
  auth already uses the shared DB).

### 2a. API on Fly.io (concrete, ready to run)
`fly.toml` (repo root) + `deploy/Dockerfile.api` are written. From the repo root:

```bash
fly apps create originba-api            # once; name matches fly.toml
# secrets (never in fly.toml): the Supabase POOLED url backs BOTH auth + state
fly secrets set \
  PORTAL_AUTH_DATABASE_URL="postgresql://postgres.<ref>:<pw>@aws-0-us-east-2.pooler.supabase.com:6543/postgres?sslmode=require" \
  PORTAL_AUTH_SECRET="$(openssl rand -hex 24)" \
  PORTAL_BOOTSTRAP_ADMIN_EMAIL="admin@origin.local" \
  PORTAL_BOOTSTRAP_ADMIN_PASSWORD="<strong password>" \
  WAREHOUSE_DATABASE_URL="postgresql://<dbt warehouse>" \
  PORTAL_CORS_ORIGINS="https://originba-portal.vercel.app,https://originba-portal-chase-powers-projects.vercel.app"
fly deploy                              # builds deploy/Dockerfile.api, boots uvicorn
```
The API comes up at `https://originba-api.fly.dev`; `GET /health` is the Fly check.
`min_machines_running = 1` keeps one machine warm so the connection pools stay hot.
For an Oracle-serving build, swap the Dockerfile base to an Instant Client image,
uncomment `oracledb` in `deploy/requirements-api.txt`, and add the `<ORG>_DB_*`
secrets — the Postgres orgs need none of that.

### 2b. API on Render (no credit card — alternative to Fly)
`render.yaml` (repo root) is a Blueprint. In Render: **New + → Blueprint → pick the
`chasepowers59/OriginBA` repo**. It builds `deploy/Dockerfile.api`, health-checks
`/health`, and **auto-deploys on every push**. Set the four `sync:false` secrets in
the dashboard (the Supabase pooled URL, the two bootstrap-admin values, the warehouse
URL); Render generates `PORTAL_AUTH_SECRET` and the CORS origins are baked in.
The code must be on the blueprint's `branch` (default `main` — merge
`feature/bi-builder` first, or set `branch: feature/bi-builder`). Free web services
cold-start after idle; use the Starter plan or Fly for always-on. The API comes up at
`https://originba-api.onrender.com`.

### 3. Vercel (frontend)
- Project is linked to `chasepowers59/OriginBA`, root `apps/analytics-portal`
  (team `chase-powers-projects`). It builds the repo's production branch.
- Set env `NEXT_PUBLIC_API_URL` = the API container URL, then redeploy.
- CORS: the API must allow the Vercel origin (`FRONTEND_ORIGINS` / CORS config).

### 4. Warehouse data (what the `dev` org reads)
- Quick start / fabricated demo: `deploy/load_test_data.sh` dumps the local fixture
  `reporting.*` into Supabase (no VPN, no real data).
- **Real INT_DEV 25.4 data** (real C2M shape, no client PII): `deploy/load_intdev_to_supabase.sh`
  — one command that extracts INT_DEV, builds the dbt reporting layer, and loads it into
  Supabase. Needs **VPN** (Oracle reachable) and `TARGET_DB_URL` (Supabase Session pooler,
  never committed). It preflights both and refuses if a MICR column ever reached the layer.
  Do NOT load a real *client* slice (Ellensburg, etc.) into cloud Supabase — data residency.

## Backups
`deploy/backup_portal_state.sh [outdir]` dumps the control-plane data users create
by hand — auth tables + the whole `portal_state` schema (saved views, dashboards,
schedules, alerts) — into a timestamped `.sql.gz`. Run it daily from the same cron
that runs the report-schedule runner; it needs only `PORTAL_AUTH_DATABASE_URL`.
The warehouse is NOT backed up here (dbt rebuilds it).

## Deploy / update
1. `git push origin main` (or merge the feature branch) — Vercel auto-builds the frontend.
2. Rebuild + roll the API container.
3. Migrations: re-run 001_init.sql if the state schema changed; auth is auto-migrated.

## What must NOT go on Vercel
- The FastAPI API (pools + Oracle Instant Client + optional schedulers).
- The nightly Oracle warehouse builds — those stay on the OKE CronJob / VCN runner
  (see the originba_dbt `oracle-native-rollout` skill), not here.

## Current blockers (need the account owner)
- Push the builder branch to GitHub (this agent cannot `git push`).
- Supabase project is provisioned + schema applied; supply its pooled connection
  string to the API host (the password is the remaining secret).
- Pick + provision the API container host.
