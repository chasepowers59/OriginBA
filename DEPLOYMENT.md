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
- Project `hvnfyulgwpjpeeowzuni` (region us-east-2) is live and the state schema
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
  - `WAREHOUSE_DATABASE_URL` (shared) and/or `WAREHOUSE_DATABASE_URL_<ORG>` per client
  - Oracle orgs only: `<ORG>_DB_*` / `<ORG>_ORACLE_DSN`, `DB_THICK_MODE`, `ORACLE_CLIENT_LIB_DIR`
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
- Supabase project is provisioned + schema applied; supply its pooled connection
  string to the API host (the password is the remaining secret).
- Pick + provision the API container host.
