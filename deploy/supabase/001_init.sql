-- OriginBA portal — Supabase (Postgres) schema for shared user state.
--
-- WHY: on Vercel/containers the app runs as MANY stateless instances, so the
-- JSON file stores (saved views, dashboards, DQ acks) cannot be local files --
-- every replica would see different data and lose writes. This is the shared
-- store. (Auth/identity tables self-create via SQLAlchemy when
-- PORTAL_AUTH_DATABASE_URL points at this same database.)
--
-- One generic records table keyed by (collection, organization_id, id) with a
-- JSONB payload: the portal's entry shapes evolve (a measures[] array was just
-- added), and a blob avoids a migration every time a field changes while the
-- API keeps enforcing structure. Org scoping is enforced in the API from the
-- verified JWT; if the browser is ever given direct access, add RLS on
-- organization_id first.

create schema if not exists portal_state;

create table if not exists portal_state.records (
  collection      text not null,          -- 'saved_views' | 'saved_dashboards' | 'dq_acks'
  id              text not null,
  organization_id text not null,
  data            jsonb not null,
  updated_at      timestamptz not null default now(),
  primary key (collection, id)
);

create index if not exists records_scope_idx
  on portal_state.records (collection, organization_id, updated_at desc);
