# Snapshot QA Intake Standard

## Purpose
Use this when sending SQL Developer results for a governed snapshot QA pass.

It reduces back-and-forth and makes it easier to convert your outputs into:
- the snapshot QA results file
- the master technical guide QA section
- the release decision

## Minimum Evidence To Send

For every snapshot, send these blocks:
1. source vs snapshot row count
2. source rows missing in snapshot
3. snapshot rows not in source
4. duplicate natural-key check
5. main additive measure parity
6. main overlay/context coverage block
7. raw-code-only or missing-description audit

## Nice-To-Have Evidence

Send these when they exist in the QA pack:
- distribution by family or status
- month-level parity
- bridge-method or overlay-method breakdown
- sample rows for code-only fields
- source-lookup-gap counts separate from description-mismatch counts

## Paste Format

When possible, label each result block before pasting it:

```text
4a Row Count Parity
<paste output>

4b Anti-Join Source Missing
<paste output>

4c Anti-Join Snapshot Extra
<paste output>
```

That makes it faster to tell whether a suspicious count is:
- a real defect
- expected due to a known design choice
- a QA query that is overcounting through join fan-out

## Decision Rules

Treat as a blocker:
- non-zero anti-joins unless intentionally excluded population is documented
- duplicate natural-key rows
- additive measure mismatch for the promised business truth
- missing or multiplied driving population

Do not treat as a blocker by default:
- missing description columns the business already accepted as code-only
- source lookup coverage gaps when snapshot values still match the source outcome
- QA comparison blocks whose source-side join graph obviously multiplies rows

## Accepted Code-Only Pattern

If the business has already accepted code-only fields, say that explicitly in the results you send.

Example:
- `DIVISION_CD` accepted as code-only
- status reason codes accepted as code-only
- no translation required for release

## Finish Line

After QA is accepted, update all three:
- the snapshot `*_qa_results_template.md`
- the snapshot `*_master_technical_guide.md`
- the snapshot `README.md` if release status or caveats changed
