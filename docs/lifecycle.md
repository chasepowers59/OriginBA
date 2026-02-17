# Origin BA Lifecycle: Implement and Promote to Trusted Zone

This document describes how to move the personalized monthly bill from local development to the **Trusted Zone** on Jaspersoft Server: JSONQL adapter, UAT, publishing, and scheduling. Following these steps keeps the repository and server from being cluttered with broken or unofficial reports.

## 1. Connect Template to Pipeline Output (Studio)

1. In Jaspersoft Studio, create a **JSONQL Data Adapter**.
2. Point it to the Python pipeline output:
   - **File:** path to `output/narrative.json` (or `NARRATIVE_JSON_PATH`), or
   - **URL:** if the pipeline is deployed and exposes the JSON via HTTP.
3. Map fields to the report:
   - `narrative` → Summary Band text field
   - `current_amount` / `prior_amount` → use in totals or charts as needed
4. Attach the adapter to the report **Billing & Rates – Personalized Monthly Statement – Monthly** (see `docs/jasper-template-guide.md`).
5. Run a preview in Studio using sample JSON to confirm layout and field binding.

## 2. User Acceptance Testing (UAT)

Before promoting to the server, run UAT against the **Metrics Catalog**:

- [ ] **Numbers:** Compare amounts and usage on the report to the Metrics Catalog (or governed C2M queries). Ensure definitions match (e.g. active accounts, frozen facts, date window).
- [ ] **Narrative:** Confirm the AI narrative is accurate and appropriate for the sample data (no hallucination, tone consistent with Origin).
- [ ] **Layout:** Verify bands (Detail, Summary, Page Footer), remittance slip, and charts render correctly and do not repeat inappropriately.
- [ ] **Naming:** Report name is **Billing & Rates – Personalized Monthly Statement – Monthly**.

Document any exceptions and get sign-off from the designated UAT owner before publishing.

## 3. Publish to Jaspersoft Server

1. From Studio, **Publish** the report (and any dependent resources, e.g. data source) to the Jaspersoft Server.
2. Place it in the **Trusted Zone** folder/organization so only approved reports are used for production scheduling.
3. Ensure the server can access the pipeline output (same file path, URL, or shared drive) when the report runs.

## 4. Scheduler (Nightly Generation and Email)

1. In Jaspersoft Server, open the **Scheduler**.
2. Create a **job** for the report **Billing & Rates – Personalized Monthly Statement – Monthly**.
3. Set the schedule to **nightly** (or per Origin’s agreed cadence).
4. Configure **email** delivery so generated PDFs are sent to customers or designated distribution list.
5. Optionally chain or trigger the Python pipeline before the report runs (e.g. via cron or workflow) so the latest narrative JSON is available when the report executes.

## 5. Naming Convention (Recap)

| Asset | Convention |
|-------|------------|
| Report | Billing & Rates – Personalized Monthly Statement – Monthly |
| Trusted Zone | Use the folder/organization designated for production reports only |

## 6. Repeatability

- Keep this lifecycle in version control (this doc) so any BA can promote a new or updated template the same way.
- When changing the pipeline output schema (e.g. new JSON fields), update the JSONQL adapter and this doc so UAT and promotion steps stay accurate.
