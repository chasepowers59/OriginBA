# Jaspersoft Client Form Ideas (C2M Utilities)

## Confirmed Feasibility: Customer Contact Letter
- Live schema validation confirms printable contact letter sources:
  - `CISADM.CI_CC` (includes `PRINT_LETTER_SW`, `LETTER_PRINT_DTTM`, `LTR_TMPL_CD`, `DESCRLONG`)
  - `CISADM.CI_PER_NAME` (contact name)
  - `CISADM.CI_PREM` (mailing address)
- Result: yes, the letter can be printed from customer contact info in Jaspersoft.

## High-Value Template Ideas
1. Customer Contact Letter Pack
- Purpose: print notice/door tag/first notice letters from `CI_CC`.
- Layout: official letterhead, recipient block, dynamic body from `DESCRLONG`, signature line.
- Design variant: "Regulatory Formal" (high-contrast monochrome, strict spacing, archive footer).

2. Billing Explanation Statement
- Purpose: explain recent bill changes to reduce call-center volume.
- Data: `CI_BILL`, `CI_FT`, `CI_BSEG`.
- Design variant: "Story Card" (mini charts + plain-language bullets + action panel).

3. Payment Arrangement Confirmation
- Purpose: confirm installment plans and due milestones.
- Data: `CI_SA`, debt metrics, due dates.
- Design variant: "Timeline" with milestones and detachable reminder stub.

4. Arrears Escalation Notice
- Purpose: first/second/final notice automation by debt-age bucket.
- Data: `CI_FT` arrears, `CI_ACCT_ALERT`.
- Design variant: color-coded urgency ribbon + legal footer by client.

5. Field Appointment Notice
- Purpose: outbound appointment letters/SMS PDFs for field operations.
- Data: `D1_ACTIVITY`, `CI_SP`, `D1_SP`.
- Design variant: route window card with map placeholder and QR code for confirmation.

6. Meter Exception Summary
- Purpose: exception communications for estimated/failed reads.
- Data: `D1_MSRMT`, `D1_MEASR_COMP`, `D1_INSTALL_EVT`.
- Design variant: compact "technical appendix" section for engineering teams.

7. Deposit Reconciliation Certificate
- Purpose: daily cashiering audit packet.
- Data: `CI_PAY_EVENT`, `CI_PAY_TNDR`, `CI_DEP_CTL`.
- Design variant: audit ledger style with control totals and sign-off blocks.

8. Service Start Welcome Pack
- Purpose: onboarding letter with service details and next actions.
- Data: `CI_SA`, `CI_SP_CHAR`, customer account context.
- Design variant: branded welcome style with checklist and self-service links.

9. Vulnerable Customer Care Check-In
- Purpose: periodic outreach letter and proof-of-contact report.
- Data: account alerts + contact history.
- Design variant: accessibility-first typography and simplified language version.

10. Executive Workstream Health Brief
- Purpose: one-page client leadership digest.
- Data: `output/workstream_health.json`, `output/config_completeness.json`.
- Design variant: KPI grid + red/amber/green panel + "Top 3 interventions" block.

## Design System Directions for Client-Specific Branding
1. Civic Classic
- Serif headings, formal spacing, grayscale print optimization.

2. Utility Modern
- Sans-serif, icon-assisted section headers, strong whitespace hierarchy.

3. Operations Compact
- Dense tabular layout for back-office users; minimal ornament, max information density.

## Template Engineering Recommendations
1. Keep all report parameters in ALL_CAPS (`CLIENT_ID`, `START_TS`, `END_TS`, `CC_ID`).
2. Keep one master style library per client (`fonts`, `brand colors`, `legal footer`).
3. Split reusable blocks into subreports (address block, legal clause, payment coupon).
4. Add an "Audit Metadata" footer: datasource name, run timestamp, parameter echo.
5. Build print-safe defaults (A4 and Letter variants, monochrome-friendly contrasts).

## Integration Plan (Implemented Assets)
1. Portfolio scorecard SQL: `sql/client_value_scorecard.sql`
2. Contact-letter readiness KPI SQL: `sql/customer_contact_readiness_kpi.sql`
3. Scorecard Input Controls payload: `server/input_controls/client_value_scorecard_input_controls.json`
4. Scorecard JRXML template starter: `reports/client_value_scorecard.jrxml`
5. Execution roadmap by business capability: `docs/c2m-idea-integration-backlog.md`
