<!-- GENERATED from originba_dbt/.claude/skills/c2m-functional-architect/references/functional-architect-bok.md by scripts/local/sync_assistant_knowledge.py; do not edit -->

# The C2M 25.4 functional architect & technical analyst body of knowledge

Distilled from the C2M 25.4 Business User Guide (BUG), the Oracle Utilities
implementation-guide corpus, and course/certification outlines. Citation shorthand:
`BUG/<file>` = `https://docs.oracle.com/en/industries/energy-water/advanced-meter/254/c2m-user-guides/Topics/<file>`.
Entry point: BUG/C2M_BP_Intro.html. Where a lifecycle-state list was inferred from topic
structure rather than stated verbatim, verify exact state names against the client's BO
configuration before hardcoding them in tests or canvases.

## 1. C-side functional map (CCB)

### The V — master data spine
Person → Account (demographic leg), Premise → Service Point (geographic leg), joined at
the vertex by the **Service Agreement** — the financial contract linking an account to
the service points it consumes through (BUG/C1_BP01CustInfo_Customer_Information.html).
SA Type drives nearly all behavior: billing algorithm, rate eligibility, GL
distribution, C&C treatment (BUG/C1_BP14_Rates_Rates_Introduction.html).

**SA lifecycle**: Pending Start → Active → Pending Stop → Stopped → Closed (+
Reactivated post-close). Active/Stopped SAs still carry debt; Closed means zero
balance — report populations must state which states are "customers".
**Start/Stop**: starting creates Pending Start; background processes (+ field activity
linkage) complete activation (BUG/C1_BP01CustInfo_Start_Stop.html). Order-based vs
Start/Stop-based enrollment is a documented design trade-off
(BUG/C1_BP13SalesAndMarketing_Order_versus_Start_Stop.html).
**Pitfalls**: SAs stuck Pending Start silently drop out of billing; premise-level joins
ignoring effective-dated SA/SP links double-count on meter exchange; landlord reversion
auto-creates SAs on tenant move-out and surprises churn metrics.

### Billing lifecycle end to end
Bill cycle defines *when*; the cycle's bill window is the days batch tries; one bill
segment per SA, in billing-processing-sequence order for interdependent SAs
(BUG/C1_BP05Billing_A_High_Level_Overview_Of_The_Bill.html). Metered flow: request
determinants from MDM → apply rate → segment + FT, calc detail in bill calc lines.

**Bill lifecycle** (Pending → Complete), completion in documented order: pre-completion
algorithms; due date = bill date + customer-class days; routing from account persons;
freeze of freezable segments/adjustments (if Freeze At Bill Completion is on);
final-deposit refund; completion algorithms; bill messages; sweep of FTs since last
bill; autopay creation; match events (open-item); LPC date; mark for debt monitor;
post-completion algorithms (BUG/C1_BP05Billing_Bill_Lifecycle.html). Reopen only for
most-recent bill and not after autopay interfaced.
**Bill segment lifecycle**: Incomplete → Freezable|Error → Frozen → Pending Cancel →
Cancelled; Frozen is the ONLY state that reaches the customer and GL; Rebill = original
to Pending Cancel + new Freezable; cancel/rebill sweeps to the NEXT bill unless Credit
Notes are used (BUG/C1_BP05Billing_Bill_Segment_Lifecycle.html).
**Documented pitfall**: Error segments can be AUTO-DELETED on the last night of the
window (DEL-BSEG pre-completion) — an unbilled SA vanishes from the error queue.
Segment counts must always pin status: freezable+frozen+cancelled overstates revenue.

### Cashiering
Three tiers: **Payment Event** (remittance envelope) ⊃ **Tenders** (instruments) +
**Payments** (allocation to accounts); many-to-many across accounts within an event
(BUG/C1_BP06Payment_The_Big_Picture_of_Payments.html). Payment lifecycle mirrors
segments (error → freezable → frozen = GL-effective). Two cancellation flavors: tender
cancellation (NSF, fee + C&C consequences) vs payment cancellation (reallocation).
Unbalanced payment events are a first-class exception state; tender/deposit controls
implement drawer-to-bank balancing. **Pitfalls**: tenders≠payments breaks daily cash
recon when one check pays several accounts; a payment "may affect more than customer
balances" (deposits, credits) so cash ≠ AR relief.

### Credit & collections
Automated debt monitor vs control-table criteria; humans override
(BUG/C1_BP08CreditAndCollections_Credit_Collections.html). Three escalating processes
with events: collection (letters/To Dos), severance (incl. disconnect field
activities), write-off; plus payment arrangements / pay plans and agency referral.
Overdue-obligation processing is the newer BO-based stream. **Reporting states**:
process active/completed/cancelled (payment cures CANCEL the process — not "success"
without care); broken arrangements re-expose old debt; severance ≠ disconnection until
the field activity completes.

### Financial transactions & GL
Every financial effect is an FT (BS bill segment / AD adjustment / PS pay segment);
FTs carry GL detail and maintain **current balance** (due) vs **payoff balance**
(clears the obligation — differs on budgets, loans, deposits)
(BUG/C1_BP09FinancialTransaction_Financial_Transactions.html). FTs are GL-effective
only when FROZEN; balance control gates GL transmission; match events tie FTs for
open-item accounting; arrears buckets feed C&C. **Pitfall**: revenue reports source
frozen FTs, never bill segments alone — adjustments and cancels exist only in the FT
stream.

### Rates, field work, cases, sales
Two engines: legacy component-based (schedule → rate versions → rate components) and
calc-rule-based (schedule → calc groups → rules); bill factors externalize prices;
mid-period changes PRORATE — recomputing rate×usage outside the engine won't tie
(BUG/C1_BP14_Rates_Rates_Introduction.html). C2M replaces classic field activities
with **Service Order Activities** (X1/D1 orchestrator) spawning field activities;
orphaned activities block SA activation/stop (BUG/C1_BP04FieldWork_Field_Orders.html).
Cases are fully implementation-defined (type + lifecycle) — case reporting is always
client-config-specific (BUG/C1_BP21Cases_Case_Management.html). Sales: campaigns →
packages → orders, which can create person/account/premise/SP in one transaction
(BUG/C1_BP13SalesAndMarketing_Sales_Marketing.html).

## 2. D-side functional map (MDM)

### Devices, configurations, measuring components
Device classes: smart meter, manual meter, item, communication component
(BUG/D1_BG_Devices.html). Physical asset lifecycle (received → in stock → installed →
removed → repair → retired) lives in Asset Management shared with ODM
(BUG/W1_BG_Asset_Management_AssetManagement.html). A **device configuration** is the
effective-dated arrangement of the device's **measuring components** — MCs, not
devices, are what measurements attach to; MC types: interval vs scalar (+ autoread,
standalone/aggregator) (BUG/D1_BG_Measuring_Components.html). **Pitfall**: joining
consumption to devices breaks on multi-channel meters; ignoring config effective
dating misattributes usage across reprogramming.

### Service point / install event
The SP is the D-side anchor; an **install event** records which device config is at
which SP with install/removal datetimes and **on/off history** within one installation
(BUG/D1_BG_Install_Events.html). Measurement cycles/routes schedule manual reads;
cross-installed-meter correction is a documented enough failure to have its own topic.
**Pitfall**: at meter exchange, removal dttm of one event = install of the next —
naive joins double-count the exchange day.

### IMD → VEE → measurement pipeline
Raw reads arrive as **IMD**; VEE processes them; only then **final measurements** —
the single billable series per MC (BUG/D1_BG_Measurements.html). VEE rules grouped
into groups, executed under roles: Initial Load (automatic), Manual Override,
Estimation; flow = validate → edit → estimate, producing VEE exceptions
(BUG/D1_BG_VEE.html). Gaps filled by periodic estimation; corrections re-derive via
measurement reprocessing; measurements carry condition codes (regular/estimated/
edited). **Pitfalls**: consumption from IMDs double-counts re-derivations;
estimated-read % by condition code is THE meter-data-quality KPI; unworked VEE
exceptions are tomorrow's billing errors.

### Usage subscription → usage transaction
The **usage subscription** says which SPs' consumption to compute for which subscriber
(C2M mirror of the CCB SA); a **usage transaction** is one execution: usage calc
group/rules over final measurements → billing determinants
(BUG/D1_BG_Usage_Transactions.html). UT lifecycle: pending → calculated/sent with
issue-detected/approval branches; **subsequent correction** for post-bill re-dos.
**TOU maps** (types + generated data from templates) bucket intervals for
TOU-differentiated determinants (BUG/D1_BG_Time_of_Use_Maps.html). **Pitfall**: a
C-side bill segment in error very often traces to a D-side UT in issue-detected —
report both queues together.

### Aggregations & 360 views
Aggregations compute totals across MC populations (standard and dynamic) for
settlement/load research (BUG/D1_BG_Aggregations.html). **360 Degree Views** (Device,
MC, SP, Usage Subscription, Contact) are the base product's own statement of "what an
analyst expects joined around one entity" — a defensible canvas design target
(BUG/D1_BG_360_Degree_Views.html).

## 3. The C2M seam

Master data sync is **one-way, CCB → MDM; MDM changes never sync back**
(BUG/X1_AG_C2M_Data_Mapping-Master_Data_Sync.html):

| C-side master | D-side copy | Outbound BO |
| --- | --- | --- |
| PERSON | D1-CONTACT | C1-MDM2PersonSyncRequest |
| SA | Usage Subscription | C1-MDM2SASyncRequest |
| BILL CYCLE | D1-BILLCYCLE | C1-MDM2BillCycleSyncRequest |
| CONTRACT OPTION / EVENT | Dynamic Option / Event | C1-MDM2ContractOpt(Evt)SyncRequest |

- C-side masters: identity, accounts, SAs, financials, rates. D-side masters: devices,
  MCs, install events, measurements, VEE, UTs. SP exists on both sides, unified/linked,
  D-side carries metering detail.
- **Reporting sourcing rule**: source each fact from its master — money from `CI_*`,
  metering from `D1_*`; treat Contact/US as denormalized copies of Person/SA (join back
  to the C-side dimension, don't dimensionalize them).
- **Seam pitfalls**: stalled sync requests leave a new SA with no US (billing finds no
  determinants); one-way sync overwrites D-side "fixes"; UT ↔ bill-segment
  reconciliation is the canonical seam health check.

## 4. Technical analyst toolkit

- **CMA** is the sanctioned config transport: migration plans (per MO) → migration
  requests → export → import with compare/approve → apply, via batch; moves
  CONFIGURATION only, never master/transactional data
  (BUG/F1_95CMA_Configuration_Process.html; cloud doctrine:
  docs.oracle.com/en/industries/energy-water/shared/23b/cs-live-ops-guide/CS_LIVE_OPS_23B/Cloud_Live_Operate_Guidelines.3.5.html).
  Bundling is the lighter BO-based sibling.
- **Batch model**: batch control → runs → threads → thread instances (second instance
  only after error+restart); error runs auto-restart next submission; Do Not Attempt
  Restart is the corrupt-data bailout; Batch Run Tree exposes per-thread errors,
  output, performance, 20-run history (BUG/F1_BP03Batch_Batch_Run_Tree.html). Thread
  number 0 = run all threads; rerun number re-extracts a prior run for download
  processes.
- **Integration patterns**: sync-request BO state machines; lockbox payment upload;
  consumption extract requests; head-end/AMI comms; GL interface fed by frozen FTs
  gated by balance control.
- **Schema conventions** (framework DB naming standard,
  docs.oracle.com/en/industries/utilities/common/264/cs-implementation-guide/database-naming-conventions.html):
  owner-flag table prefixes (`CI_`/`SC_` legacy CCB, `F1_`, `D1_`/`D2_`, `W1_`,
  `X1_`, `CM_` mandatory for customer mods), names ≤30 chars; `_L` language tables
  (PK = parent + LANGUAGE_CD); `_K` key tables (key + environment id — basis of
  environment copy); `*_FLG` via CI_LOOKUP_VAL_L; BO CLOBs need XML extraction;
  effective-dated config joins need range predicates.

## 5. Reporting / analytics lens — the daily questions per stakeholder

- **Billing manager**: bill-window progress (billed vs scheduled per cycle); Error
  segments and AGE — before the end-of-window auto-delete; cancel/rebill volume and
  reasons; unbilled active SAs; estimated-read billing rate (via measurement condition
  codes); revenue by rate/GL from frozen FTs only.
- **Cashier supervisor**: tender/deposit control balancing by cashier and drawer;
  unbalanced + incomplete payment events; NSF counts/amounts; payments in error;
  autopay volumes.
- **Credit manager**: aged AR by arrears bucket; processes by state and event stage;
  cure (cancelled-by-payment) rates; pending disconnect field activities;
  arrangement kept/broken rates; agency referral balances.
- **Meter shop / AMI ops**: device population by lifecycle state; install/removal/
  exchange counts; AMI read-success rate (IMDs received vs expected per MC); VEE
  exception backlog by rule; estimation % trend; UTs in issue-detected blocking
  billing; cross-installed corrections.
- **Field operations**: service order activity aging by state; appointments kept;
  activities blocking Pending Start/Stop SAs.
- **Customer service / marketing**: case volume/aging by type+status (config-defined);
  campaign/order conversion; To Do backlog by role.
- **IT operations**: batch run tree failures/durations vs history; sync-request
  backlog across the seam.

Cross-cutting doctrine: every fact filters on lifecycle state (frozen FTs, final
measurements, completed bills); counts of zero are findings; the product's 360 views
and dashboards are the base-product blueprint of what each persona expects in one
place.
