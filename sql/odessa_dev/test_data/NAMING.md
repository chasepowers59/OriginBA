# Odessa DEV synthetic test data — naming contract

All rows we insert must be identifiable and removable without touching converted production data.

## Prefix (required)

| Token | Meaning |
|-------|---------|
| `ODEV` | Odessa DEV synthetic row — **only** rows we create |

**Do not use** `999…` numeric IDs for new packs. That range already has ~173 converted accounts and ~2,320 bills on pdevdb.

## ID pattern (pdevdb CHAR limits)

CISADM keys on pdevdb are **fixed-length CHAR**, not long VARCHAR:

| Column | Max chars |
|--------|-----------|
| `PER_ID`, `ACCT_ID`, `PREM_ID`, `SA_ID`, `SP_ID`, `SA_SP_ID` | 10 |
| `BILL_ID`, `BSEG_ID`, `FT_ID` | 12 |

Use compact `ODEV` prefix IDs (rollback: `LIKE 'ODEV%'`):

| Role | Pack B01 ID |
|------|-------------|
| Person | `ODEV010001` |
| Account | `ODEV010002` |
| Premise | `ODEV010003` |
| SA | `ODEV010004` |
| SP | `ODEV010005` |
| SA/SP link | `ODEV040001` |
| Bill | `ODEV01000001` |
| BSEG | `ODEV02000001` |
| FT | `ODEV03000001`, `ODEV03000002` |

Logical naming `ODEV-{PACK}-{ENTITY}-{SEQ}` is documentation only; **stored IDs must fit CHAR limits above**.

## ID pattern (logical / docs)

```
ODEV-{PACK}-{ENTITY}-{SEQ}
```

| Part | Values | Example |
|------|--------|---------|
| `PACK` | Workstream pack code (see below) | `B01` |
| `ENTITY` | Table role | `PER`, `ACCT`, `SA`, `PREM`, `SP`, `BILL`, `BSEG`, `FT`, `TD` |
| `SEQ` | Zero-padded sequence within pack | `0001`, `00000001` |

### Pack codes (reserved)

| Code | Workstream | Purpose |
|------|------------|---------|
| `B01` | Billing | Completed water bill + calc + SQ (+ optional FT) |
| `B02` | Billing errors | Pending bill + `BSEG_STAT_FLG = 20` + `CI_BSEG_EXCP` |
| `W01` | Workflow | `CI_TD_ENTRY` with assignee |
| `V01` | VEE / meter ops | `D1_VEE_EXCP` or usage exception (later) |
| `M01` | Meter install (device/SP) | `D1_DVC` → `D1_DVC_CFG` → `D1_INSTALL_EVT` (+ optional `D1_MEASR_COMP`) |

### Example ID set (pack `B01`, first customer)

| Role | ID |
|------|-----|
| Person | `ODEV-B01-PER-0001` |
| Account | `ODEV-B01-ACCT-0001` |
| Premise | `ODEV-B01-PREM-0001` |
| Service agreement | `ODEV-B01-SA-0001` |
| Service point | `ODEV-B01-SP-0001` |
| Bill | `ODEV-B01-BILL-00000001` |
| Bill segment (water) | `ODEV-B01-BSEG-00000001` |
| FT (if cloned) | `ODEV-B01-FT-00000001` … `00000004` |
| Install event (meter pack) | `ODEV-M01-INST-00000001` |

All IDs fit CISADM column lengths (`ACCT_ID` 40, `BILL_ID`/`BSEG_ID` 48).

## Human-visible marker

Set primary name on every pack:

```text
ODEV TEST {PACK} CUSTOMER {SEQ}
```

Example: `ODEV TEST B01 CUSTOMER 0001` on `CI_PER_NAME.ENTITY_NAME` / `ENTITY_NAME_UPR`.

Reports that filter on customer name can exclude with:

```sql
NVL(entity_name, 'X') NOT LIKE 'ODEV TEST%'
```

## Rollback predicates

Use the same prefix everywhere:

```sql
WHERE per_id    LIKE 'ODEV%'
WHERE acct_id   LIKE 'ODEV%'
WHERE bill_id   LIKE 'ODEV%'
WHERE bseg_id   LIKE 'ODEV%'
WHERE td_entry_id LIKE 'ODEV-%'   -- if we use char-compatible IDs
```

Child tables without `ODEV` in the key are deleted by joining to a parent with `ODEV-%` (see `99_rollback_odev.sql`).

## Clone template (golden source — do not rename)

Pack `B01` clones from this **existing** completed water account (read-only source):

| Entity | Template ID |
|--------|-------------|
| Account | `1110100087` |
| Person | `9184027141` |
| Premise | `4237790275` |
| SA (W-RES) | `7790352119` |
| SP | `8740115078` |
| Bill (latest completed) | `856601546942` |
| BSEG (water + SQ) | `776805100203` |

Clone copies **all NOT NULL columns** from template rows; only `ODEV-*` keys and dates shift.
