# Analytics Portal — Identity & Access Control

The portal uses a **separate identity database** from Oracle/CISADM. Analytics credentials stay in the existing vault; user accounts live in `PORTAL_AUTH_DATABASE_URL`.

## Roles

| Role | Capabilities |
| --- | --- |
| **User** | View reports, run governed queries, NLQ, executive dashboards |
| **Editor** | User + save views, custom dashboards, Ad Hoc Builder |
| **Admin** | Editor + manage users/groups, database connection, raw SQL tab |

## Security features

- **Workstream scoping** applies to snapshots, report library, and executive dashboard KPIs.
- **Password change gate** — new users and admin password resets require a password change before portal access.
- **Login rate limiting** — 5 failed attempts per email/IP per 5 minutes.
- **Admin self-lockout guards** — admins cannot deactivate themselves or change their own role.
- **Data source redaction** — non-admins only see whether a database is configured, not masked credentials.
- **NLQ + custom dashboards** — metric catalog, NLQ queries, and dashboard tiles are limited to accessible snapshots/workstreams.
- **Audit log** — admin user/group/password changes recorded; view under Settings → Users & access.

## Access groups

Access groups restrict which **workstreams** appear in the sidebar and explorer.

- `*` = all workstreams (default when a user has no groups)
- Otherwise only listed workstreams (e.g. `cashiering`, `finance`) are visible

Assign groups when creating or editing users in **Settings → Users & access**.

## Configuration

```bash
# Identity store (PostgreSQL recommended for production)
PORTAL_AUTH_DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/portal_auth

# Required when auth is enabled (min 32 characters)
PORTAL_AUTH_SECRET=change-me-to-a-long-random-secret-value

# Optional: disable auth for local development (open admin access)
PORTAL_AUTH_DISABLED=true

# Bootstrap first admin (created only when user table is empty)
PORTAL_BOOTSTRAP_ADMIN_EMAIL=admin@your-utility.org
PORTAL_BOOTSTRAP_ADMIN_PASSWORD=ChangeMe-Admin-1!

# Token lifetime (minutes)
PORTAL_AUTH_ACCESS_MINUTES=480
```

### Frontend (Next.js)

```bash
# Match API — disable login gate locally
NEXT_PUBLIC_PORTAL_AUTH_DISABLED=true
```

When auth is enabled, set `NEXT_PUBLIC_PORTAL_AUTH_DISABLED=false` (or unset) and sign in at `/login`.

## API endpoints

| Method | Path | Access |
| --- | --- | --- |
| GET | `/auth/status` | Public |
| POST | `/auth/login` | Public |
| GET | `/auth/me` | Authenticated (allowed while password change pending) |
| POST | `/auth/change-password` | Authenticated (password change pending) |
| GET/POST/PUT | `/auth/users` | Admin |
| GET/POST/PUT/DELETE | `/auth/groups` | Admin |
| GET | `/auth/audit-log` | Admin |

Send `Authorization: Bearer <token>` on all protected routes.

## Local development

1. `PORTAL_AUTH_DISABLED=true` in `.env` — no login required (dev admin context).
2. Or enable auth with SQLite default (`data/analytics_portal/portal_auth.db`) and sign in as bootstrap admin.

### Local auth enabled (current setup)

```bash
# .env
PORTAL_AUTH_SECRET=local-dev-portal-auth-secret-key-32chars-minimum
PORTAL_BOOTSTRAP_ADMIN_EMAIL=admin@origin.local
PORTAL_BOOTSTRAP_ADMIN_PASSWORD=ChangeMe-Admin-1!

# apps/analytics-portal/.env.local
NEXT_PUBLIC_PORTAL_AUTH_DISABLED=false
```

Start API (`uvicorn api.app:app --port 8000`) and portal (`npm run dev`), then open http://localhost:3000 — you will be redirected to `/login`.

Default bootstrap admin: `admin@origin.local` / `ChangeMe-Admin-1!`

Validate the stack:

```bash
python3 scripts/smoke_portal_auth.py
```

## Production checklist

1. Host PostgreSQL (or managed DB) for `PORTAL_AUTH_DATABASE_URL`
2. Set strong `PORTAL_AUTH_SECRET`
3. Set `PORTAL_AUTH_DISABLED=false`
4. Change bootstrap admin password after first login
5. Create access groups per team (Cashiering, Finance, etc.)
6. Assign users to groups and roles
