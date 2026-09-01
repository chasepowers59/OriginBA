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
| Export: true Excel (.xlsx) | ❌ | "Export Excel pack" writes CSV — misleading label |
| **Scheduled report delivery (email/subscriptions)** | ❌ | the #1 asked-for feature in utility reporting shops |
| Alerting on thresholds (KPI breach → notify) | ❌ | DQ alerts exist for the *pipeline* (qa_alert), not for business KPIs |
| Annotations / commentary on reports | ❌ | analysts explain variances; nowhere to write it down |
| Report versioning / history | ❌ | saved views overwrite silently |

## C. Enterprise / IT requirements

| Requirement | Status | Notes |
|---|---|---|
| RBAC (roles, workstream scoping) | ✅ | user/editor/admin + workstream groups |
| Audit log of admin actions | 🟡 | auth events logged; report/query access is not |
| **SSO (SAML/OIDC — Azure AD is the utility default)** | ❌ | password-only today; enterprise blocker for real rollouts |
| MFA | ❌ | comes largely free with SSO |
| Session/password policy controls | 🟡 | expiry + forced change exist; no lockout/policy UI |
| Deployment shapes (cloud demo / on-prem / in-database) | ✅ | Vercel+Render+Supabase and OKE/VPN paths |
| Backup/restore & environment promotion | 🟡 | dbt rebuilds are reproducible; portal state (views/boards) needs a backup story |
| Accessibility (WCAG) | 🟡 | contrast now audited; keyboard DnD + screen-reader pass not done |
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

1. **SSO/OIDC (Azure AD)** — the enterprise gate. No utility IT department approves a
   password-only analytics tool at rollout. MFA rides along.
2. **Scheduled report delivery** — saved view/dashboard → PDF/CSV on a cron → email.
   The single most-used feature of legacy utility reporting stacks; also what lets the
   portal replace emailed spreadsheets.
3. **True .xlsx export** (and fix the "Excel pack" label until then) — utility finance
   lives in Excel; CSV loses types and formatting.
4. **KPI threshold alerts** — reuse the DQ engine's shape: rule + threshold + notify;
   the exec KPIs are already computed on a schedule.
5. **Brand font decision** — get the font name from Origin's brand guide, load via
   next/font with licensed files, swap the Inter default.
6. **Query/report access audit** — extend the existing audit log to report runs and
   SQL statements (compliance ask in regulated utilities).
7. **Report annotations** — a comments field on saved views/dashboard tiles.
8. **UX backlog burn-down** — docs/UX_REVIEW_BACKLOG.md mediums.
9. **Accessibility pass** — keyboard field-add in the builder (also in the backlog),
   focus states, aria labels on charts.
10. **Portal-state backup** — pg_dump of portal_state/auth schemas on a schedule.
