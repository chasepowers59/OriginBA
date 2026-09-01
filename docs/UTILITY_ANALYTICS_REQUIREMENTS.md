# Utility analytics platform — essential requirements vs. current state

2026-09-01. The honest inventory: what analyst/reporting software for utilities must
provide, what OriginBA has today, and the ranked gap list. Statuses: ✅ have ·
🟡 partial · ❌ missing. Update this file when a row changes — it is the roadmap's
source of truth.

## A. Data foundation (the moat — largely done)

| Requirement | Status | Notes |
|---|---|---|
| Governed semantic layer over CIS | ✅ | 38 contracted canvases, grain-asserted, lineage-traced to CISADM |
| Numbers reconcile to the source system | ✅ | comparison suite + question-catalog validator (92/92, 11 exact grain ties) |
| Same warehouse on every deployment shape | ✅ | Postgres CDC + in-database Oracle (Ellensburg 25.4 live) |
| Data freshness visible to users | ✅ | refresh marker + per-table batch counts on Home |
| Data quality worklists with CIS actions | ✅ | 22-rule engine, severity triage, ack workflow |
| Raw-schema SQL access for power analysts | ✅ | CISADM workspace, secrets-guarded, table guides |
| Multi-tenant with per-org catalogs/backends | ✅ | org registry, engine routing, tenant login |

## B. Analyst workflow

| Requirement | Status | Notes |
|---|---|---|
| Self-serve visual builder (drag & drop) | ✅ | table-first pane, shelves, 8 visuals, value picker filters |
| Pre-built report library | ✅ | 92 governed questions, every canvas covered |
| Saved views that actually reopen | ✅ | fixed 2026-08-31 |
| Personal dashboards / pinboards | ✅ | list + editor, cross-filtering |
| Cross-filter / drill interactions | ✅ | click-to-filter across tiles |
| Export: CSV | ✅ | tables + SQL results |
| Export: PDF | 🟡 | council/lineage print packs; no per-chart PDF |
| Export: true Excel (.xlsx) | ✅ | SheetJS workbook: typed numbers, True/False booleans, one sheet per dashboard section |
| **Scheduled report delivery (email/subscriptions)** | ✅ | saved view → CSV email on a cadence; hourly cron runner (`api.report_schedule_runner`), SMTP env |
| Alerting on thresholds (KPI breach → notify) | ✅ | KPI alerts (value/pct-change thresholds), notify once per breach; same runner |
| Annotations / commentary on reports | ✅ | notes on saved views + dashboards; author-or-admin delete |
| Report versioning / history | ❌ | saved views overwrite silently |

## C. Enterprise / IT requirements

| Requirement | Status | Notes |
|---|---|---|
| RBAC (roles, workstream scoping) | ✅ | user/editor/admin + workstream groups |
| Audit log of admin actions | 🟡 | auth events logged; report/query access is not |
| **SSO (SAML/OIDC — Azure AD is the utility default)** | ✅ | OIDC auth-code flow (`/auth/oidc/*`), JIT provisioning as role user, Microsoft button on login |
| MFA | 🟡 | inherited via the IdP when SSO is on; no native MFA for password logins |
| Session/password policy controls | 🟡 | expiry + forced change exist; no lockout/policy UI |
| Deployment shapes (cloud demo / on-prem / in-database) | ✅ | Vercel+Render+Supabase and OKE/VPN paths |
| Backup/restore & environment promotion | ✅ | `deploy/backup_portal_state.sh` dumps auth tables + portal_state nightly; dbt rebuilds the warehouse |
| Accessibility (WCAG) | 🟡→✅ | contrast audited; app-wide :focus-visible ring; charts carry role=img + descriptive aria-labels; builder fields add by click/Enter (no drag required); full screen-reader audit still advisable before a public-sector rollout |
| Mobile usability | 🟡 | nav now works on phones; dashboards usable, builder is desktop-first (fine) |

## D. Brand & experience governance (the "how do we ensure" answer)

| Mechanism | Status | Notes |
|---|---|---|
| Single source of truth: design tokens | ✅ | globals.css tokens + Tailwind registration |
| Brand assets from the real vector | ✅ | origin-logo/-white/-mark; swap in SVG export for infinite crispness |
| **Brand font** | 🟡 | app ships Inter; the Origin wordmark is a distinct geometric sans. Needs the brand guide's font name + license to align |
| Automated enforcement in CI | ✅ | portal-ci runs tsc, tests, `audit:brand` (tokens only, paired accents, flat axes, no raw hex), build |
| Conventions as a living skill | ✅ | .claude/skills/originba-frontend |
| Residual UX debt tracked | ✅ | docs/UX_REVIEW_BACKLOG.md |

## Ranked gaps (the actual roadmap)

Shipped 2026-09 (all tests-first): 1 SSO/OIDC (JIT provisioning, Microsoft button),
2 scheduled report delivery (CSV email on a cadence, hourly runner), 3 true .xlsx
export, 4 KPI threshold alerts (notify once per breach), 5 Aptos brand font,
6 query/report access audit (report runs + SQL executes + fence refusals),
7 report annotations (saved views + dashboards), 10 portal-state backup script.

All ten ranked gaps are shipped as of 2026-09-01: the UX backlog mediums are
closed (see docs/UX_REVIEW_BACKLOG.md) and the accessibility pass added the
app-wide focus ring, chart aria-labels, and keyboard field-add. Remaining
lower-priority follow-ups live in the UX backlog's Low section, plus a full
screen-reader audit before any public-sector rollout.
