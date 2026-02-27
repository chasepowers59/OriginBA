# Bill Templating Playbook

## Goal
Support one-bill-per-customer delivery with reusable templates and consistent server deployment.

## Template Included
- `reports/templates/base_customer_bill_template.jrxml`

This template is designed for single-bill rendering by `BILL_ID`, then pulls line items through:
- `repo:subreports/line_items`

## How Clients Use It
1. User selects a `BILL_ID` from an input control list.
2. Report returns exactly one bill header + total.
3. Subreport renders bill segment line items for that bill.
4. PDF can be downloaded or batch-exported.

## Server Resources Required
1. Main report unit:
   - URI example: `/reports/origin/billing_customer_statement`
2. Subreport resource:
   - URI: `/reports/origin/subreports/line_items`
3. Input controls:
   - `server/input_controls/billing_customer_statement_input_controls.json`

## Runtime Parameters
- `BILL_ID` (required)
- `CLIENT_LOGO_URL` (optional)

## Multi-Org Deployment Pattern
1. Keep JRXML logic identical across orgs.
2. Bind each report unit to that org's datasource.
3. Keep repository-relative subreport references (`repo:`).

## Common Failure Modes
1. `Resource not found` for subreport:
   - Ensure subreport resource ID matches `line_items`.
2. Empty output:
   - Validate selected `BILL_ID` exists and has related data.
3. SQL permission errors:
   - Ensure datasource user has access to `CISADM.CI_BILL`, `CI_FT`, `CI_BSEG`.
