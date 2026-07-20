# Odessa DEV test data packs

Synthetic CISADM rows for report/snapshot smoke testing during conversion.  
**Read-only discovery done.** Pack B01 load script is ready; run only on VPN with write access.

## Docs

| File | Purpose |
|------|---------|
| [NAMING.md](NAMING.md) | `ODEV-{PACK}-{ENTITY}-{SEQ}` naming + rollback predicates |
| [PLAN.md](PLAN.md) | What to build per workstream, load order, golden template |
| `00_discover_valid_codes.sql` | Re-run after C2M config changes |
| `01_pack_manifest.sql` | Preflight: ODEV collisions + template exists |
| `10_pack_b01_billing_clone.sql` | **Load + validate** pack B01 in one script |
| `lib/clone_type.sql` | Shared override map type |
| `lib/clone_procedures.sql` | Shared clone/assert procedures (included) |
| `lib/validate_b01_post_load.sql` | Post-commit SELECT validation for B01 |
| `99_rollback_odev.sql` | Delete all `ODEV-%` rows (commented until needed) |

## Workflow

```bash
# 1. Discover (read-only)
python3 scripts/local/run_client_oracle_sql.py \
  --client odessa_dev \
  --file sql/odessa_dev/test_data/00_discover_valid_codes.sql

# 2. Preflight before any load
python3 scripts/local/run_client_oracle_sql.py \
  --client odessa_dev \
  --file sql/odessa_dev/test_data/01_pack_manifest.sql

# 3. Load pack B01 + validate (single script, three phases)
python3 scripts/local/run_client_oracle_sql.py \
  --client odessa_dev \
  --file sql/odessa_dev/test_data/10_pack_b01_billing_clone.sql \
  --fail-if-any-rows

# 4. Rollback when done
python3 scripts/local/run_client_oracle_sql.py \
  --client odessa_dev \
  --file sql/odessa_dev/test_data/99_rollback_odev.sql
```

## Naming rule (summary)

- **Prefix:** `ODEV` only (zero collisions today; do **not** use `999…` — conversion already uses that range).
- **Pattern:** `ODEV-B01-ACCT-0001`, `ODEV-B01-BILL-00000001`, etc.
- **Display name:** `ODEV TEST B01 CUSTOMER 0001` on `CI_PER_NAME`.
- **Rollback:** `WHERE …_id LIKE 'ODEV-%'` (see `99_rollback_odev.sql`).

## Golden clone source (pack B01)

Clone from account `1110100087` (water W-RES, calc + SQ). See [PLAN.md](PLAN.md) for full ID map.

## Pack roadmap

| Pack | Code | Status |
|------|------|--------|
| Billing water | `B01` | **Loaded** — 5 customers (`10` + `11` scripts) |
| Meter install On/Off | `M01` | **Loaded** — 5 devices (`20_pack_m01_meter_five.sql`) |
| Billing errors | `B02` | Planned |
| Workflow to-do | `W01` | Planned |
| VEE exceptions | `V01` | Planned — clone from existing `D1_VEE_EXCP` |
