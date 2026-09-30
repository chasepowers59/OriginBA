# Service Agreement 360 — Premise Characteristics patch

Extends Standard Offering **`Service_Agreement___Domain`** (label **Service Agreement 360 - Domain**) with live **`CISADM.CI_PREM_CHAR`** on the existing **`CI_SA` → `CI_PREM`** path.

## Rebuild

```bash
python3 scripts/jaspersoft/build_service_agreement_360_prem_char_domain.py
```

Every table, including the two derived characteristic tables, takes the source export's datasource id (the builder reads it and refuses a schema with two).

## Import

Upload `Service_Agreement___Domain_prem_char_client_import.zip` to the tenant repository and overwrite the existing domain under:

`/SmartCity/Report/Standard_Offering/Customer_Operations/Service_Agreements`

## Ad Hoc field group

**2.1) Premise Characteristics** — a derived table (type/value descriptions, resolved value, Is Current flag), the same shape **2.0) Service Agreement Characteristics** now has.

See `jaspersoft/docs/service_agreement_360_premise_characteristics.md`.
