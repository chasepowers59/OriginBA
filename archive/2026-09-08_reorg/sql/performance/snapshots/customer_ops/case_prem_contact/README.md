# Case / Premise / Contact Snapshot

This folder is for the customer-operations case snapshot built from `CISADM.CI_CASE` with premise, account, person, and customer-contact context consolidated at case grain.

## Purpose

`CISADM.CASE_PREM_CONTACT_RPT_CURR` is the standardized customer-operations snapshot for case workload, premise overlay, and linked customer-contact reporting.

It is designed for ad hoc reporting where users need one safe row per case with:
- case status, type, condition, and lifecycle timestamps
- responsible user and case-level contact instructions
- account and primary customer context
- premise address and operational premise descriptors when linked
- latest linked customer-contact context without duplicating the case row

## Grain

One row per `CASE_ID`.

Natural key:
- `CASE_ID`

## Source domains consolidated

Field coverage is aligned to Standard Offering domain inventories:
- `Customer_Operations_Case_Case.csv`
- `Customer_Operations_Premise_Premise.csv`
- `Customer_Operations_Customer_Contact_Customer_Contact.csv`

## Why this grain was chosen

The legacy Case domain mixes:
- `CI_CASE` as the driving header
- optional `CI_PREM`, `CI_ACCT`, and person joins
- `CMS_CI_CASE_VW` for create/close timing
- `CI_CC` as a separate contact fact table

Joining `CI_CC` directly at case grain would repeat case rows unless contact rows are rolled up first.

## What is included

- case header fields from `CI_CASE`
- lifecycle timestamps and duration from `CMS_CI_CASE_VW`
- case type/status/condition descriptions from lookup tables
- account context from `CI_ACCT` with bill cycle, customer class, and management group descriptions
- primary case person name from `CI_PER_NAME`
- primary account customer from `CI_ACCT_PER` / `CI_PER_NAME`
- premise address and premise-type / meter-read descriptors when `PREM_ID` is populated
- customer-contact count plus latest linked `CI_CC` context

## Customer contact linkage rule

`CI_CC` rows are linked to a case when either:
- `CI_CC.C1_CONTACT_ID = CI_CASE.C1_CONTACT_ID`, or
- account / premise / person keys match (`ACCT_ID`, `PREM_ID`, `PER_ID`)

The refresh keeps one latest contact per case (`LATEST_CC_*` columns) and a distinct contact count (`CC_COUNT`).

## What is intentionally excluded

- one row per case log entry (`CMS_CI_CASE_LOG_VW`)
- one row per customer contact
- service-agreement detail from the Premise domain join tree
- case-characteristic child rows

Those belong in separate lower-grain snapshots if needed.

## Refresh strategy

| Script | Procedure | Use |
| --- | --- | --- |
| `02a_full_history_refresh_procedure.sql` | `REFRESH_CASE_PREM_CONTACT_RPT_CURR` | First-time baseline: `TRUNCATE` + full insert |
| `02_refresh_snapshot_procedure.sql` | `REFRESH_CASE_PREM_CONTACT_RPT_CURR` | Scheduled refresh: delete/reload cases with `CASE_CRE_DTTM` in the rolling 6-month window |

Rolling window anchor:
- `CMS_CI_CASE_VW.CASE_CRE_DTTM`

Deploy `02a` for initial population, then replace the procedure with `02` for ongoing operations (same procedure name, rolling implementation).

## End-user guidance

Use this snapshot for:
- open-case workload by type, status, owner, and customer class
- case creation trends over recent months
- premise-address overlays on case populations
- case rows with latest customer-contact context

Do not use it to answer:
- case state-transition history
- contact-class distribution across all contacts (use a contact-grain snapshot)
- row-level contact detail for every touchpoint

## Implemented snapshot

- `01_create_snapshot_table.sql`
- `02a_full_history_refresh_procedure.sql`
- `02_refresh_snapshot_procedure.sql`
- `04_validation_queries.sql`

## Related inventory inputs

- `output/standard_offering_domain_inventory/by_domain/Customer_Operations_Case_Case.csv`
- `output/standard_offering_domain_inventory/by_domain/Customer_Operations_Premise_Premise.csv`
- `output/standard_offering_domain_inventory/by_domain/Customer_Operations_Customer_Contact_Customer_Contact.csv`
