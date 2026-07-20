# Odessa conversion validation

Validate that converted pdevdb data follows **C2M relationship rules** and matches reference clients.

## Start here

| Doc | Purpose |
|-----|---------|
| **[WORKSTREAMS.md](WORKSTREAMS.md)** | Plain-language: billing, todo, meters, devices, field ops, VEE, usage |
| **[MANIFEST.md](MANIFEST.md)** | Gate catalog (FAIL vs WARN) per workstream |

## Quick start (VPN on)

```bash
# Full suite — all workstreams
python3 scripts/local/run_conversion_validation.py --client odessa_dev

# One process area
python3 scripts/local/run_conversion_validation.py --client odessa_dev --workstream billing
python3 scripts/local/run_conversion_validation.py --client odessa_dev --workstream meter_ops
python3 scripts/local/run_conversion_validation.py --client odessa_dev --workstream devices
python3 scripts/local/run_conversion_validation.py --client odessa_dev --workstream workflow
python3 scripts/local/run_conversion_validation.py --client odessa_dev --workstream field_ops
python3 scripts/local/run_conversion_validation.py --client odessa_dev --workstream vee
python3 scripts/local/run_conversion_validation.py --client odessa_dev --workstream usage

# Profile only (no pass/fail)
python3 scripts/local/run_conversion_validation.py --client odessa_dev --discovery-only

# Compare to reference client
python3 scripts/local/run_conversion_validation.py --client odessa_dev --reference citycorp --discovery-only

# Faster gate rerun (skip discovery); save full log
python3 scripts/local/run_conversion_validation.py --client odessa_dev --gates-only \
  --report-file /tmp/odessa_validation.txt

# Treat WARN gates as failures (CI strict mode)
python3 scripts/local/run_conversion_validation.py --client odessa_dev --strict-warn
```

**Note:** Do not pipe through `tail` if you need the script exit code (`echo $?`). Use `--report-file` instead.

**Latest findings:** [FINDINGS.md](FINDINGS.md)

## Layout

```
conversion_validation/
  WORKSTREAMS.md          ← understand the model
  MANIFEST.md             ← gate index
  discovery/              ← row counts & distributions (informational)
  gates/
    billing/
    workflow/
    meter_ops/
    devices/
    field_ops/
    vee/
    usage/
```

## Two layers

| Layer | Purpose |
|-------|---------|
| **Discovery** | What does the DB look like? |
| **Gates** | Is anything wrong? (empty result = pass) |

Pair with `sql/odessa_dev/test_data/` to prove reports work when data is shaped correctly.
