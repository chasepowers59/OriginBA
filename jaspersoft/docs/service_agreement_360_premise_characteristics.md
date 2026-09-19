# Service Agreement 360 — Premise Characteristics (CISADM)

## Which domain this is

**Service Agreement 360 - Domain** is the Standard Offering CISADM semantic layer:

- JRS path: `/SmartCity/Report/Standard_Offering/Customer_Operations/Service_Agreements/Service_Agreement___Domain`
- Repository name: `Service_Agreement___Domain`
- Driving join tree: **`JoinTree_1`** (root `CI_SA`, including contract terms and TOU fan-out)
- Characteristic premise link: **`CI_SA.CHAR_PREM_ID` → `CI_PREM.PREM_ID`**

Do **not** use the dbt canvas **`RPT_SERVICE_AGREEMENT_BI`** / `rpt_service_agreement` for this workstream change.

## What was added

Live CISADM **`CI_PREM_CHAR`** on the existing premise path, as a **derived table** — and the
existing **2.0) Service Agreement Characteristics** (`CI_SA_CHAR`) was converted to the same
shape (reviewed and reworked 2026-09-17; the reasons are in
`scripts/jaspersoft/patch_domain_characteristics.py`):

| Item group | Content |
| --- | --- |
| **2.1) Premise Characteristics** | derived `CI_PREM_CHAR`: raw columns + **Characteristic Type Description**, **Characteristic Type Kind** (DFV / ADV / FKV), **Characteristic Value Description**, **Characteristic Value** (resolved by kind), **Is Current Characteristic** |
| **2.0) Service Agreement Characteristics** | derived `CI_SA_CHAR`, same columns |
| **1.) Formulas** | **Distinct Premise Characteristic** (`PREM_CHAR_DIST`); **Distinct Service Agreement ID** now counts `CI_SA.SA_ID` (it counted SAs with contract terms) |

Joins (all **left outer**): `CI_SA.CHAR_PREM_ID == CI_PREM.PREM_ID`, then
`CI_PREM.PREM_ID == CI_PREM_CHAR.PREM_ID`; `CI_SA.SA_ID == CI_SA_CHAR.SA_ID`. The
`CI_CHAR_TYPE_L` / `CI_CHAR_VAL_L` label tables are no longer joined — their descriptions
are folded into the derived rows. Derived-table ids equal the old table ids, so saved Ad Hoc
views keep resolving.

Every table takes the source export's datasource id (the builder reads it; it refuses a
schema with two).

## Why derived tables

- **The type-code list is scoped.** Dragging *Characteristic Type Code* from a label table
  offered every characteristic type in the system (account, person, SA, premise...) and,
  selected alone, queried the label table alone. Now the values are exactly the
  characteristics that exist on premises (on SAs for 2.0).
- **Effective dating without losing history.** Characteristics are versioned by `EFFDT`.
  Every version is still a row; **Is Current Characteristic = Y** marks the latest version
  that is not future-dated. Filter on it for "as of today", leave it off for history.
- **Every value resolves.** `CI_CHAR_VAL_L` only describes predefined (DFV) types; ad hoc
  (ADV) and foreign-key (FKV) characteristics had no description. *Characteristic Value*
  picks by `CI_CHAR_TYPE.CHAR_TYPE_FLG`: DFV → label (or code), ADV → ad hoc text, FKV →
  foreign key. On the Ellensburg slice 19 of 50 premise characteristics are ADV.

## Grain and Ad Hoc usage

- Characteristic groups are **tall** (entity × type × version). Selecting them beside
  contract-term, TOU or history fields multiplies rows; that is the 360 design (pull
  everything, then filter), and the **1.) Formulas** distinct counts stay honest.
- For one row per SA per characteristic type: filter **Is Current Characteristic = Y**.
- For a crosstab by characteristic: rows = SA, columns = *Characteristic Type
  Description*, measure = *Characteristic Value*, with the current filter on.

## Rebuild import bundle

```bash
python3 scripts/jaspersoft/build_service_agreement_360_prem_char_domain.py
```

Output:

- `domains/manual_imports/service_agreement_360_prem_char/Service_Agreement___Domain_prem_char_client_import.zip`
- Reference `schema.data` + domain XML alongside the bundle

Domain wrapper XML is passed through unchanged from the source export. For client tenants, start from that tenant’s Standard Offering export (or retarget only the three prem-char jdbcTables if needed).

## Import

1. Import the ZIP into the client org (overwrite existing **Service Agreement 360 - Domain**).
2. Open Domain Designer → **JoinTree_1** → the two derived tables (`CI_SA_CHAR`, `CI_PREM_CHAR`) must show as joined; open each and confirm its query previews (the server validates derived queries on load).
3. Ad Hoc: add **Service Agreement ID**, **Characteristic Premise ID**, **Characteristic Type Description**, **Characteristic Value**, **Is Current Characteristic**; the type-code filter list must show only premise characteristic types.

## Validation (VPN required)

```bash
python3 scripts/local/run_client_oracle_sql.py --client collegestation \
  --file sql/validation/service_agreement_prem_char_grain_check.sql
```

Offline checks (no server): `python3 -m pytest tests/test_domain_characteristics_patch.py -q`; schema validator:

```bash
python3 scripts/jaspersoft/validate_domain_schema.py \
  domains/manual_imports/service_agreement_360_prem_char/Service_Agreement___Domain_files/schema.data
```
