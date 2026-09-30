# Legacy "Inventory" domains vs the Standard Offering: the tables we do not use yet (2026-09-24)

Chase found `CI_ADJ_APREQ` by reading the tables inside legacy domains, and it became the A/P
request work. This is the same read done systematically over the two exports he took of the
`/SmartCity/Report/Inventory` library (Ellensburg test: 28 domains; Origin_DEV: 25 domains; every
domain present in both uses the same tables, except OriginPay which differs), against every table
the 53 Standard Offering domains use on Origin_DEV (289 distinct tables, from the 2026-09-18
inventory snapshot). Offline; nothing was queried. Exports and the raw per-domain analysis are
under `backups/jaspersoft/legacy_inventory_exports_2026-09-24/`.

**Result: the legacy library is almost entirely inside the offering already.** Of everything the
28 legacy domains read, 19 names are not in a Standard Offering domain; four of those are not
real gaps (two are column names the SQL scan caught, `CI_ADJ_APREQ` is in the new Adjustment
domain, `CI_LOOKUP` is a decode the offering does better). Fifteen tables remain, in seven
groups below, each with what it holds, the value, the ease, and the domain it belongs in. Every
target domain is hand-built, so an addition is the SA 360 premise-characteristics pattern:
export the org's domain, add the `jdbcTable` + join + set to its schema, `domain-apply`, four
proofs. "Verify" means a live measurement when the VPN is on; column lists below are from the
legacy schemas, and the tables not in our landing DDL are marked.

## 1. Field Operations: the CCB side of a field activity (high value, medium ease)

| Table | Holds | Legacy join |
| --- | --- | --- |
| `CI_FA` (landed) | The CCB field activity: type, status, priority, scheduled date/time, dispatch group, field order, cancel and reschedule reasons, created-by, instructions, external id | `D1_ACTIVITY_IDENTIFIER.ID_VALUE = CI_FA.FA_ID` |
| `D1_ACTIVITY_IDENTIFIER` (not landed) | The MDM activity's identifiers by type; the `D1FA` type carries the CCB FA id (the base-product bridge the architect skill names) | `D1_ACTIVITY.D1_ACTIVITY_ID = ...D1_ACTIVITY_ID` |

Today both Field Activity domains reach the FA through a client-built view
(`CMS_D1_ACTIVITY_D1FA_BODA_VW`, parsed out of BO_DATA_AREA). The typed identifier table is
the base-product way, needs no view per client, and once the FA id is on the row the whole
CCB activity comes along: dispatch group, scheduled vs created, cancel reason, instructions.
Verify: `ACTIVITY_ID_TYPE_FLG = 'D1FA'` population per client (resolve rate like the SP bridge's
100%). Target: `Field_Operations/Field_Activity/Field_Activity___Domain` and the 360, replacing
the CMS view. Ease: medium (two outer joins, one typed).

## 2. Severance: the disconnect field activity and the template rules (high value, easy)

| Table | Holds | Legacy join |
| --- | --- | --- |
| `CI_SEV_EVT_FA` (not landed) | Which field activity each severance EVENT created (cut-off, reconnect): process id + event seq -> FA id | `CI_SEV_PROC.SEV_PROC_ID = SEV_PROC_ID`, then `EVT_SEQ` to `CI_SEV_EVT` |
| `CI_SEV_PROC_TMP` (not landed) | The severance template's configuration: auto-cancel switch, cancel-criteria and post-cancel algorithms | `CI_SEV_PROC.SEV_PROC_TMPL_CD = ...` |

The offering's Severance domain is already at event grain (`CI_SEV_EVT`) with the template
LABEL only. `CI_SEV_EVT_FA` + `CI_FA` answers "was the disconnect actually dispatched and
completed, when, by which group" per event, which is the operational question behind every
severance report. Target: `Debt_Management/Severance_Process/Severance_Process___Domain`. Ease:
easy (one join each; event -> FA is one-to-one by key).

## 3. Case: open-vs-closed without client status codes (high value, trivial)

| Table | Holds | Legacy join |
| --- | --- | --- |
| `CI_CASE_TYPE` (landed) | Case type configuration: business object, division, which links a case can carry (person, account, premise, user, contact) | `CI_CASE.CASE_TYPE_CD` |
| `CI_CASE_STATUS` (landed) | Per type and status: `STATUS_COND_FLG` (the base-product open / closed / ... condition), alert flag, transitory flag, sort order | `CI_CASE.CASE_TYPE_CD + CASE_STATUS_CD` |

Status codes are client configuration (the architect skill's costliest lesson), but
`STATUS_COND_FLG` is base product: a "case is open" flag built on it is right at every client.
The offering's Case domain has only the two label tables. Target:
`Customer_Operations/Case/Case___Domain`. Ease: trivial (two outer joins, full composite key).

## 4. Cashiering: tender source configuration and the deposit-control interface (medium value, easy)

| Table | Holds | Legacy join |
| --- | --- | --- |
| `CI_TNDR_SRCE` (not landed) | Tender source configuration: source TYPE (drawer, lockbox, ...), the source's SA, bank and bank account, default start and max balances | `CI_TNDR_CTL.TNDR_SOURCE_CD` |
| `CI_DEP_CTL_ST` (not landed) | Deposit control staging: external source and transmission ids, staging status, transmit time, tender-control totals and counts | `CI_DEP_CTL.DEP_CTL_ID` |

Deposit Control, Payment Tender and Cashiering 360 all carry the tender-source LABEL only; the
source TYPE is the dimension a cashiering report actually groups by, and the balance limits give a
drawer-over-limit flag. `CI_DEP_CTL_ST` is the lockbox / bank transmission trail, one-to-many per
deposit control (outer, or folded). Target: `Cashiering/Deposit_Control/Deposit_Control___Domain`
(both), `Cashiering/Payment_Tender/Payment_Tender___Domain` and the 360 (`CI_TNDR_SRCE`). Ease: easy.

## 5. Billing: the bill cycle schedule (high value, medium ease)

| Table | Holds | Legacy join |
| --- | --- | --- |
| `CI_BILL_CYC_SCH` (not landed) | The billing calendar per cycle: window start and end, accounting date, estimated date, freeze-complete switch | `CI_BILL.BILL_CYC_CD` and `CI_BILL.WIN_START_DT` between the schedule's window |

This is the scheduled side of billing: scheduled vs actual completion, cycles whose freeze is not
complete, accounting date per window, and a cycle calendar for planning. The legacy join is a
range; C2M stamps a bill's window start from the schedule, so an equality on cycle + window start
should be exact (verify: bills whose `WIN_START_DT` is not a schedule row). Target:
`Billing_and_Rates/Billing_360___Domain`, and it also stands alone as a small "Bill Cycle
Schedule" domain for the calendar itself. Ease: medium (the join key needs the verification).

## 6. Meter Operations: the MDM service type and the usage-subscription bridge (medium value, easy)

| Table | Holds | Legacy join |
| --- | --- | --- |
| `D1_SP_TYPE` (not landed) | Service point type configuration: the MDM service type (`D1_SVC_TYPE_CD`), SP category and class, parent-SP indicator, business objects | `D1_SP.D1_SP_TYPE_CD` |
| `D1_SVC_TYPE_L` (not landed) | The MDM service type's label | `D1_SP_TYPE.D1_SVC_TYPE_CD` |
| `D1_US_IDENTIFIER` (not landed) | The usage subscription's identifiers by type; the SA-typed one carries the CCB SA id | `CI_SA.SA_ID = ID_VALUE` (typed; verify the type flag value) |

Every domain with `D1_SP` (Device, Meter Operations 360, Un-billed Usage, Premise-side views)
has the SP type LABEL but not the MDM service type, so meter-side reports cannot slice by
electric / water / gas independently of the CCB SA type. `D1_US_IDENTIFIER` ties the usage
subscription to the SA directly (the offering goes SA -> SA/SP -> SP -> SP identifier), which is
what the vacant-premise-consumption question and any US-lifecycle-vs-SA-lifecycle report need.
Target: `Meter_Operations/Device/Device___Domain`, `Meter_Operations_360___Domain`,
`Usage/Un_Billed_Usage___Domain`. Ease: easy (config joins; the identifier is typed, verify the
type flag).

## 7. Asset: notes and attributes (low to medium value, verify first)

| Table | Holds | Legacy join |
| --- | --- | --- |
| `W1_ASSET_NOTE` (not landed) | Free-text notes on the asset with type, user, time | `W1_ASSET.ASSET_ID` (one-to-many) |
| `W1_ASSET_ATTRIBUTE` (not landed) | Characteristic-shaped attributes on the asset (type, value, FK values) | `W1_ASSET.ASSET_ID` (one-to-many) |
| `W1_ASSET_MEASUREMENT_TYPE` (not landed) | Which measurement types the asset supports | `W1_ASSET.ASSET_ID` |

The offering's Asset domain already carries `W1_ASSET_CHAR`; whether `W1_ASSET_ATTRIBUTE` is a
second characteristics store or the type-level attribute definitions needs a live look (row
counts, overlap with `W1_ASSET_CHAR`) before it earns a place. Notes are meter-shop history, one
row per note, so they belong folded to one row (count, last note, last user) as the Adjustment
domain folds characteristics. Measurement types are configuration of little reporting use.
Target: `Meter_Operations/Asset/Asset___Domain`. Ease: easy once verified; value modest.

## Not recommended

- `CI_LOOKUP`: the lookup FIELD master. The legacy OriginPay domains joined it on `FIELD_VALUE`
  alone, with no `FIELD_NAME`, which decodes across every lookup family at once (the
  cross-family decode the architect skill forbids). The offering already decodes through
  `CI_LOOKUP_VAL_L` by field name.
- `CI_TD_SRTKEY` and `CI_TD_LOG` (To Do): sort-key values and the per-transition log. The
  offering's To Do domain has the drill keys; the log is one-to-many per entry (1.1M rows at
  Ellensburg) and its outcome already sits on the entry's status. If a workload question ever
  needs "time to first assignment" or "times reassigned", fold the log to one row per entry.
  `CI_TD_TYPE` (the To Do TYPE configuration: creating and routing batch, priority, usage type,
  message) IS worth one outer join into `Common/To_Do/To_Do___Domain`; trivial.

## Recommended order

1. Case (`CI_CASE_STATUS` + `CI_CASE_TYPE`) and To Do (`CI_TD_TYPE`): trivial, immediate flags.
2. Severance (`CI_SEV_EVT_FA` + `CI_FA`, `CI_SEV_PROC_TMP`) and Cashiering (`CI_TNDR_SRCE`,
   `CI_DEP_CTL_ST`): easy, real operational questions.
3. Field Activity through `D1_ACTIVITY_IDENTIFIER` + `CI_FA`: replaces a client-built view.
4. Bill cycle schedule and the two MDM tables: each needs one verification first.
5. Asset notes / attributes: after the live look.

## The next ring (needs the VPN)

Chase's method -- the child tables of a header table -- can be run against the database itself
rather than the legacy library: `ALL_CONSTRAINTS` gives every table whose foreign key points at
a Standard Offering header (`CI_ADJ`, `CI_SA`, `CI_ACCT`, `CI_BILL`, `CI_PAY_EVENT`, `CI_FT`,
`D1_SP`, `D1_DVC`, `W1_ASSET`, ...), and the ones absent from the 289 are the candidates the
legacy library never reached. That is the query to run next time the VPN is up.
