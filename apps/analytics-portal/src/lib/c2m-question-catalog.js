// ---------------------------------------------------------------- the question library
//
// Predefined SQL over the REPORTING canvases only. Never landing, never staging: the
// canvases carry the enforced contracts, the Title-Case names Jaspersoft binds to, and
// the grain assertions. A question that reaches past them is a second transformation
// layer by another name.
//
// NO SQL IS EVER BUILT FROM USER INPUT. Each entry's `sql` is a fixed string; the only
// thing a request chooses is WHICH entry runs and which tenant it runs against. That is
// what makes this safe to point at a client warehouse.
//
// Every question is phrased the way a utility actually asks it, and answers with one of
// five shapes -- total, count, ranking, distribution, outlier -- because those are what
// the operational questions reduce to. `axis` names the label column and `value` the
// number, so the renderer needs no per-question code.
//
// PORTABILITY: codes are client configuration and differ per client, so no question
// filters on one. They group BY code and let the reader see what this client uses. The
// exceptions are base-product constants (bill segment status 50/60, BO statuses like
// COMPLETE and ERROR), which are safe everywhere and are commented where used.

export const PROCESSES = [
  { id: "customer", name: "Customer & Account",
    blurb: "Who the utility serves, how they are reached, and what they have agreed to." },
  { id: "meter", name: "Metering & Assets",
    blurb: "The physical estate: devices, service points, installs and the asset record." },
  { id: "usage", name: "Usage & Billing",
    blurb: "Measurement to charge — what was consumed, what it was priced at, what was billed." },
  { id: "financial", name: "Financials & Payments",
    blurb: "Money in and money owed: transactions, payments, tenders and the general ledger." },
  { id: "credit", name: "Credit & Collections",
    blurb: "Arrears, collection processes, pay plans and the customers behind them." },
  { id: "field", name: "Field & Operations",
    blurb: "Field activities, device events, exceptions, to-dos and overnight batch." },
];

const q = (o) => o;

export const QUESTIONS = [
  // ------------------------------------------------------------------ Customer & Account
  q({
    id: "accounts-by-class",
    process: "customer", workstream: "Customer Information",
    kind: "count",
    title: "How many accounts, by customer class?",
    why: "The denominator behind almost every other number. A class with a handful of accounts is usually a configuration left over from implementation.",
    canvas: "rpt_customer_account",
    axis: "Customer Class", value: "Accounts",
    sql: `select coalesce("Customer Class", "Customer Class Code", '(unset)') as "Customer Class",
                 count(*)::bigint as "Accounts",
                 count(*) filter (where "Active SA Count" > 0)::bigint as "With Active Service",
                 round(avg("SA Count")::numeric, 1) as "Avg Agreements"
          from reporting.rpt_customer_account
          group by 1 order by 2 desc`,
  }),
  q({
    id: "self-service-adoption",
    process: "customer", workstream: "Customer Information",
    kind: "distribution",
    title: "What is self-service adoption, by customer class?",
    why: "Self-service take-up is the cheapest lever on contact volume. Splitting by class shows where a campaign would land.",
    canvas: "rpt_customer_account",
    axis: "Customer Class", value: "Self-Service %",
    sql: `select coalesce("Customer Class", '(unset)') as "Customer Class",
                 count(*)::bigint as "Accounts",
                 count(*) filter (where "Self-Service Enabled")::bigint as "Self-Service",
                 round(100.0 * count(*) filter (where "Self-Service Enabled") / nullif(count(*),0), 1) as "Self-Service %",
                 count(*) filter (where "Any Person Receives Notifications")::bigint as "Opted Into Notifications"
          from reporting.rpt_customer_account
          group by 1 order by 2 desc`,
  }),
  q({
    id: "accounts-no-email",
    process: "customer", workstream: "Customer Contact",
    kind: "count",
    title: "How many accounts have no email address on file?",
    why: "An account with no email cannot be sent a bill-ready notification, so every one of them is a paper bill and a phone call waiting to happen.",
    canvas: "rpt_customer_account",
    axis: "Has Email On File", value: "Accounts",
    sql: `select case when "Main Customer Email" is not null then 'Has email'
                     when "Main Customer Phone" is not null then 'Phone only'
                     else 'No email or phone' end as "Reachability",
                 count(*)::bigint as "Accounts",
                 count(*) filter (where "Self-Service Enabled")::bigint as "Self-Service Enabled"
          from reporting.rpt_customer_account
          group by 1 order by 2 desc`,
  }),
  q({
    id: "notification-outcomes",
    process: "customer", workstream: "Customer Notification",
    kind: "distribution",
    title: "Did the customer actually get told? Notification outcomes by type.",
    why: "A cancelled notification is normal; a RATE of cancellation is a signal. Errors are customers who were never reached at all.",
    canvas: "rpt_customer_notification",
    axis: "Task Type", value: "Total",
    // COMPLETE / ERROR / CANCEL are base-product BO statuses, safe to test on any client.
    sql: `select coalesce("Task Type", "Task Type Code") as "Task Type",
                 count(*)::bigint as "Total",
                 count(*) filter (where "Is Complete")::bigint as "Complete",
                 count(*) filter (where "Is Error")::bigint as "Errored",
                 count(*) filter (where "Is Cancelled")::bigint as "Cancelled",
                 count(*) filter (where "Is Outstanding")::bigint as "Outstanding",
                 round(100.0 * count(*) filter (where "Is Error") / nullif(count(*),0), 1) as "Error %"
          from reporting.rpt_customer_notification
          group by 1 order by 2 desc`,
  }),
  q({
    id: "notifications-stuck",
    process: "customer", workstream: "Customer Notification",
    kind: "outlier",
    title: "Which notifications have been outstanding longest?",
    why: "A task pending for weeks is not pending, it is stuck. These are the ones a person has to look at.",
    canvas: "rpt_customer_notification",
    axis: "Task Type", value: "Days Outstanding",
    sql: `select "Service Task ID", coalesce("Task Type", "Task Type Code") as "Task Type",
                 "Days Outstanding", "Task Status Code" as "Status",
                 "Account ID", "Main Customer Name"
          from reporting.rpt_customer_notification
          where "Is Outstanding" and "Days Outstanding" is not null
          order by "Days Outstanding" desc nulls last
          limit 50`,
  }),

  // ------------------------------------------------------------------ Metering & Assets
  q({
    id: "device-estate",
    process: "meter", workstream: "Device Management",
    kind: "count",
    title: "What is the device estate, by type and attachment?",
    why: "Meters reach a service point through an install event; communication modules through service point equipment. Counting only one route hides half the estate.",
    canvas: "rpt_device_asset",
    axis: "Device Type", value: "Devices",
    sql: `select coalesce("Device Type", "Device Type Code") as "Device Type",
                 count(*)::bigint as "Devices",
                 count(*) filter (where "Attachment Path" = 'Metered install')::bigint as "Metered Install",
                 count(*) filter (where "Attachment Path" = 'Equipment')::bigint as "Equipment",
                 count(*) filter (where "Attachment Path" is null)::bigint as "Not Attached",
                 count(*) filter (where "Is Retired")::bigint as "Retired"
          from reporting.rpt_device_asset
          group by 1 order by 2 desc`,
  }),
  q({
    id: "asset-disposition",
    process: "meter", workstream: "Asset Management",
    kind: "distribution",
    title: "Where is the physical estate sitting?",
    why: "Disposition is the asset-side status: installed, in store, in receipt, retired. In-store stock that never moves is capital doing nothing.",
    canvas: "rpt_device_asset",
    axis: "Asset Disposition Code", value: "Devices",
    sql: `select coalesce("Asset Disposition Code", '(no placement)') as "Asset Disposition Code",
                 count(*)::bigint as "Devices",
                 count(distinct "Asset Type Code")::bigint as "Asset Types",
                 round(sum("Replacement Cost")::numeric, 2) as "Replacement Cost"
          from reporting.rpt_device_asset
          group by 1 order by 2 desc`,
  }),
  q({
    id: "meters-not-registered",
    process: "meter", workstream: "Device Management",
    kind: "outlier",
    title: "Which installed meters never registered with the head-end?",
    why: "An installed meter the network has never heard from is an AMI rollout failure. It bills on estimates until someone visits it.",
    canvas: "rpt_device_asset",
    axis: "Device Type", value: "Devices",
    sql: `select coalesce("Device Type", "Device Type Code") as "Device Type",
                 coalesce("Head-End Registration Status Code", '(none)') as "Head-End Status",
                 count(*)::bigint as "Devices"
          from reporting.rpt_device_asset
          where "Is Attached To Service Point"
          group by 1, 2 order by 3 desc`,
  }),
  q({
    id: "service-off-but-installed",
    process: "meter", workstream: "Service Point",
    kind: "count",
    title: "How many premises have a meter installed but service switched off?",
    why: "Present but disconnected. A meter can be asset-INSTALLED and install-OFF at the same time, and only one of those two statuses says whether anyone is being served.",
    canvas: "rpt_premise_sp",
    axis: "Installed But Switched Off", value: "Service Points",
    sql: `select case when "Service Is On" then 'On'
                     when "Installed But Switched Off" then 'Installed, switched off'
                     when "Has Installed Device" then 'Installed, other status'
                     else 'No device installed' end as "Service State",
                 count(*)::bigint as "Service Points",
                 count(distinct "Premise ID")::bigint as "Premises",
                 sum("Active SA Count")::bigint as "Active Agreements"
          from reporting.rpt_premise_sp
          group by 1 order by 2 desc`,
  }),
  q({
    id: "usage-no-active-sa",
    process: "meter", workstream: "Service Point",
    kind: "outlier",
    title: "Which service points are recording usage with no active agreement?",
    why: "Consumption nobody is being billed for. Either service started without an agreement or one was stopped while the meter kept running.",
    canvas: "rpt_premise_sp",
    axis: "Premise Address", value: "Unbilled Usage Transaction Count (Point)",
    sql: `select "Service Point ID", "Premise ID", "Premise Address", "City",
                 "Unbilled Usage Transaction Count (Point)", "Latest Unbilled Usage Through",
                 "Meter Badge Number", "Device Type"
          from reporting.rpt_premise_sp
          where "Has Usage With No Active SA"
          order by "Unbilled Usage Transaction Count (Point)" desc nulls last
          limit 50`,
  }),

  // ------------------------------------------------------------------ Usage & Billing
  q({
    id: "billed-revenue-by-type",
    process: "usage", workstream: "Billing",
    kind: "total",
    // Declared for the portal, which builds its own governed query and never runs the
    // SQL below. Without these the tile showed the unrestricted total under a caption
    // promising frozen revenue only, and ranked Payment Arrangement first.
    filters: [{"field": "Is Frozen", "op": "eq", "value": true},
              {"field": "Is Cancelled", "op": "eq", "value": false},
              {"field": "Is Revenue Bearing", "op": "eq", "value": true}],
    title: "What revenue was billed, by service agreement type?",
    why: "Billed revenue is FROZEN segments only. Unfrozen segments are still in flight and cancelled ones were reversed; counting either inflates the total. Not every billed line is revenue either: a payment arrangement is billed but only reschedules debt, so it is split out here rather than silently dropped.",
    canvas: "rpt_bill_segment",
    axis: "SA Type", value: "Billed Amount",
    sql: `select coalesce("SA Type", "SA Type Code") as "SA Type",
                 coalesce("Utility Type", '(unset)') as "Utility Type",
                 case when "Is Revenue Bearing" then 'Revenue'
                      else coalesce("SA Special Role", 'Not revenue') end as "Revenue Or Not",
                 count(*)::bigint as "Segments",
                 round(sum("Billed Amount")::numeric, 2) as "Billed Amount",
                 round(avg("Billed Amount")::numeric, 2) as "Average Segment",
                 round(sum("Billed Usage")::numeric, 2) as "Billed Usage"
          from reporting.rpt_bill_segment
          where "Is Frozen" and not "Is Cancelled"
          group by 1, 2, 3 order by 5 desc nulls last`,
  }),
  q({
    id: "billed-not-revenue",
    process: "financial", workstream: "Revenue",
    kind: "total", unit: "money",
    filters: [{"field": "Is Frozen", "op": "eq", "value": true},
              {"field": "Is Cancelled", "op": "eq", "value": false},
              {"field": "Is Revenue Bearing", "op": "eq", "value": false}],
    title: "How much of what we bill is not revenue?",
    why: "Payment arrangements, cash deposits, write-offs, loans and non-billed budgets all put money on a bill without earning any. A payment arrangement reschedules debt that was already billed on another agreement, so counting it as revenue books the same money twice; a deposit is the customer's own money, held as security and refundable. This is the amount a revenue report has to exclude, and the reason it excludes it.",
    canvas: "rpt_bill_segment",
    axis: "SA Special Role", value: "Billed Amount",
    sql: `select coalesce("SA Special Role", '(no special role)') as "SA Special Role",
                 coalesce("SA Type", "SA Type Code") as "SA Type",
                 count(*)::bigint as "Segments",
                 round(sum("Billed Amount")::numeric, 2) as "Billed Amount"
          from reporting.rpt_bill_segment
          where "Is Frozen" and not "Is Cancelled" and not "Is Revenue Bearing"
          group by 1, 2 order by 4 desc nulls last`,
  }),
  q({
    id: "charge-basis-split",
    process: "usage", workstream: "Billing",
    kind: "distribution",
    title: "How does a bill split between consumption, demand, service quantity and flat charges?",
    why: "The charge basis split is what tells you whether a rate is volumetric or fixed. It is also the split that goes wrong first when a rate is reconfigured.",
    canvas: "rpt_bill_segment",
    axis: "SA Type", value: "Consumption Charge Amount",
    sql: `select coalesce("SA Type", "SA Type Code") as "SA Type",
                 round(sum("Consumption Charge Amount")::numeric, 2) as "Consumption Charge Amount",
                 round(sum("Demand Charge Amount")::numeric, 2) as "Demand",
                 round(sum("Service Quantity Charge Amount")::numeric, 2) as "Service Quantity",
                 round(sum("Flat Charge Amount")::numeric, 2) as "Flat",
                 round(sum("Unclassified Unit Charge Amount")::numeric, 2) as "Unclassified",
                 round(sum("Billed Amount")::numeric, 2) as "Total"
          from reporting.rpt_bill_segment
          where "Is Frozen" and not "Is Cancelled"
          group by 1 order by 7 desc nulls last`,
  }),
  q({
    id: "estimated-billing",
    process: "usage", workstream: "Billing",
    kind: "distribution",
    title: "How much billing is running on estimates?",
    why: "An estimated bill is a read that did not arrive. A rising rate here is a metering problem showing up as a billing number.",
    canvas: "rpt_bill_segment",
    axis: "SA Type", value: "Estimated %",
    sql: `select coalesce("SA Type", "SA Type Code") as "SA Type",
                 count(*)::bigint as "Segments",
                 count(*) filter (where "Estimated Segment")::bigint as "Estimated",
                 round(100.0 * count(*) filter (where "Estimated Segment") / nullif(count(*),0), 1) as "Estimated %",
                 round(sum("Billed Amount") filter (where "Estimated Segment")::numeric, 2) as "Estimated Amount"
          from reporting.rpt_bill_segment
          where "Is Frozen"
          group by 1 order by 4 desc nulls last`,
  }),
  q({
    id: "rebilled-segments",
    // Declared for the portal's governed query (rebilled segments only: without it every never-cancelled segment drew a null bar; demo25, 2026-09-04).
    filters: [{"field": "Is Rebilled", "op": "eq", "value": true}],
    process: "usage", workstream: "Billing",
    kind: "count",
    title: "How much is being rebilled, and why?",
    why: "Every rebill is a bill the utility got wrong the first time. The cancel reason is where the pattern is.",
    canvas: "rpt_bill_segment",
    axis: "Cancel Reason Code", value: "Segments",
    sql: `select coalesce("Cancel Reason Code", '(none given)') as "Cancel Reason Code",
                 count(*)::bigint as "Segments",
                 count(distinct "Account ID")::bigint as "Accounts",
                 round(sum(abs("Billed Amount"))::numeric, 2) as "Absolute Amount"
          from reporting.rpt_bill_segment
          where "Is Cancelled"
          group by 1 order by 2 desc`,
  }),
  q({
    id: "highest-bills",
    process: "usage", workstream: "Billing",
    kind: "outlier",
    title: "Which bill segments are the largest?",
    why: "The top of the distribution is where billing errors surface first, and where a high-bill complaint is about to come from.",
    canvas: "rpt_bill_segment",
    axis: "Main Customer Name", value: "Billed Amount",
    sql: `select "Bill Segment ID", "Bill Date", "Billed Amount", "Billed Usage",
                 "Billed Usage UOM" as "UOM", "Average Price Per Unit",
                 coalesce("SA Type", "SA Type Code") as "SA Type",
                 "Account ID", "Main Customer Name", "Premise Address"
          from reporting.rpt_bill_segment
          where "Is Frozen" and not "Is Cancelled" and "Billed Amount" is not null
          order by "Billed Amount" desc
          limit 50`,
  }),
  q({
    id: "price-per-unit-outliers",
    process: "usage", workstream: "Rates",
    kind: "outlier",
    title: "Where is the price per unit furthest from its rate's norm?",
    why: "A segment priced far from every other segment on the same rate is either a proration, a rate change mid-period, or a mistake. All three are worth seeing.",
    canvas: "rpt_bill_segment",
    axis: "Sole Rate Schedule Code", value: "Average Price Per Unit",
    sql: `with priced as (
            select "Bill Segment ID", "Bill Date", "Sole Rate Schedule Code" as rs,
                   "Average Price Per Unit" as ppu, "Billed Amount", "Billed Usage",
                   "Account ID", "Main Customer Name"
            from reporting.rpt_bill_segment
            where "Is Frozen" and not "Is Cancelled"
              and "Sole Rate Schedule Code" is not null
              and "Average Price Per Unit" is not null
          ), stats as (
            select rs, avg(ppu) as mean, stddev_samp(ppu) as sd, count(*) as n
            from priced group by rs having count(*) >= 5
          )
          select p."Bill Segment ID", p.rs as "Sole Rate Schedule Code", p."Bill Date",
                 round(p.ppu::numeric, 4) as "Average Price Per Unit",
                 round(s.mean::numeric, 4) as "Rate Mean",
                 round((abs(p.ppu - s.mean) / nullif(s.sd,0))::numeric, 2) as "Std Devs From Mean",
                 p."Billed Amount", p."Billed Usage", p."Main Customer Name"
          from priced p join stats s on s.rs = p.rs
          where s.sd > 0 and abs(p.ppu - s.mean) / s.sd >= 2
          order by abs(p.ppu - s.mean) / s.sd desc
          limit 50`,
  }),
  q({
    id: "unbilled-revenue",
    process: "usage", workstream: "Billing",
    kind: "outlier",
    title: "What service is going unbilled?",
    why: "Revenue earned and not invoiced. A stopped agreement awaiting a final bill is the expensive kind — the customer has gone.",
    canvas: "rpt_unbilled_revenue",
    axis: "SA Type", value: "Agreements",
    sql: `select coalesce("SA Type", "SA Type Code") as "SA Type",
                 count(*)::bigint as "Agreements",
                 count(*) filter (where "Is Stale Unbilled")::bigint as "Stale",
                 count(*) filter (where "Has Never Been Billed")::bigint as "Never Billed",
                 count(*) filter (where "Is Stopped Awaiting Final Bill")::bigint as "Awaiting Final Bill",
                 max("Days Since Last Billed")::bigint as "Worst Days Unbilled",
                 sum("Unbilled Usage Transaction Count")::bigint as "Unbilled Usage Txns"
          from reporting.rpt_unbilled_revenue
          group by 1 order by 2 desc`,
  }),
  q({
    id: "rate-configuration-shape",
    process: "usage", workstream: "Rates",
    kind: "count",
    title: "How complicated is each rate?",
    why: "Rule count is the honest measure of a rate's complexity, and complexity is what makes a rate change risky. Conditional rules are the ones that only apply sometimes.",
    canvas: "rpt_rate_configuration",
    axis: "Rate Schedule Code", value: "Rules",
    sql: `select "Rate Schedule Code",
                 max("Rate Schedule") as "Rate Schedule",
                 max("Service Type Code") as "Service Type Code",
                 count(distinct "Calculation Group Code")::bigint as "Groups",
                 count(distinct "Calculation Rule Code")::bigint as "Rules",
                 count(*) filter (where "Is Conditional")::bigint as "Conditional Rules",
                 count(*) filter (where "Has Nested Group")::bigint as "Nesting Rules",
                 count(distinct "Bill Factor Code")::bigint as "Distinct Prices"
          from reporting.rpt_rate_configuration
          group by 1 order by 5 desc`,
  }),

  // ------------------------------------------------------------------ Financials
  q({
    id: "financial-position",
    process: "financial", workstream: "Financial Transactions",
    kind: "total",
    title: "What is the financial position, by transaction type?",
    why: "Every movement of money in C2M is a financial transaction. Splitting by type separates what was charged from what was paid from what was reversed.",
    canvas: "rpt_financial_txn",
    axis: "FT Type", value: "Current Amount",
    sql: `select coalesce("FT Type", "FT Type Code") as "FT Type",
                 count(*)::bigint as "Transactions",
                 round(sum("Current Amount")::numeric, 2) as "Current Amount",
                 round(sum("Total Amount (Payoff)")::numeric, 2) as "Payoff Amount",
                 count(*) filter (where "Payoff Differs From Current")::bigint as "Payoff Differs"
          from reporting.rpt_financial_txn
          where "Is Frozen"
          group by 1 order by 3 desc nulls last`,
  }),
  q({
    id: "payments-by-tender",
    process: "financial", workstream: "Payments",
    kind: "distribution",
    title: "How are customers paying?",
    why: "Tender mix drives cashiering cost. A channel that is growing tells you where to invest, and one that is shrinking tells you what to retire.",
    canvas: "rpt_payment_tender",
    axis: "Tender Type", value: "Tender Amount",
    sql: `select coalesce("Tender Type", "Tender Type Code") as "Tender Type",
                 count(*)::bigint as "Tenders",
                 round(sum("Tender Amount")::numeric, 2) as "Tender Amount",
                 round(avg("Tender Amount")::numeric, 2) as "Average Tender",
                 count(*) filter (where "Is Cancelled")::bigint as "Cancelled"
          from reporting.rpt_payment_tender
          group by 1 order by 3 desc nulls last`,
  }),
  q({
    id: "unbalanced-tender-controls",
    process: "financial", workstream: "Cashiering",
    kind: "outlier",
    title: "Which tender controls have not been balanced?",
    why: "An unbalanced tender control is cash the utility cannot yet account for. Days unbalanced is the aging on that.",
    canvas: "rpt_tender_control",
    axis: "Tender Source", value: "Days Unbalanced",
    sql: `select "Tender Control ID", coalesce("Tender Source", "Tender Source Code") as "Tender Source",
                 "Tender Control Status", "Days Unbalanced",
                 "Start Balance", "End Balance", "Operator User ID", "Created Date/Time"
          from reporting.rpt_tender_control
          where not "Is Balanced"
          order by "Days Unbalanced" desc nulls last
          limit 50`,
  }),
  q({
    id: "gl-not-extracted",
    process: "financial", workstream: "General Ledger",
    kind: "count",
    title: "How much has not yet reached the general ledger?",
    why: "Financial transactions post to the GL on a schedule. Anything sitting unextracted is a reconciliation difference between C2M and the finance system.",
    canvas: "rpt_gl",
    axis: "GL Distribution Status", value: "GL Amount",
    sql: `select coalesce("GL Distribution Status", "GL Distribution Status Code", '(unset)') as "GL Distribution Status",
                 count(*)::bigint as "GL Lines",
                 count(distinct "FT ID")::bigint as "Transactions",
                 round(sum("GL Amount")::numeric, 2) as "GL Amount",
                 count(*) filter (where "Is Extracted to GL")::bigint as "Extracted"
          from reporting.rpt_gl
          group by 1 order by 4 desc nulls last`,
  }),
  q({
    id: "revenue-reconciliation",
    process: "financial", workstream: "General Ledger",
    kind: "outlier",
    title: "Where does calculated revenue disagree with the financial transactions?",
    why: "The calc lines say what the rate produced; the financial transactions say what was posted. They should agree to the cent, and where they do not there is a real variance.",
    canvas: "rpt_revenue_reconciliation",
    axis: "Bill ID", value: "Variance",
    sql: `select "Bill ID", "Is Budget Billed",
                 round("Calc Line Revenue"::numeric, 2) as "Calc Line Revenue",
                 round("FT Bill Segment Amount"::numeric, 2) as "FT Bill Segment Amount",
                 round("FT Cancellation Amount"::numeric, 2) as "FT Cancellation Amount",
                 round("FT Net of Cancellations"::numeric, 2) as "FT Net of Cancellations",
                 round("Variance"::numeric, 2) as "Variance"
          from reporting.rpt_revenue_reconciliation
          where abs(coalesce("Variance", 0)) > 0.005
          order by abs("Variance") desc
          limit 50`,
  }),

  // ------------------------------------------------------------------ Credit & Collections
  q({
    id: "arrears-by-band",
    process: "credit", workstream: "Collections",
    kind: "total",
    title: "What is owed, and how old is it?",
    why: "Aged debt is the collections work queue and the bad-debt provision at the same time. The oldest band is the one that stops being collectable.",
    canvas: "rpt_sa_aged_balance",
    axis: "Oldest Debt Band", value: "Total Balance",
    // the wide canvas IS the debt table (one row per SA, a column per bucket --
    // the CMS_SA_SNAPSHOT shape); band rows here are unpivoted from its columns
    sql: `select b."Aging Band",
                 count(distinct s."Service Agreement ID") filter (where b.amt > 0)::bigint as "Agreements",
                 count(distinct s."Account ID") filter (where b.amt > 0)::bigint as "Accounts",
                 round(sum(b.amt)::numeric, 2) as "Unpaid Amount"
          from reporting.rpt_sa_aged_balance s
          cross join lateral (values
            ('1) 0-30',   s."Arrears 0-30 Days"),
            ('2) 31-60',  s."Arrears 31-60 Days"),
            ('3) 61-90',  s."Arrears 61-90 Days"),
            ('4) 91-120', s."Arrears 91-120 Days"),
            ('5) 121+',   s."Arrears 121+ Days")) as b("Aging Band", amt)
          group by 1 order by 1`,
  }),
  q({
    id: "arrears-by-class",
    process: "credit", workstream: "Collections",
    kind: "distribution",
    title: "Which customer classes carry the arrears?",
    why: "Total arrears is one number; who owes it decides which collection approach applies. Commercial debt and residential debt are not worked the same way.",
    canvas: "rpt_sa_aged_balance",
    axis: "Customer Class", value: "Past Due Amount",
    sql: `select coalesce("Customer Class", '(unset)') as "Customer Class",
                 coalesce("Collection Class", '(unset)') as "Collection Class",
                 count(distinct "Account ID")::bigint as "Accounts",
                 round(sum("Past Due Amount")::numeric, 2) as "Past Due Amount",
                 round(avg("Total Balance")::numeric, 2) as "Average SA Balance"
          from reporting.rpt_sa_aged_balance
          group by 1, 2 order by 4 desc nulls last`,
  }),
  q({
    id: "largest-debtors",
    process: "credit", workstream: "Collections",
    kind: "outlier",
    title: "Who owes the most?",
    why: "Collections effort follows the money. The top of this list is worth a phone call before it is worth a process.",
    canvas: "rpt_customer_account",
    axis: "Main Customer Name", value: "Total Arrears",
    sql: `select "Account ID", "Main Customer Name", "Customer Class", "Collection Class",
                 round("Total Arrears"::numeric, 2) as "Total Arrears",
                 round("Arrears 120+ Days"::numeric, 2) as "120+ Days",
                 round("Current Balance"::numeric, 2) as "Current Balance",
                 "Is On Active Pay Plan", "Active SA Count"
          from reporting.rpt_customer_account
          where coalesce("Total Arrears", 0) > 0
          order by "Total Arrears" desc
          limit 50`,
  }),
  q({
    id: "collection-effectiveness",
    process: "credit", workstream: "Collections",
    kind: "distribution",
    title: "Are collection processes actually collecting?",
    why: "A process that runs to completion without reducing arrears has cost money and recovered nothing. Percent of arrears collected is the measure that matters.",
    canvas: "rpt_debt_process",
    axis: "Process Template", value: "Arrears Reduction",
    sql: `select coalesce("Process Template", '(unset)') as "Process Template",
                 "Process Type",
                 count(distinct "Process ID")::bigint as "Processes",
                 round(sum("Arrears Reduction")::numeric, 2) as "Arrears Reduction",
                 round(avg("% of Arrears Collected")::numeric, 1) as "Avg % Collected",
                 round(avg("Duration (Days)")::numeric, 1) as "Avg Days"
          from reporting.rpt_debt_process
          group by 1, 2 order by 4 desc nulls last`,
  }),
  q({
    id: "pay-plan-health",
    process: "credit", workstream: "Pay Plans",
    kind: "distribution",
    title: "Are customers keeping their pay plans?",
    why: "A broken pay plan is a customer who tried and could not. The kept-versus-broken split is the honest measure of whether the plans are set at affordable amounts.",
    canvas: "rpt_pay_plan",
    axis: "Pay Plan Type", value: "Plans",
    sql: `select coalesce("Pay Plan Type", "Pay Plan Type Code") as "Pay Plan Type",
                 count(*)::bigint as "Plans",
                 count(*) filter (where "Is Active")::bigint as "Active",
                 count(*) filter (where "Is Kept")::bigint as "Kept",
                 count(*) filter (where "Is Broken")::bigint as "Broken",
                 round(100.0 * count(*) filter (where "Is Broken") / nullif(count(*),0), 1) as "Broken %",
                 round(sum("Scheduled Total Amount")::numeric, 2) as "Scheduled Amount"
          from reporting.rpt_pay_plan
          group by 1 order by 2 desc`,
  }),

  // ------------------------------------------------------------------ Field & Operations
  q({
    id: "field-activity-backlog",
    process: "field", workstream: "Field Operations",
    kind: "count",
    title: "What is the field activity backlog, by type?",
    why: "Field work is the most expensive thing a utility does. Backlog by type shows which work is accumulating faster than the crews clear it.",
    canvas: "rpt_field_activity",
    axis: "Activity Type", value: "Activities",
    sql: `select coalesce("Activity Type", "Activity Type Code") as "Activity Type",
                 coalesce("Activity Status Code", '(unset)') as "Status",
                 count(*)::bigint as "Activities",
                 count(*) filter (where trim("Appointment Required") = 'Y')::bigint as "Appointment Required",
                 -- Number of Retries lands as text: CISADM stores it as a character
                 -- column and the canvas carries the source shape faithfully.
                 round(avg(nullif(trim("Number of Retries"),'')::numeric), 2) as "Avg Retries"
          from reporting.rpt_field_activity
          group by 1, 2 order by 3 desc`,
  }),
  q({
    id: "exceptions-open",
    process: "field", workstream: "Data Quality",
    kind: "outlier",
    title: "Which data exceptions are open longest?",
    why: "A VEE or usage exception blocks a read from becoming a bill. Days open is how long that revenue has been stuck.",
    canvas: "rpt_exception",
    axis: "Exception Type", value: "Days Open",
    sql: `select coalesce("Exception Type", "Exception Type Code") as "Exception Type",
                 "Exception Domain", coalesce("Severity", "Severity Code") as "Severity",
                 count(*)::bigint as "Open Exceptions",
                 max("Days Open")::bigint as "Worst Days Open",
                 round(avg("Days Open")::numeric, 1) as "Avg Days Open"
          from reporting.rpt_exception
          where "Is Open"
          group by 1, 2, 3 order by 4 desc`,
  }),
  q({
    id: "device-events",
    process: "field", workstream: "Device Events",
    kind: "distribution",
    title: "What are the meters reporting?",
    why: "Device events are the meter's own account of what happened to it — tamper, outage, reverse flow. The mix is an early warning the billing data will not give you.",
    canvas: "rpt_device_event",
    axis: "Event Type", value: "Events",
    sql: `select coalesce("Event Type", "Event Type Code") as "Event Type",
                 count(*)::bigint as "Events",
                 count(distinct "Device ID")::bigint as "Devices",
                 count(*) filter (where "Is Event Closed")::bigint as "Closed",
                 round(avg("Event Duration Minutes")::numeric, 1) as "Avg Duration (min)"
          from reporting.rpt_device_event
          group by 1 order by 2 desc`,
  }),
  q({
    id: "batch-failures",
    process: "field", workstream: "Batch Operations",
    kind: "outlier",
    title: "Which overnight batches failed or ran long?",
    why: "Batch is what makes bills exist. A failed billing batch is tomorrow's missed bill run, and a slow one is the reason the window is closing.",
    canvas: "rpt_batch",
    axis: "Batch Code", value: "Duration (min)",
    sql: `select "Batch Code", "Program", "Run Number",
                 coalesce("Run Status", "Run Status Code") as "Run Status",
                 "Start Time", "End Time", round("Duration (min)"::numeric, 1) as "Duration (min)"
          from reporting.rpt_batch
          order by ("Run Status Code" = '30') desc, "Duration (min)" desc nulls last
          limit 50`,
  }),
  q({
    id: "todo-backlog",
    process: "field", workstream: "Work Queues",
    kind: "count",
    title: "What is sitting in the to-do queues?",
    why: "A to-do is work the system could not finish on its own. The oldest open entries are the exceptions nobody owns.",
    canvas: "rpt_todo",
    axis: "To Do Type", value: "Open",
    sql: `select coalesce("To Do Type", "To Do Type Code") as "To Do Type",
                 count(*)::bigint as "Entries",
                 count(*) filter (where not "Is Complete")::bigint as "Open",
                 round(max("Hours Open") filter (where not "Is Complete")::numeric, 1) as "Worst Hours Open",
                 count(distinct "Assigned User")::bigint as "Assigned Users"
          from reporting.rpt_todo
          group by 1 order by 3 desc`,
  }),
  // ============================================================ INDUSTRY KPI SET
  // Benchmarks below are the published meter-to-cash and MDM targets utilities are
  // measured against -- billing accuracy above 95%, exception rate under 10%, write-off
  // under 1% of billed revenue, billing cycle under 30 days. They are stated as targets,
  // not thresholds the SQL filters on, because a client whose number is outside the
  // benchmark still needs to see its own number.

  q({
    id: "kpi-billing-accuracy",
    process: "usage", workstream: "Billing Performance",
    kind: "distribution", unit: "percent", target: "above 95%",
    title: "Billing accuracy rate — what share of bills were not rebilled?",
    why: "The headline meter-to-cash KPI. Every cancelled and rebilled segment is a bill the utility got wrong and had to redo, and the industry target is above 95% right first time.",
    canvas: "rpt_bill_segment",
    axis: "Bill Cycle", value: "Accuracy %",
    sql: `select coalesce("Bill Cycle", "Bill Cycle Code", '(unset)') as "Bill Cycle",
                 count(*)::bigint as "Segments",
                 count(*) filter (where "Is Cancelled" or "Is Rebilled")::bigint as "Rebilled or Cancelled",
                 round(100.0 * (count(*) - count(*) filter (where "Is Cancelled" or "Is Rebilled"))
                       / nullif(count(*),0), 2) as "Accuracy %"
          from reporting.rpt_bill_segment
          group by 1 order by 2 desc`,
  }),
  q({
    id: "kpi-exception-rate",
    process: "field", workstream: "Data Quality",
    kind: "distribution", unit: "percent", target: "under 10%",
    title: "Exception rate — what share of usage is stuck behind an exception?",
    why: "An exception blocks a read from becoming a bill. The MDM benchmark is under 10%; above that the exception queue grows faster than anyone clears it and the billing window starts closing.",
    canvas: "rpt_exception",
    axis: "Exception Domain", value: "Open",
    sql: `select "Exception Domain",
                 count(*)::bigint as "Exceptions",
                 count(*) filter (where "Is Open")::bigint as "Open",
                 round(100.0 * count(*) filter (where "Is Open") / nullif(count(*),0), 1) as "Still Open %",
                 round(avg("Days Open")::numeric, 1) as "Avg Days Open",
                 max("Days Open")::bigint as "Worst Days Open"
          from reporting.rpt_exception
          group by 1 order by 3 desc`,
  }),
  q({
    id: "kpi-estimation-rate",
    process: "usage", workstream: "Billing Performance",
    kind: "distribution", unit: "percent", target: "as low as possible",
    title: "Estimation rate — how much revenue is billed on estimates?",
    why: "Estimated bills generate disputes, and disputes generate calls. A rising estimation rate is an AMI reliability problem arriving as a customer-service cost.",
    canvas: "rpt_bill_segment",
    axis: "Bill Cycle", value: "Estimated %",
    sql: `select coalesce("Bill Cycle", "Bill Cycle Code", '(unset)') as "Bill Cycle",
                 count(*)::bigint as "Frozen Segments",
                 count(*) filter (where "Estimated Segment")::bigint as "Estimated",
                 round(100.0 * count(*) filter (where "Estimated Segment") / nullif(count(*),0), 2) as "Estimated %",
                 round(sum("Billed Amount") filter (where "Estimated Segment")::numeric, 2) as "Estimated Revenue"
          from reporting.rpt_bill_segment
          where "Is Frozen"
          group by 1 order by 4 desc nulls last`,
  }),
  q({
    id: "kpi-write-off-exposure",
    process: "credit", workstream: "Credit Risk",
    kind: "total", unit: "money", target: "under 1% of billed revenue",
    title: "Write-off exposure — how much debt is past the point of collection?",
    why: "Debt beyond 120 days is the bad-debt provision in waiting. The benchmark is under 1% of billed revenue; this is the number a finance director asks for first.",
    canvas: "rpt_customer_account",
    axis: "Customer Class", value: "120+ Days",
    sql: `select coalesce("Customer Class", '(unset)') as "Customer Class",
                 count(*) filter (where coalesce("Arrears 120+ Days",0) > 0)::bigint as "Accounts At Risk",
                 round(sum("Arrears 120+ Days")::numeric, 2) as "120+ Days",
                 round(sum("Total Arrears")::numeric, 2) as "Total Arrears",
                 round(100.0 * sum("Arrears 120+ Days") / nullif(sum("Total Arrears"),0), 1) as "% Of Arrears Beyond 120d"
          from reporting.rpt_customer_account
          group by 1 order by 3 desc nulls last`,
  }),
  q({
    id: "kpi-days-unbilled",
    process: "usage", workstream: "Billing Performance",
    kind: "outlier", unit: "days", target: "billing cycle under 30 days",
    title: "Billing cycle health — which agreements are furthest past their window?",
    why: "The benchmark is a billing cycle under 30 days. Every day past that is revenue earned and not invoiced, and the tail is where the real money sits.",
    canvas: "rpt_unbilled_revenue",
    axis: "SA Type", value: "Days Since Last Billed",
    sql: `select "Service Agreement ID", coalesce("SA Type", "SA Type Code") as "SA Type",
                 "Days Since Last Billed", "Last Billed Through Date",
                 "Unbilled Usage Transaction Count" as "Unbilled Usage Txns",
                 "Is Stopped Awaiting Final Bill" as "Awaiting Final Bill",
                 "Account ID", "Main Customer Name"
          from reporting.rpt_unbilled_revenue
          where "Days Since Last Billed" is not null
          order by "Days Since Last Billed" desc
          limit 50`,
  }),
  q({
    id: "kpi-first-time-fix",
    process: "field", workstream: "Field Performance",
    kind: "distribution", unit: "percent", target: "high is good",
    title: "First-time fix — which field work needed more than one visit?",
    why: "First-time fix rate is the field KPI that moves cost and satisfaction together. Retries are the inverse: every one is a truck sent twice for the same job.",
    canvas: "rpt_field_activity",
    axis: "Activity Type", value: "First-Time %",
    sql: `select coalesce("Activity Type", "Activity Type Code") as "Activity Type",
                 count(*)::bigint as "Activities",
                 count(*) filter (where coalesce(nullif(trim("Number of Retries"),'')::numeric,0) = 0)::bigint as "No Retry",
                 count(*) filter (where coalesce(nullif(trim("Number of Retries"),'')::numeric,0) > 0)::bigint as "Retried",
                 round(100.0 * count(*) filter (where coalesce(nullif(trim("Number of Retries"),'')::numeric,0) = 0)
                       / nullif(count(*),0), 1) as "First-Time %"
          from reporting.rpt_field_activity
          group by 1 order by 2 desc`,
  }),
  q({
    id: "kpi-call-deflection",
    process: "customer", workstream: "Channel & Deflection",
    kind: "distribution", unit: "percent", target: "high is good",
    title: "Channel mix — how much customer contact came through self-service?",
    why: "Call deflection is the cheapest lever a utility has on contact cost. The contact method is what says whether a customer solved it themselves or needed a person.",
    canvas: "rpt_customer_contact",
    axis: "Contact Method", value: "Contacts",
    sql: `select coalesce("Contact Method", "Contact Method Code", '(unset)') as "Contact Method",
                 coalesce("Contact Class", '(unset)') as "Contact Class",
                 count(*)::bigint as "Contacts",
                 count(distinct "Account ID")::bigint as "Accounts",
                 count(*) filter (where "Prints Letter")::bigint as "Generated A Letter"
          from reporting.rpt_customer_contact
          group by 1, 2 order by 3 desc`,
  }),

  // ============================================================ Customer, deeper
  q({
    id: "accounts-multi-utility",
    process: "customer", workstream: "Customer Information",
    kind: "distribution",
    title: "How many customers take more than one utility service?",
    why: "A multi-service customer is worth more and is harder to lose. It also means one billing failure affects several services at once.",
    canvas: "rpt_customer_account",
    axis: "Takes Multiple Utility Services", value: "Accounts",
    sql: `select "Utility Type Count"::text as "Services Taken",
                 count(*)::bigint as "Accounts",
                 round(avg("Total Balance")::numeric, 2) as "Avg Balance",
                 round(avg("SA Count")::numeric, 1) as "Avg Agreements",
                 round(sum("Total Paid")::numeric, 2) as "Total Paid"
          from reporting.rpt_customer_account
          -- order by the grouped expression, not the raw column: "Utility Type Count"
          -- is not in the GROUP BY once it has been cast to text for the label
          group by 1 order by 1`,
  }),
  q({
    id: "accounts-on-alerts",
    // Declared for the portal's governed query (accounts carrying an alert: without it the chart was one null bar of every account; demo25, 2026-09-04).
    filters: [{"field": "Has Alert", "op": "eq", "value": true}],
    process: "customer", workstream: "Customer Information",
    kind: "count",
    title: "Which accounts carry active alerts?",
    why: "An alert is a flag someone put on the account for a reason — a dispute, a vulnerability, a payment arrangement. It should be visible before anyone contacts the customer.",
    canvas: "rpt_customer_account",
    axis: "Active Alerts", value: "Accounts",
    sql: `select coalesce("Active Alerts", '(none)') as "Active Alerts",
                 count(*)::bigint as "Accounts",
                 round(sum("Total Arrears")::numeric, 2) as "Total Arrears",
                 count(*) filter (where "Is On Active Pay Plan")::bigint as "On Pay Plan"
          from reporting.rpt_customer_account
          where "Has Alert"
          group by 1 order by 2 desc`,
  }),
  q({
    id: "bill-routing-mix",
    process: "customer", workstream: "Channel & Deflection",
    kind: "distribution",
    title: "How are bills actually being delivered?",
    why: "Every paper bill has a print, post and handling cost. Route type is the only place that says which customers still get one.",
    canvas: "rpt_customer_account",
    axis: "Bill Route Types", value: "Accounts",
    sql: `select coalesce("Bill Route Types", '(unset)') as "Bill Route Types",
                 count(*)::bigint as "Accounts",
                 count(*) filter (where "Self-Service Enabled")::bigint as "Self-Service",
                 count(*) filter (where "Main Customer Email" is not null)::bigint as "Has Email"
          from reporting.rpt_customer_account
          group by 1 order by 2 desc`,
  }),
  q({
    id: "contact-reasons",
    process: "customer", workstream: "Customer Contact",
    kind: "distribution",
    title: "Why are customers getting in touch?",
    why: "Contact reason is the demand signal. The type that grows fastest is the process that is failing upstream.",
    canvas: "rpt_customer_contact",
    axis: "Contact Type", value: "Contacts",
    sql: `select coalesce("Contact Type", "Contact Type Code") as "Contact Type",
                 coalesce("Contact Class", '(unset)') as "Contact Class",
                 count(*)::bigint as "Contacts",
                 count(distinct "Account ID")::bigint as "Accounts"
          from reporting.rpt_customer_contact
          group by 1, 2 order by 3 desc`,
  }),
  q({
    id: "case-resolution-time",
    process: "customer", workstream: "Cases",
    kind: "distribution", unit: "days",
    title: "How long do cases take to close, by type?",
    why: "Case duration is the customer's experience of the utility's back office. The types that take longest are where the process, not the person, is slow.",
    canvas: "rpt_case",
    axis: "Case Type", value: "Avg Hours",
    sql: `select coalesce("Case Type", "Case Type Code") as "Case Type",
                 count(*)::bigint as "Cases",
                 count(*) filter (where "Is Closed")::bigint as "Closed",
                 count(*) filter (where not "Is Closed")::bigint as "Open",
                 round(avg("Case Duration Hours") filter (where "Is Closed")::numeric, 1) as "Avg Hours",
                 round(max("Case Duration Hours")::numeric, 1) as "Longest Hours"
          from reporting.rpt_case
          group by 1 order by 2 desc`,
  }),
  q({
    id: "notification-error-detail",
    process: "customer", workstream: "Customer Notification",
    kind: "outlier",
    title: "Which notification types fail most often?",
    why: "An errored notification is a customer who was never told. Ranking by error rate rather than error count stops the highest-volume type hiding a worse one.",
    canvas: "rpt_customer_notification",
    axis: "Task Type", value: "Error %",
    sql: `select coalesce("Task Type", "Task Type Code") as "Task Type",
                 "Task Class Code" as "Task Class",
                 count(*)::bigint as "Total",
                 count(*) filter (where "Is Error")::bigint as "Errored",
                 round(100.0 * count(*) filter (where "Is Error") / nullif(count(*),0), 1) as "Error %"
          from reporting.rpt_customer_notification
          group by 1, 2
          having count(*) >= 5
          order by 5 desc nulls last`,
  }),

  // ============================================================ Metering, deeper
  q({
    id: "read-coverage",
    process: "meter", workstream: "Meter Reading",
    kind: "distribution", unit: "percent",
    title: "Read quality — how many measurements are estimated or missing?",
    why: "A read that is estimated or missing is the root of an estimated bill and a future dispute. This is the number that should be watched daily during an AMI rollout.",
    canvas: "rpt_measurement",
    axis: "Device Type", value: "Estimated %",
    sql: `select coalesce("Device Type", "Device Type Code", '(unset)') as "Device Type",
                 count(*)::bigint as "Measurements",
                 count(*) filter (where "Is Regular Measurement")::bigint as "Regular",
                 count(*) filter (where "Is Estimated Measurement")::bigint as "Estimated",
                 count(*) filter (where "Is Missing Measurement")::bigint as "Missing",
                 round(100.0 * count(*) filter (where "Is Estimated Measurement") / nullif(count(*),0), 2) as "Estimated %"
          from reporting.rpt_measurement
          group by 1 order by 2 desc`,
  }),
  q({
    id: "meter-read-routes",
    process: "meter", workstream: "Meter Reading",
    kind: "count",
    title: "How is the meter reading workload distributed across routes?",
    why: "Route size is the daily workload of a reader or the daily load on the head-end. A route far larger than its neighbours is the one that runs late.",
    canvas: "rpt_premise_sp",
    axis: "Meter Read Route Code", value: "Service Points",
    sql: `select coalesce("Meter Read Cycle Code", '(unset)') as "Cycle",
                 coalesce("Meter Read Route Code", '(unset)') as "Meter Read Route Code",
                 count(*)::bigint as "Service Points",
                 count(*) filter (where "Has Installed Device")::bigint as "With Device",
                 count(*) filter (where "Service Is On")::bigint as "Service On"
          from reporting.rpt_premise_sp
          group by 1, 2 order by 3 desc`,
  }),
  q({
    id: "meter-age-replacement",
    process: "meter", workstream: "Asset Management",
    kind: "outlier", unit: "days",
    title: "Which meters are oldest relative to their useful life?",
    why: "A meter past its useful life drifts, and a drifting meter under-reads. This is the replacement programme's work queue and its capital case at once.",
    canvas: "rpt_device_asset",
    axis: "Device Type", value: "Years In Service",
    sql: `select "Device ID", "Meter Badge Number",
                 coalesce("Device Type", "Device Type Code") as "Device Type",
                 "Asset In Service Date",
                 round((current_date - "Asset In Service Date"::date) / 365.25, 1) as "Years In Service",
                 "Useful Life Years", "Replacement Cost", "Asset Condition Code",
                 "Premise Address"
          from reporting.rpt_device_asset
          where "Asset In Service Date" is not null
          order by "Asset In Service Date" asc
          limit 50`,
  }),
  q({
    id: "asset-replacement-value",
    process: "meter", workstream: "Asset Management",
    kind: "total", unit: "money",
    title: "What would it cost to replace the estate?",
    why: "Replacement cost by asset type is the capital plan. Splitting it by disposition shows how much of it is already sitting in a warehouse.",
    canvas: "rpt_device_asset",
    axis: "Asset Type", value: "Replacement Cost",
    sql: `select coalesce("Asset Type", "Asset Type Code", '(unset)') as "Asset Type",
                 count(*)::bigint as "Assets",
                 round(sum("Replacement Cost")::numeric, 2) as "Replacement Cost",
                 round(avg("Useful Life Years")::numeric, 1) as "Avg Useful Life",
                 count(*) filter (where "Asset Is In Service")::bigint as "In Service"
          from reporting.rpt_device_asset
          where "Asset ID" is not null
          group by 1 order by 3 desc nulls last`,
  }),
  q({
    id: "device-model-reliability",
    process: "meter", workstream: "Device Events",
    kind: "outlier",
    title: "Which meter models report the most events per device?",
    why: "Events per device normalises for fleet size, which is what turns a device-event count into a reliability comparison between models.",
    canvas: "rpt_device_event",
    axis: "Device Model", value: "Events Per Device",
    sql: `select coalesce("Device Model", "Device Model Code", '(unset)') as "Device Model",
                 coalesce("Manufacturer", '(unset)') as "Manufacturer",
                 count(*)::bigint as "Events",
                 count(distinct "Device ID")::bigint as "Devices",
                 round(count(*)::numeric / nullif(count(distinct "Device ID"),0), 2) as "Events Per Device"
          from reporting.rpt_device_event
          group by 1, 2
          having count(distinct "Device ID") >= 3
          order by 5 desc`,
  }),
  q({
    id: "service-on-off-churn",
    process: "meter", workstream: "Service Point",
    kind: "outlier",
    title: "Which service points are switched on and off most?",
    why: "Repeated on/off at one point is either a rental property turning over or a disconnection cycle. Both are expensive and both look the same in this list until you open one.",
    canvas: "rpt_on_off_history",
    axis: "Premise Address", value: "Events",
    sql: `select "Service Point ID", "Premise ID", "Premise Address",
                 count(*)::bigint as "Events",
                 count(*) filter (where "On/Off Event Code" = 'ON')::bigint as "Turn On",
                 count(*) filter (where "On/Off Event Code" = 'OFF')::bigint as "Turn Off",
                 max("Event Date/Time") as "Latest Event"
          from reporting.rpt_on_off_history
          group by 1, 2, 3
          having count(*) > 1
          order by 4 desc
          limit 50`,
  }),
  q({
    id: "life-support-premises",
    process: "meter", workstream: "Service Point",
    kind: "count",
    title: "Which premises are flagged life support or sensitive load?",
    why: "These customers must never be disconnected by an automated process. The flag exists so that every collections and field workflow can check it, which means someone has to know the list.",
    canvas: "rpt_premise_sp",
    axis: "Life Support / Sensitive Load", value: "Service Points",
    sql: `select coalesce("Life Support / Sensitive Load", "Life Support / Sensitive Load Code", '(none)') as "Life Support / Sensitive Load",
                 count(*)::bigint as "Service Points",
                 count(distinct "Premise ID")::bigint as "Premises",
                 count(*) filter (where "Service Is On")::bigint as "Service On",
                 sum("Active SA Count")::bigint as "Active Agreements"
          from reporting.rpt_premise_sp
          group by 1 order by 2 desc`,
  }),

  // ============================================================ Billing, deeper
  q({
    id: "revenue-by-cycle",
    process: "usage", workstream: "Billing",
    kind: "total", unit: "money",
    title: "What does each bill cycle bring in?",
    why: "Cycle is how the billing calendar is actually organised. A cycle whose revenue moves without its customer count moving is a rate or a read problem.",
    canvas: "rpt_bill_segment",
    axis: "Bill Cycle", value: "Billed Amount",
    sql: `select coalesce("Bill Cycle", "Bill Cycle Code", '(unset)') as "Bill Cycle",
                 count(distinct "Bill ID")::bigint as "Bills",
                 count(distinct "Account ID")::bigint as "Accounts",
                 round(sum("Billed Amount")::numeric, 2) as "Billed Amount",
                 round(avg("Billed Amount")::numeric, 2) as "Average Segment"
          from reporting.rpt_bill_segment
          where "Is Frozen" and not "Is Cancelled"
          group by 1 order by 4 desc nulls last`,
  }),
  q({
    id: "consumption-by-uom",
    process: "usage", workstream: "Usage",
    kind: "total",
    title: "How much was consumed, by unit of measure?",
    why: "Volume is the physical side of revenue. Splitting by unit keeps kWh, therms and gallons apart, which is the mistake that makes a usage total meaningless.",
    canvas: "rpt_billed_usage",
    axis: "Unit of Measure", value: "Billed Quantity",
    sql: `select coalesce("Unit of Measure", "Unit of Measure Code") as "Unit of Measure",
                 "UOM Class",
                 count(*)::bigint as "Lines",
                 round(sum("Billed Quantity")::numeric, 2) as "Billed Quantity",
                 round(avg("Billed Quantity")::numeric, 2) as "Average Per Line"
          from reporting.rpt_billed_usage
          where "Is Frozen" and not "Is Cancelled"
          group by 1, 2 order by 4 desc nulls last`,
  }),
  q({
    id: "usage-vs-read",
    process: "usage", workstream: "Usage",
    kind: "outlier",
    title: "Where does billed usage disagree with the meter reads behind it?",
    why: "Billed usage should be derivable from the reads. A gap means a correction, an override or an estimate — and the customer will notice before the utility does.",
    canvas: "rpt_bill_segment",
    axis: "Main Customer Name", value: "Billed Usage less Read Quantity",
    sql: `select "Bill Segment ID", "Bill Date",
                 "Billed Usage", "Read Quantity",
                 "Billed Usage less Read Quantity",
                 "Service Quantity Override", "Estimated Segment",
                 "Account ID", "Main Customer Name", "Premise Address"
          from reporting.rpt_bill_segment
          where "Billed Usage less Read Quantity" is not null
            and abs("Billed Usage less Read Quantity") > 0.001
          order by abs("Billed Usage less Read Quantity") desc
          limit 50`,
  }),
  q({
    id: "zero-and-negative-bills",
    process: "usage", workstream: "Billing",
    kind: "outlier", unit: "money",
    title: "Which bills came out zero or negative?",
    why: "A zero bill is usually a missing read; a negative one is a credit the customer will ring about. Neither should appear without a reason attached.",
    canvas: "rpt_bill_segment",
    axis: "Main Customer Name", value: "Billed Amount",
    sql: `select "Bill Segment ID", "Bill Date", "Billed Amount", "Billed Usage",
                 coalesce("SA Type", "SA Type Code") as "SA Type",
                 "Estimated Segment", "Cancel Reason Code",
                 "Account ID", "Main Customer Name", "Premise Address"
          from reporting.rpt_bill_segment
          where "Is Frozen" and not "Is Cancelled" and coalesce("Billed Amount", 0) <= 0
          order by "Billed Amount" asc nulls last
          limit 50`,
  }),
  q({
    id: "consumption-outliers",
    process: "usage", workstream: "Usage",
    kind: "outlier",
    title: "Which premises consumed far more than others on the same rate?",
    why: "High consumption is a leak, a theft, a faulty meter or a genuinely large customer. Comparing within a rate schedule is what separates the fourth from the first three.",
    canvas: "rpt_bill_segment",
    axis: "Premise Address", value: "Std Devs From Mean",
    sql: `with u as (
            select "Bill Segment ID", "Bill Date", "Sole Rate Schedule Code" as rs,
                   "Billed Usage" as qty, "Billed Usage UOM" as uom, "Billed Amount",
                   "Premise Address", "Main Customer Name", "Account ID"
            from reporting.rpt_bill_segment
            where "Is Frozen" and not "Is Cancelled"
              and "Sole Rate Schedule Code" is not null and "Billed Usage" is not null
          ), s as (
            select rs, avg(qty) m, stddev_samp(qty) sd from u group by rs having count(*) >= 5
          )
          select u."Bill Segment ID", u.rs as "Rate Schedule Code", u."Bill Date",
                 round(u.qty::numeric,2) as "Billed Usage", u.uom as "UOM",
                 round(s.m::numeric,2) as "Rate Mean",
                 round(((u.qty - s.m) / nullif(s.sd,0))::numeric, 2) as "Std Devs From Mean",
                 u."Billed Amount", u."Premise Address", u."Main Customer Name"
          from u join s on s.rs = u.rs
          where s.sd > 0 and (u.qty - s.m) / s.sd >= 2
          order by (u.qty - s.m) / s.sd desc
          limit 50`,
  }),
  q({
    id: "rate-migration",
    process: "usage", workstream: "Rates",
    kind: "count",
    title: "Who moved rate, and to what?",
    why: "A rate change alters a customer's bill without them doing anything. The volume of moves is a risk register for the next bill run.",
    canvas: "rpt_rate_schedule_history",
    axis: "Rate Schedule", value: "Changes",
    sql: `select coalesce("Previous Rate Schedule", "Previous Rate Schedule Code", '(initial)') as "From Rate",
                 coalesce("Rate Schedule", "Rate Schedule Code") as "Rate Schedule",
                 count(*)::bigint as "Changes",
                 count(distinct "Account ID")::bigint as "Accounts",
                 max("Effective Date") as "Latest Change"
          from reporting.rpt_rate_schedule_history
          where "Is Rate Change"
          group by 1, 2 order by 3 desc`,
  }),
  q({
    id: "bill-factor-prices",
    process: "usage", workstream: "Rates",
    kind: "count",
    title: "What prices are in force, and which are stale?",
    why: "A bill factor nobody has updated is charging last year's price. A bill factor no rule references is dead configuration that still looks live.",
    canvas: "rpt_bill_factor_price",
    axis: "Bill Factor Code", value: "Value",
    sql: `select "Bill Factor Code", "Varies By Char Type Code" as "Varies By",
                 "Characteristic Value", "Effective Date", "Value",
                 "Rate Schedule Count", "Calculation Rule Count", "Is Unreferenced"
          from reporting.rpt_bill_factor_price
          where "Is Current"
          order by "Rate Schedule Count" desc nulls last, "Bill Factor Code"
          limit 100`,
  }),
  q({
    id: "billable-charges",
    process: "usage", workstream: "Billing",
    kind: "distribution", unit: "money",
    title: "What is being charged outside the rate engine?",
    why: "A billable charge is a one-off the rate did not produce — a fee, a reconnection, a deposit. High volumes here mean manual work happening every cycle.",
    canvas: "rpt_billable_charge",
    axis: "Charge Template Code", value: "Charge Amount",
    sql: `select coalesce("Charge Template Code", '(none)') as "Charge Template Code",
                 count(*)::bigint as "Lines",
                 count(distinct "Billable Charge ID")::bigint as "Charges",
                 round(sum("Charge Amount")::numeric, 2) as "Charge Amount",
                 count(*) filter (where "Is Cancelled")::bigint as "Cancelled",
                 count(*) filter (where not "Is Billed")::bigint as "Not Yet Billed"
          from reporting.rpt_billable_charge
          group by 1 order by 4 desc nulls last`,
  }),

  // ============================================================ Financial, deeper
  q({
    id: "payment-timing",
    process: "financial", workstream: "Payments",
    kind: "distribution", unit: "days",
    title: "How promptly are bills being paid?",
    why: "Days between the bill and the payment is DSO in its rawest form. It is also the number that tells you whether a due-date change worked.",
    canvas: "rpt_customer_account",
    axis: "Customer Class", value: "Avg Days To Pay",
    sql: `select coalesce("Customer Class", '(unset)') as "Customer Class",
                 count(*) filter (where "Latest Payment Date" is not null)::bigint as "Accounts Paying",
                 round(avg("Latest Payment Date"::date - "Latest Bill Date"::date)
                       filter (where "Latest Payment Date" is not null
                               and "Latest Bill Date" is not null)::numeric, 1) as "Avg Days To Pay",
                 round(sum("Total Paid")::numeric, 2) as "Total Paid",
                 round(sum("Current Balance")::numeric, 2) as "Outstanding"
          from reporting.rpt_customer_account
          group by 1 order by 4 desc nulls last`,
  }),
  q({
    id: "cancelled-payments",
    // Declared for the portal's governed query (cancelled payments only: without it the not-cancelled majority drew a null bar; demo25, 2026-09-04).
    filters: [{"field": "Is Cancelled", "op": "eq", "value": true}],
    process: "financial", workstream: "Payments",
    kind: "outlier", unit: "money",
    title: "Which payments were cancelled, and why?",
    why: "A cancelled payment is usually a returned item, and a returned item is money the utility counted and then lost. The reason code is where the pattern is.",
    canvas: "rpt_payment",
    axis: "Cancel Reason", value: "Amount",
    sql: `select coalesce("Cancel Reason", "Cancel Reason Code", '(none given)') as "Cancel Reason",
                 count(*)::bigint as "Payments",
                 round(sum("Pay Segment Amount")::numeric, 2) as "Amount",
                 count(distinct "Account ID")::bigint as "Accounts"
          from reporting.rpt_payment
          where "Is Cancelled"
          group by 1 order by 3 desc nulls last`,
  }),
  q({
    id: "unbalanced-pay-events",
    process: "financial", workstream: "Cashiering",
    kind: "outlier", unit: "money",
    title: "Which payment events do not balance?",
    why: "The tenders taken and the payments applied should equal each other. Where they do not, cash has been recorded that was never applied to an account.",
    canvas: "rpt_payment",
    axis: "Main Customer Name", value: "Event Tender Total",
    sql: `select "Pay Event ID", "Payment Date",
                 round("Event Tender Total"::numeric, 2) as "Event Tender Total",
                 round("Event Payment Total"::numeric, 2) as "Event Payment Total",
                 round(("Event Tender Total" - "Event Payment Total")::numeric, 2) as "Difference",
                 "Account ID", "Main Customer Name"
          from reporting.rpt_payment
          where not "Event Is Balanced"
          order by abs("Event Tender Total" - "Event Payment Total") desc nulls last
          limit 50`,
  }),
  q({
    id: "adjustments-by-type",
    process: "financial", workstream: "Adjustments",
    kind: "distribution", unit: "money",
    title: "What is being adjusted, and by how much?",
    why: "Adjustments are the manual override on an automated system. A type that grows is a process people have stopped trusting.",
    canvas: "rpt_financial_txn",
    axis: "Adjustment Type", value: "Adjustment Amount",
    sql: `select coalesce("Adjustment Type", "Adjustment Type Code", '(unset)') as "Adjustment Type",
                 count(*)::bigint as "Adjustments",
                 round(sum("Adjustment Amount")::numeric, 2) as "Adjustment Amount",
                 count(distinct "Account ID")::bigint as "Accounts",
                 count(*) filter (where "Is Adjustment Cancellation")::bigint as "Cancellations"
          from reporting.rpt_financial_txn
          where "Is Adjustment" or "Is Adjustment Cancellation"
          group by 1 order by 3 desc nulls last`,
  }),
  q({
    id: "gl-by-account",
    process: "financial", workstream: "General Ledger",
    kind: "total", unit: "money",
    title: "What is posting to each general ledger account?",
    why: "This is the bridge between the billing system and the finance system. Finance reconciles to these numbers, so they are the ones that get questioned.",
    canvas: "rpt_gl",
    axis: "GL Account", value: "GL Amount",
    sql: `select "GL Account",
                 coalesce("Distribution Code", '(unset)') as "Distribution Code",
                 count(*)::bigint as "Lines",
                 round(sum("GL Amount") filter (where "Is Debit")::numeric, 2) as "Debits",
                 round(sum("GL Amount") filter (where not "Is Debit")::numeric, 2) as "Credits",
                 round(sum("GL Amount")::numeric, 2) as "GL Amount"
          from reporting.rpt_gl
          group by 1, 2 order by 6 desc nulls last
          limit 100`,
  }),
  q({
    id: "revenue-by-class",
    process: "financial", workstream: "Revenue",
    kind: "total", unit: "money",
    filters: [{"field": "Is Frozen", "op": "eq", "value": true},
              {"field": "Is Bill Segment", "op": "eq", "value": true},
              {"field": "Is Revenue Bearing", "op": "eq", "value": true}],
    title: "Where does revenue come from, by revenue class?",
    why: "Revenue class is how a utility reports itself to a regulator. Anything unclassified here is revenue that cannot be reported. Non-revenue service agreements are excluded — see \"How much of what we bill is not revenue?\" for what came out and why.",
    canvas: "rpt_financial_txn",
    axis: "Revenue Class", value: "Current Amount",
    sql: `select coalesce("Revenue Class", "Revenue Class Code", '(unclassified)') as "Revenue Class",
                 coalesce("Utility Type", '(unset)') as "Utility Type",
                 count(*)::bigint as "Transactions",
                 round(sum("Current Amount")::numeric, 2) as "Current Amount"
          from reporting.rpt_financial_txn
          where "Is Frozen" and "Is Bill Segment" and "Is Revenue Bearing"
          group by 1, 2 order by 4 desc nulls last`,
  }),

  // ============================================================ Credit, deeper
  q({
    id: "credit-rating-movement",
    process: "credit", workstream: "Credit Risk",
    kind: "distribution",
    title: "How is customer credit standing moving?",
    why: "Credit rating points are what drive deposits and collection severity. The events that create them tell you which process is downgrading customers.",
    canvas: "rpt_credit_rating_history",
    axis: "Created By Event", value: "Changes",
    sql: `select coalesce("Created By Event", "Created By Event Code", '(unset)') as "Created By Event",
                 count(*)::bigint as "Changes",
                 count(distinct "Account ID")::bigint as "Accounts",
                 round(avg("Credit Rating Points")::numeric, 1) as "Avg Rating Points",
                 round(avg("Cash-Only Points")::numeric, 1) as "Avg Cash-Only Points"
          from reporting.rpt_credit_rating_history
          group by 1 order by 2 desc`,
  }),
  q({
    id: "severance-pipeline",
    process: "credit", workstream: "Collections",
    kind: "distribution",
    title: "What is in the disconnection pipeline?",
    why: "Severance is the end of the collections path and the point of no return for the customer relationship. Knowing the volume before it executes is the whole value of watching it.",
    canvas: "rpt_debt_process",
    axis: "Process Status", value: "Processes",
    sql: `select "Process Type",
                 coalesce("Process Status", "Process Status Code") as "Process Status",
                 count(distinct "Process ID")::bigint as "Processes",
                 count(distinct "Account ID")::bigint as "Accounts",
                 round(sum("Process Arrears Amount")::numeric, 2) as "Arrears In Pipeline",
                 round(avg("Days Since Process Created")::numeric, 1) as "Avg Age (days)"
          from reporting.rpt_debt_process
          group by 1, 2 order by 3 desc`,
  }),
  q({
    id: "arrears-without-process",
    process: "credit", workstream: "Collections",
    kind: "outlier", unit: "money",
    title: "Who is in arrears with no collection process running?",
    why: "Debt nobody is chasing. Every account here is either an oversight or an exclusion somebody applied and never reviewed.",
    canvas: "rpt_customer_account",
    axis: "Main Customer Name", value: "Total Arrears",
    sql: `select "Account ID", "Main Customer Name", "Customer Class", "Collection Class",
                 round("Total Arrears"::numeric, 2) as "Total Arrears",
                 round("Arrears 120+ Days"::numeric, 2) as "120+ Days",
                 "Collection Process Count", "Is On Active Pay Plan", "Has Alert"
          from reporting.rpt_customer_account
          where coalesce("Total Arrears",0) > 0 and coalesce("Collection Process Count",0) = 0
          order by "Total Arrears" desc
          limit 50`,
  }),
  q({
    id: "pay-plan-vs-actual",
    process: "credit", workstream: "Pay Plans",
    kind: "outlier", unit: "money",
    title: "Which pay plans are furthest behind schedule?",
    why: "The variance between what was scheduled and what was paid is the early warning that a plan is about to break, while there is still time to renegotiate it.",
    canvas: "rpt_pay_plan",
    axis: "Main Customer Name", value: "Paid vs Elapsed Schedule Variance",
    sql: `select "Pay Plan ID", coalesce("Pay Plan Type", "Pay Plan Type Code") as "Pay Plan Type",
                 "Pay Plan Status", "Start Date",
                 "Scheduled Payments Elapsed Count" as "Instalments Due",
                 round("Paid Total Since Plan Start"::numeric, 2) as "Paid",
                 round("Paid vs Elapsed Schedule Variance"::numeric, 2) as "Paid vs Elapsed Schedule Variance",
                 "Account ID", "Main Customer Name"
          from reporting.rpt_pay_plan
          where "Is Active" and "Paid vs Elapsed Schedule Variance" is not null
          order by "Paid vs Elapsed Schedule Variance" asc
          limit 50`,
  }),
  q({
    id: "sa-aged-balance",
    process: "credit", workstream: "Credit Risk",
    kind: "total", unit: "money",
    title: "What does the aged balance look like at agreement level?",
    why: "Account-level arrears can hide a single agreement in deep debt behind others in credit. The agreement is where collections actually acts.",
    canvas: "rpt_sa_aged_balance",
    axis: "SA Type", value: "Past Due Amount",
    sql: `select coalesce("SA Type", "SA Type Code") as "SA Type",
                 count(*)::bigint as "Agreements",
                 count(*) filter (where "Is Past Due")::bigint as "Past Due",
                 count(*) filter (where "Has Credit Balance")::bigint as "In Credit",
                 round(sum("Past Due Amount")::numeric, 2) as "Past Due Amount",
                 round(sum("Arrears 121+ Days")::numeric, 2) as "121+ Days"
          from reporting.rpt_sa_aged_balance
          group by 1 order by 5 desc nulls last`,
  }),

  // ============================================================ Operations, deeper
  q({
    id: "batch-runtime-trend",
    process: "field", workstream: "Batch Operations",
    kind: "distribution", unit: "days",
    title: "Which batch jobs take the longest, on average?",
    why: "The overnight window is finite. The jobs at the top of this list are the ones that decide whether the window holds when volumes grow.",
    canvas: "rpt_batch",
    axis: "Batch Code", value: "Avg Duration (min)",
    sql: `select "Batch Code", max("Program") as "Program",
                 count(*)::bigint as "Runs",
                 count(*) filter (where "Run Status Code" = '30')::bigint as "Errored",
                 round(avg("Duration (min)")::numeric, 1) as "Avg Duration (min)",
                 round(max("Duration (min)")::numeric, 1) as "Worst Run (min)"
          from reporting.rpt_batch
          group by 1 order by 5 desc nulls last`,
  }),
  q({
    id: "todo-oldest",
    process: "field", workstream: "Work Queues",
    kind: "outlier", unit: "days",
    title: "Which to-do entries have been open longest?",
    why: "A to-do is work the system could not finish alone. The oldest ones are the exceptions nobody has been made responsible for.",
    canvas: "rpt_todo",
    axis: "To Do Type", value: "Hours Open",
    sql: `select "To Do Entry ID", coalesce("To Do Type", "To Do Type Code") as "To Do Type",
                 "Entry Status", "Priority Code", round("Hours Open"::numeric, 1) as "Hours Open",
                 "Assigned User", "Created Date/Time"
          from reporting.rpt_todo
          where not "Is Complete"
          order by "Hours Open" desc nulls last
          limit 50`,
  }),
  q({
    id: "field-appointments",
    process: "field", workstream: "Field Performance",
    kind: "count",
    title: "How much field work needs an appointment?",
    why: "An appointment is a commitment to a customer and a constraint on the crew's day. The proportion needing one is what makes a route plannable or not.",
    canvas: "rpt_field_activity",
    axis: "Activity Type", value: "Appointment Required",
    sql: `select coalesce("Activity Type", "Activity Type Code") as "Activity Type",
                 count(*)::bigint as "Activities",
                 count(*) filter (where trim("Appointment Required") = 'Y')::bigint as "Appointment Required",
                 count(*) filter (where "Appointment Taken Date/Time" is not null)::bigint as "Appointment Booked",
                 count(distinct "Work By Crew")::bigint as "Crews"
          from reporting.rpt_field_activity
          group by 1 order by 2 desc`,
  }),
  q({
    id: "exception-by-rule",
    process: "field", workstream: "Data Quality",
    kind: "distribution",
    title: "Which validation rules are firing most?",
    why: "A single VEE rule producing most of the exceptions is usually mis-tuned rather than right. Tuning it clears the queue faster than working it does.",
    canvas: "rpt_exception",
    axis: "VEE Rule", value: "Exceptions",
    sql: `select coalesce("VEE Rule", "Rule Code", '(unset)') as "VEE Rule",
                 coalesce("VEE Group Code", '(unset)') as "VEE Group",
                 count(*)::bigint as "Exceptions",
                 count(*) filter (where "Is Open")::bigint as "Open",
                 count(distinct "Device ID")::bigint as "Devices Affected"
          from reporting.rpt_exception
          group by 1, 2 order by 3 desc`,
  }),
  q({
    id: "usage-transactions",
    process: "field", workstream: "Data Quality",
    kind: "distribution",
    title: "Are usage transactions reaching a bill?",
    why: "A usage transaction that never gets used on a bill is measurement that produced no revenue. It is the cleanest definition of leakage in the meter-to-cash chain.",
    canvas: "rpt_usage_txn",
    axis: "Usage Status Code", value: "Transactions",
    sql: `select coalesce("Usage Status Code", '(unset)') as "Usage Status Code",
                 coalesce("Used on Bill Code", '(unset)') as "Used on Bill Code",
                 count(*)::bigint as "Transactions",
                 count(*) filter (where "Is Used on Bill")::bigint as "Used on Bill",
                 round(sum("Final Quantity")::numeric, 2) as "Final Quantity"
          from reporting.rpt_usage_txn
          group by 1, 2 order by 3 desc`,
  }),

  // ------------------------------------------------- coverage: every canvas answers
  // (2026-08-31: seven canvases had no ready-to-run reports; each now carries at
  // least two, so the library and the builder's question gallery cover the whole
  // reporting layer.)
  q({
    id: "bills-by-status",
    process: "usage", workstream: "Billing",
    kind: "count",
    title: "How many bills, by status?",
    why: "Pending bills past their window are billing throughput problems; completed is the denominator for close.",
    canvas: "rpt_bill",
    axis: "Bill Status", value: "Bills",
    sql: `select coalesce("Bill Status", '(unset)') as "Bill Status",
                 count(*)::bigint as "Bills"
          from reporting.rpt_bill
          group by 1 order by 2 desc`,
  }),
  q({
    id: "bills-longest-open",
    // Declared for the portal's governed query (pending bills only: a completed bill has no open clock; demo25, 2026-09-04).
    filters: [{"field": "Is Completed", "op": "eq", "value": false}],
    process: "usage", workstream: "Billing",
    kind: "outlier", chart: "horizontal",
    title: "Which bill cycles have the longest-open bills?",
    why: "A cycle whose bills sit open for weeks is where billing close is actually stuck.",
    canvas: "rpt_bill",
    axis: "Bill Cycle", value: "Days Bill Open",
    sql: `select coalesce("Bill Cycle", '(none)') as "Bill Cycle",
                 max("Days Bill Open")::bigint as "Days Bill Open"
          from reporting.rpt_bill
          group by 1 order by 2 desc`,
  }),
  q({
    id: "sas-by-type",
    process: "customer", workstream: "Customer Information",
    kind: "ranking", chart: "horizontal",
    title: "How many service agreements, by SA type?",
    why: "The service portfolio at a glance — and a type with a handful of SAs is usually leftover configuration.",
    canvas: "rpt_service_agreement",
    axis: "SA Type", value: "Service Agreements",
    sql: `select coalesce("SA Type", "SA Type Code", '(unset)') as "SA Type",
                 count(*)::bigint as "Service Agreements"
          from reporting.rpt_service_agreement
          group by 1 order by 2 desc`,
  }),
  q({
    id: "sa-balance-by-type",
    process: "credit", workstream: "Credit & Collections",
    kind: "total", chart: "horizontal",
    title: "Where do balances sit, by SA type?",
    why: "Receivables concentrated in one service type changes who you call and how.",
    canvas: "rpt_service_agreement",
    axis: "SA Type", value: "Current Balance",
    sql: `select coalesce("SA Type", "SA Type Code", '(unset)') as "SA Type",
                 sum("Current Balance")::numeric(18,2) as "Current Balance"
          from reporting.rpt_service_agreement
          group by 1 order by 2 desc`,
  }),
  q({
    id: "links-by-relationship",
    process: "customer", workstream: "Customer Information",
    kind: "count",
    title: "How are people linked to accounts, by relationship?",
    why: "Account-person links drive who gets billed and who gets told; an unexpected relationship mix is a data-entry pattern worth seeing.",
    canvas: "rpt_account_person",
    axis: "Account Relationship", value: "Links",
    sql: `select coalesce("Account Relationship", "Account Relationship Code", '(unset)') as "Account Relationship",
                 count(*)::bigint as "Links"
          from reporting.rpt_account_person
          group by 1 order by 2 desc`,
  }),
  q({
    id: "financially-responsible-split",
    process: "customer", workstream: "Customer Information",
    kind: "distribution",
    title: "Who on the account is financially responsible?",
    why: "Responsibility drives collections contact; third-party-only accounts behave differently in arrears.",
    canvas: "rpt_account_person",
    axis: "Financially Responsible", value: "People",
    sql: `select "Financially Responsible",
                 count(*)::bigint as "People"
          from reporting.rpt_account_person
          group by 1 order by 2 desc`,
  }),
  q({
    id: "billed-by-class-calc-lines",
    process: "usage", workstream: "Billing",
    kind: "total", chart: "horizontal",
    title: "What was billed, by customer class (charge lines)?",
    why: "The charge-line view of billed dollars — the level rate analysts reconcile at.",
    canvas: "rpt_billed_charge",
    axis: "Customer Class", value: "Billed Amount",
    sql: `select coalesce("Customer Class", "Customer Class Code", '(unset)') as "Customer Class",
                 sum("Billed Amount")::numeric(18,2) as "Billed Amount"
          from reporting.rpt_billed_charge
          group by 1 order by 2 desc`,
  }),
  q({
    id: "billed-by-budget-plan",
    process: "usage", workstream: "Billing",
    kind: "total",
    title: "How much was billed under each budget plan?",
    why: "Budget billing shifts cash timing; the split shows how much revenue rides on it.",
    canvas: "rpt_billed_charge",
    axis: "Budget Plan", value: "Billed Amount",
    sql: `select coalesce("Budget Plan", '(none)') as "Budget Plan",
                 sum("Billed Amount")::numeric(18,2) as "Billed Amount"
          from reporting.rpt_billed_charge
          group by 1 order by 2 desc`,
  }),
  q({
    id: "measured-by-uom",
    process: "usage", workstream: "Usage",
    kind: "total", chart: "horizontal",
    title: "What was measured on bills, by unit of measure?",
    why: "Per-UOM totals are the safe way to look at quantity — never sum across units.",
    canvas: "rpt_bill_segment_read",
    axis: "Unit of Measure", value: "Measured Quantity",
    sql: `select coalesce("Unit of Measure", "Unit of Measure Code", '(unset)') as "Unit of Measure",
                 sum("Measured Quantity")::numeric(18,2) as "Measured Quantity"
          from reporting.rpt_bill_segment_read
          group by 1 order by 2 desc`,
  }),
  q({
    id: "reads-by-row-kind",
    process: "usage", workstream: "Usage",
    kind: "distribution",
    title: "Where do billed reads come from?",
    why: "Register reads vs derived rows tells you how much of billing rests on actual measurement.",
    canvas: "rpt_bill_segment_read",
    axis: "Read Row Kind", value: "Read Rows",
    sql: `select coalesce("Read Row Kind", '(unset)') as "Read Row Kind",
                 count(*)::bigint as "Read Rows"
          from reporting.rpt_bill_segment_read
          group by 1 order by 2 desc`,
  }),
  q({
    id: "locations-by-type",
    process: "meter", workstream: "Assets",
    kind: "ranking", chart: "horizontal",
    title: "How many asset locations, by type?",
    why: "The shape of the location estate — and types with one node are usually setup artifacts.",
    canvas: "rpt_asset_location",
    axis: "Location Type", value: "Locations",
    sql: `select coalesce("Location Type", "Location Type Code", '(unset)') as "Location Type",
                 count(*)::bigint as "Locations"
          from reporting.rpt_asset_location
          group by 1 order by 2 desc`,
  }),
  q({
    id: "deepest-location-trees",
    process: "meter", workstream: "Assets",
    kind: "outlier", chart: "horizontal",
    title: "Which location trees run deepest?",
    why: "Very deep hierarchies slow navigation and usually mean an import created nesting nobody designed.",
    canvas: "rpt_asset_location",
    axis: "Location", value: "Hierarchy Depth",
    sql: `select "Location",
                 max("Hierarchy Depth")::bigint as "Hierarchy Depth"
          from reporting.rpt_asset_location
          group by 1 order by 2 desc
          limit 25`,
  }),
  q({
    id: "characteristics-by-entity",
    process: "field", workstream: "Operations",
    kind: "count",
    title: "Which entities carry characteristics?",
    why: "Characteristics are the free-form extension surface; where they pile up is where configuration lives.",
    canvas: "rpt_characteristics",
    axis: "Entity Type", value: "Characteristics",
    sql: `select coalesce("Entity Type", '(unset)') as "Entity Type",
                 count(*)::bigint as "Characteristics"
          from reporting.rpt_characteristics
          group by 1 order by 2 desc`,
  }),
  q({
    id: "top-characteristic-types",
    process: "field", workstream: "Operations",
    kind: "ranking", chart: "horizontal",
    title: "Which characteristic types are most used?",
    why: "The top of this list is this client's real extension model — worth knowing before any report asks for 'that extra field'.",
    canvas: "rpt_characteristics",
    axis: "Characteristic", value: "Rows",
    sql: `select coalesce("Characteristic", "Characteristic Code", '(unset)') as "Characteristic",
                 count(*)::bigint as "Rows"
          from reporting.rpt_characteristics
          group by 1 order by 2 desc
          limit 25`,
  }),
];

export function byId(id) {
  return QUESTIONS.find((x) => x.id === id) || null;
}

export function byProcess(processId) {
  return QUESTIONS.filter((x) => x.process === processId);
}

export function workstreamsFor(processId) {
  return [...new Set(byProcess(processId).map((x) => x.workstream))];
}

export const KIND_LABEL = {
  total: "Total", count: "Count", distribution: "Distribution",
  outlier: "Outliers", ranking: "Ranking",
};
