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

### 1. Supabase (login + user-state DB)
- Create a Supabase project (dashboard). Copy the connection string
  (`postgresql://…pooler.supabase.com:6543/postgres`, the pooled port for apps).
- Apply the state schema: `psql "$SUPABASE_DB_URL" -f deploy/supabase/001_init.sql`.
- The **auth tables create themselves** on first API boot (SQLAlchemy) when
  `PORTAL_AUTH_DATABASE_URL` points at Supabase — no migration needed.

### 2. API container (Fly.io / Render / Railway / OKE)
- Build `deploy/Dockerfile.api` (Postgres-serving base). For Oracle orgs, rebuild
  FROM an Instant Client base and add `oracledb` to `deploy/requirements-api.txt`.
- Env:
  - `PORTAL_AUTH_DATABASE_URL` = the Supabase connection string
  - `PORTAL_AUTH_SECRET` = a 32+ char random secret (JWT signing)
  - `PORTAL_BOOTSTRAP_ADMIN_EMAIL` / `PORTAL_BOOTSTRAP_ADMIN_PASSWORD`
  - `WAREHOUSE_DATABASE_URL` (shared) and/or `WAREHOUSE_DATABASE_URL_<ORG>` per client
  - Oracle orgs only: `<ORG>_DB_*` / `<ORG>_ORACLE_DSN`, `DB_THICK_MODE`, `ORACLE_CLIENT_LIB_DIR`
- Expose HTTPS; note the URL (e.g. `https://originba-api.fly.dev`).
- Move saved views/dashboards off local JSON to Supabase before scaling past one
  replica (schema in 001_init.sql; the store code is the one remaining backend task —
  auth already uses the shared DB).

### 3. Vercel (frontend)
- Project is linked to `chasepowers59/OriginBA`, root `apps/analytics-portal`
  (team `chase-powers-projects`). It builds the repo's production branch.
- Set env `NEXT_PUBLIC_API_URL` = the API container URL, then redeploy.
- CORS: the API must allow the Vercel origin (`FRONTEND_ORIGINS` / CORS config).

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
- Provision the Supabase project + connection string (account creation + secrets).
- Pick + provision the API container host.
