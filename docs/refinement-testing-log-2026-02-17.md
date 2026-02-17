# Refinement and Testing Log - 2026-02-17

## Scope
- Maintain read-only validation against Oracle C2M.
- Improve report/data robustness for customer contact letter workflows.
- Keep deployment process aligned with strict compliance mode.

## Read-only validation executed
1. `python -m pipeline.test_queries`
- Status: PASS
- Notes:
  - Strategic arrears returned populated dataset.
  - Duplicate-payment and bankruptcy monitor returned zero rows in current window.

2. `python -m pipeline.validate_tables`
- Status: PASS
- Outputs refreshed:
  - `output/workstream_health.json`
  - `output/config_completeness.json`
  - `output/validation_metadata.json`

## Schema confirmation for contact-letter reporting
- Verified tables:
  - `CISADM.CI_CC`
  - `CISADM.CI_LETTER_TMPL`
  - `CISADM.CI_PER_NAME`
  - `CISADM.CI_PREM`
- Confirmed live records with `CI_CC.PRINT_LETTER_SW = 'Y'`.

## Refinements applied
- Added CI_CC and CI_LETTER_TMPL to table health checks.
- Added config completeness rules for customer-contact letter readiness:
  - Printable contacts missing template code.
  - Printable contacts missing recipient essentials (name/address).

## Operational observations
- `field_ops` currently flagged as Data Currency Risk by `CI_SP.INSTALL_DT` 7-day check.
- `F1_TSK`, `F1_TSK_LOG`, `F1_BATCH_RUN`, `F1_EXT_LOOKUP` are not present in this environment.

## Next testing cycle (read-only)
1. Re-run `pipeline.validate_tables` after each schema-related refinement.
2. Validate customer-contact letter output by sample `CC_ID`.
3. Capture explain plans for:
  - `sql/customer_contact_letter.sql`
  - `sql/hourly_rollup.sql`
