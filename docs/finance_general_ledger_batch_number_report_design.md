# General Ledger Batch Number Report Design

## Purpose

This report replaces the brittle exported Ad Hoc wrapper for `General_Ledger___Batch_Number_Report` with a maintained self-contained report unit.

Business goal:
- review one GL batch at a time
- return the actual GL lines for that batch
- keep just enough top-of-report summary to validate the batch without losing the underlying detail
- present the batch in a finance-friendly layout rather than a raw technical dump

## Report Grain

One row per GL line within the selected batch.

Driving identifiers:
- `GL_LINE.FT_ID`
- `GL_LINE.GL_SEQ_NBR`
- `SNAPSHOT_AUDIT.BATCH_NBR`

This report is intentionally detailed. It is for investigating a chosen batch, not for multi-batch executive rollup.

## Required Parameter

- `BATCH_NBR_FILTER`

This is required because the report is designed for single-batch review, not unrestricted historical browsing.

## Optional Filters

- `BATCH_CD_FILTER`
- `GL_STATUS_FILTER`
- `GL_ACCT_FILTER`
- `ONLY_EXCEPTION_GROUPS`
- `MIN_ABS_GROUP_AMOUNT`

Implementation note:
- `BATCH_NBR_FILTER` is pushed into the Domain query itself through `<queryFilterString>`
- the semantic-layer predicate is `SNAPSHOT_AUDIT.BATCH_NBR == BATCH_NBR_FILTER`
- this mirrors the original exported Ad Hoc view behavior instead of relying on a post-query report filter
- `CLIENT_LABEL` is a hidden JRXML parameter used for the environment/client name shown in the title and page header
- for other clients, replace only the `CLIENT_LABEL` default during packaging rather than trying to derive the label from the repository path at runtime

## Summary Content

The report title area shows:
- client label
- short subtitle
- batch code
- freeze user
- freeze timestamp
- snapshot load timestamp
- total GL lines
- distinct FTs
- distinct GL accounts
- distinct customers
- debit total
- credit total
- net GL amount
- row-level issue counts

## Detail Content

The detail table shows:
- status
- accounting date
- GL status description
- distribution description
- `DST_ID`
- debit amount
- credit amount
- net GL amount
- statistic amount
- account ID
- customer name
- `FT_ID`
- `GL_SEQ_NBR`

## Presentation Pattern

The report is intentionally styled for business review:
- dark blue title band
- lighter blue summary and grouping bands
- repeating page header with current batch and group context
- zebra striping in detail rows
- technical IDs shifted to the right
- accounting-style negative amount presentation
- finance-friendly grouping by:
  - financial transaction type
  - GL account

## Current SQL Mapping

The current report covers these requested SQL outputs:
- `GL_BATCH_NBR`
  - mapped from `SNAPSHOT_AUDIT.BATCH_NBR`
- `FT_ID`
  - mapped from `GL_LINE.FT_ID`
- `DISTRIBUTION_CODE`
  - mapped from `GL_LINE.DST_ID`
- `GL_ACCT`
  - mapped from `GL_LINE.GL_ACCT`
- `FT_AMOUNT`
  - mapped from `GL_LINE.GL_AMOUNT`
- `FT_TYPE_DESCRIPTION`
  - mapped from `FT_CORE.FT_TYPE_FLG_DESC`
- `GL_DISTRIBUTION_STATUS`
  - mapped from `FT_CORE.GL_DISTRIB_STATUS_DESC`
- `ACCOUNTING_DATE`
  - mapped from `FT_CORE.ACCOUNTING_DT`
- `ACCT_ID`
  - mapped from `ACCT_SERVICE.ACCT_ID`

The current report does not yet expose these requested fields:
- `FT.FT_TYPE_FLG`
- `FT.GL_DISTRIB_STATUS`
- `SA.SA_TYPE_CD`
- `SATL.DESCR`

If exact parity with the posted SQL is required, add:
- `FT_CORE.FT_TYPE_FLG`
- `FT_CORE.GL_DISTRIB_STATUS`
- `ACCT_SERVICE.SA_TYPE_CD`
- `ACCT_SERVICE.SA_TYPE_DESC`

## Status Logic

- `ERROR`
  - missing `GL_ACCT`
  - or zero-amount lines in the group
- `WARN`
  - non-posted / non-distributed status rows in the group
- `OK`
  - no known issue flags in the group

## Packaging Decision

Do not package this as an Ad Hoc wrapper pointing to `/public/templates/actual_size.820.jrxml`.

Package it as:
- a self-contained report unit
- a local `main_jrxml`
- direct Domain reference to `FT_and_GL_Snapshot___Domain`

The import package also carries its own local input controls. `BATCH_NBR_FILTER` should remain a numeric prompt in the packaged report unit because the actual batch restriction is now applied in the Domain query itself through `queryFilterString`.

This avoids the same import-debug cycle already documented in:
- [jaspersoft_repository_import_debugging_runbook.md](/C:/Users/cvpow/OneDrive/Desktop/OriginBA/docs/jaspersoft_repository_import_debugging_runbook.md)
