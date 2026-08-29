-- OriginBA portal — Supabase (Postgres) schema for auth + user state.
--
-- WHY: on Vercel/containers the app runs as MANY stateless instances, so the
-- SQLite auth DB and the JSON file stores (saved views, dashboards) cannot be
-- local files — every instance would see different data and lose writes. This
-- moves them to one shared Postgres (Supabase). The AUTH tables are created
-- automatically by SQLAlchemy (api/auth/database.py) when PORTAL_AUTH_DATABASE_URL
-- points here, so this file only needs the user-state tables the file stores held.
--
-- Apply: Supabase SQL editor, or `psql "$SUPABASE_DB_URL" -f 001_init.sql`.
-- These live in their own schema so they never collide with the auth tables.

create schema if not exists portal_state;

-- Saved explorer/builder views (was data/analytics_portal/saved_views.json)
create table if not exists portal_state.saved_views (
  id             uuid primary key,
  organization_id text not null,
  snapshot_id    text not null,
  snapshot_label text,
  title          text not null,
  kind           text not null,
  report_id      text,
  dimensions     jsonb,
  measure_field  text,
  measure_agg    text,
  measures       jsonb,          -- multi-measure builder views
  chart_type     text,
  date_preset    text,
  date_start     text,
  date_end       text,
  scope_field    text,
  scope_value    text,
  saved_at       timestamptz not null default now()
);
create index if not exists saved_views_org_idx on portal_state.saved_views (organization_id, saved_at desc);

-- Custom multi-tile dashboards (was data/analytics_portal/saved_dashboards.json)
create table if not exists portal_state.saved_dashboards (
  id              uuid primary key,
  organization_id text not null,
  title           text not null,
  tiles           jsonb not null default '[]'::jsonb,
  updated_at      timestamptz not null default now()
);
create index if not exists saved_dashboards_org_idx on portal_state.saved_dashboards (organization_id, updated_at desc);

-- Data-quality acknowledgements (was data/dq_acks/*.json)
create table if not exists portal_state.dq_acks (
  organization_id text not null,
  finding_key     text not null,
  acked_by        text,
  acked_at        timestamptz not null default now(),
  primary key (organization_id, finding_key)
);

-- NOTE ON RLS: the API is the only writer and it already scopes every query by
-- organization_id from the verified JWT, so these tables are reached through the
-- service role, not the browser. If the browser is ever given direct Supabase
-- access, enable row-level security keyed on organization_id before doing so.
