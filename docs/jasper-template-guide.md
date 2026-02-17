# Jaspersoft Studio Template Guide

This guide defines the **band layout**, **field names**, and **naming convention** for the Origin personalized monthly bill so BAs and developers stay aligned. The template is designed in Jaspersoft Studio 9.0 and consumes the JSON output from the Python pipeline (see `docs/pipeline.md`).

## Report Name (Origin Naming Convention)

Save and publish the template using the Origin standard:

**Billing & Rates – Personalized Monthly Statement – Monthly**

Use this exact name when publishing to the Trusted Zone so it matches the Metrics Catalog and scheduling.

## Band Structure

Structure the report with three main bands so charts do not repeat and the layout stays stable.

| Band | Purpose | Height / Notes |
|------|---------|----------------|
| **Detail Band** | Usage data (line items, meter reads, charges) | Size as needed for one row per usage line. |
| **Summary Band** | AI narrative (2-sentence insight) | **400px** minimum; band grows if narrative is long. |
| **Page Footer** | Remittance slip for physical payment | Fixed height for tear-off slip. |

- Keep **charts** (e.g. usage vs. weather) in a **Subreport** so they render once and do not repeat per detail row.
- Place the **AI narrative** only in the Summary Band so it appears once per bill.

## AI Narrative Field (Summary Band)

1. Drag a **Text Field** into the Summary Band.
2. Set the expression to the field that maps to the pipeline JSON key `narrative` (e.g. `$F{narrative}` when using a JSONQL adapter).
3. In the **Properties** view, set **Text Adjust** to **StretchHeight**.

This allows the band to grow with the narrative length so long insights do not get cut off and the bill stays professional.

## Data Source: JSONQL Adapter

- Create a **JSONQL Data Adapter** in Studio that points to the Python pipeline output (file path or URL).
- Map the JSON keys to report fields:
  - `narrative` → text field in Summary Band
  - `current_amount` / `prior_amount` → use for totals or charts if needed
  - `amount_delta` / `percent_change` → KPIs for display (e.g. "Change from last month: +$30 (+25%)")

Field names in the adapter must match the pipeline output schema in `docs/pipeline.md`.

## HTML5 Charts (Usage vs. Weather)

- Add **HTML5 Charts** in a **Subreport** (not in the Detail Band) so the chart renders once per report.
- Use the same adapter or a shared data source so the chart can use `current_amount`, `prior_amount`, or usage/weather data if present in the JSON or a separate query.

## Checklist Before Publishing

- [ ] Detail Band: usage line items only; no chart in Detail.
- [ ] Summary Band: 400px height; Text Field with Text Adjust = StretchHeight; expression = narrative field.
- [ ] Page Footer: remittance slip only.
- [ ] Charts: in Subreport only.
- [ ] Report name: **Billing & Rates – Personalized Monthly Statement – Monthly**.
- [ ] JSONQL adapter: maps `narrative`, and optionally `current_amount` / `prior_amount` / `amount_delta` / `percent_change`.

## AC-061 (Customer Contact Letters) – Conditional Print and Audit Styling

For **Customer Contact Letters** (AC-061), use status-driven logic so the Senior Data Auditor can distinguish finalized vs in-progress data.

### Conditional Print: Welcome Letter

- **Rule:** Print the **Welcome Letter** only when the Service Agreement status has moved from **Pending** to **Active** (e.g. `SA_STATUS_FLG` from `'10'` to `'20'`).
- **In Jaspersoft Studio:** Add a **Print When** expression on the band or text element that contains the Welcome Letter. Example (adjust field/parameter names to your Domain):  
  `$F{SA_STATUS_FLG} == "20" && $V{PREV_SA_STATUS} == "10"`  
  If your data source does not provide previous status, use a subreport or query that compares current SA status to a prior snapshot (e.g. last month) so the condition reflects the transition.

### Conditional Style: Unfinalized Figures (FREEZE_SW = 'N')

- **Rule:** Rows where **FREEZE_SW = 'N'** are not finalized (human or batch has not closed the math). Highlight them so the auditor knows they are not yet suitable for financial statements.
- **In Jaspersoft Studio:** Create a **Conditional Style** on the detail row (or the table/grid showing financial rows):
  - **Condition:** `$F{FREEZE_SW} == "N"` (or the equivalent from your JSON/Domain).
  - **Style:** Set **Background** to **Yellow** (or another highlight). Apply this style to the row or to the amount cells.
- **Result:** The Senior Auditor can quickly see which lines are still in a "Not Frozen" state and need follow-up before closing the books.
