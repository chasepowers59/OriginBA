# Tenant onboarding and migration

The portal scales by **routing, not code**. Every tenant is one entry in
`config/portal_organizations.json` plus one database; nothing else in the application
is per-client. There are exactly two paths, chosen by the org's `catalog` field:

| `catalog` | engine | what the org reads | state |
| --- | --- | --- | --- |
| `dbt` | postgres | the governed reporting canvases (`reporting.rpt_*`) in that client's own dbt warehouse | the destination for every client |
| `cisadm` | oracle | the legacy `*_RPT_CURR` snapshots in the client's Oracle CISADM | legacy, until migrated |

Every surface follows the same routing decision automatically — catalog, explorer,
executive overview, workstream sections, KPI runner, NLQ, My-dashboards templates,
and the Database workspace all ask "which catalog does this org read?" and route.
There is no per-surface configuration and there must never be: a surface that
hard-wires a backend is a bug (that class was swept out on 2026-08-25).

## Why one warehouse per client, not one warehouse with a tenant column

dbt builds a **separate database per client** (the deploy pipeline in `originba_dbt`
already works this way: one target per client in `profiles.template.yml`, Slim CI
deploy on merge). Multi-tenancy in the portal is therefore routing to the right
database, which is stronger than row-level filtering: a bug can never leak one
client's rows into another's dashboard, because the connection itself is scoped.
`WAREHOUSE_DATABASE_URL_<ORG>` beats `WAREHOUSE_DATABASE_URL` when set — per-tenant
first, shared fallback second.

## Onboarding a new client (the template)

Prereqs, in order — each is the same for every client because the dbt project is
fleet-identical (one contract, enforced by tests; per-client differences live in
data and configuration, never in the models):

1. **Landing**: DBAs point the CDC feed at a Postgres database for the client;
   `scripts/landing/01_create_landing_full.sql` is the schema. Run
   `verify_schema_drift.py --client <id>` (originba_dbt) — unexplained drift is a
   stop; accepted drift is recorded with its measurement.
2. **Warehouse**: add the client target to `profiles.template.yml`, let `deploy.yml`
   build it (or run `dbt build` by hand the first time). Both build paths must be
   green — full-refresh AND incremental.
3. **Validation ladder**: run the client through the slice-validation runbook
   (`client-slice-validation` skill in originba_dbt) — reconcile canvases against
   the client's own CISADM before anyone sees a dashboard. New codes discovered
   here widen enumerations + tests together and land in `client-mappings.md`.
4. **Portal entry** — add to `config/portal_organizations.json`:

   ```json
   {
     "id": "newclient",
     "display_name": "New Client",
     "engine": "postgres",
     "catalog": "dbt",
     "warehouse_url_env": "WAREHOUSE_DATABASE_URL_NEWCLIENT"
   }
   ```

5. **Env key**: set `WAREHOUSE_DATABASE_URL_NEWCLIENT` in the deployment
   environment (never in git; the repo `.env` is local-only).
6. **The acceptance gate** — nothing ships without it:

   ```bash
   python3 scripts/check_tenant.py newclient
   ```

   It exercises the real in-process paths: registry entry, catalog, warehouse
   reachability, canvas population (empty canvases are surfaced for a human to
   explain — "no rows" is a finding, never a pass), catalog↔warehouse drift,
   every executive KPI, every workstream section, and a governed query through
   the Database workspace. Exit 0 = the tenant is ready. `--all` sweeps the fleet
   (put it in the weekly QA run).

## Migrating an existing Oracle org

Flip `catalog` to `dbt`, set the warehouse env key, run the gate. Nothing else
changes and no other tenant is affected. **Rollback is the same edit backwards** —
the legacy path stays intact until the fleet is fully migrated, at which point the
`cisadm` catalog, `demo_db`, and the Oracle starter templates can be retired
together (grep for `catalog_name_for_org` to find every routing point).

## What stays fleet-identical vs per-client

- **Fleet-identical**: the dbt models and contracts, the canvas catalog
  (`output/catalog_dbt.json`, generated from the contracts), all KPI definitions,
  DQ rules (`dq_rules/rules.yml` runs unchanged at every client because the canvas
  contract is identical), starter queries and dashboard templates.
- **Per-client**: the warehouse database, client-configured codes (captured in
  `client-mappings.md` and the convention seeds, never hardcoded in models),
  accepted schema drift, and the DQ findings themselves.

The rule that keeps this scalable: **when a fix lands, it lands in the template**
(the dbt project, the shared KPI dict, the rules file) — never as a per-tenant
patch. One fix, every client, next deploy.
