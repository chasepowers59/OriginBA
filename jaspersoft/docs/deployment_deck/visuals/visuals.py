"""The four visual slides: shared between the main deck and the standalone visuals file, and the
source of the draw.io diagrams (spec_to_drawio.py reads the same JSON). Coordinates are inches on
the 22" x 12.37" slide."""


def N(id, x, y, w, h, title, body="", kind="step", **kw):
    d = dict(id=id, x=x, y=y, w=w, h=h, title=title, kind=kind)
    if body: d["body"] = body
    d.update(kw); return d


def E(a, b, **kw):
    d = {"from": a, "to": b}; d.update(kw); return d


SEVEN = ("the seven proofs: 1 no source host, org path or datasource name survives in the package; 2 every reference to "
         "something outside the package exists on the target; 3 every field the views use resolves in its domain; "
         "4 import without warnings; 5 re-export byte-equal inside the scope; 6 every resource executes; "
         "7 datasource connection unchanged")

# ---- Standard Offering: four org columns left to right, a gate with its fail branch in each, the after-go-live band below
GX = [0.81, 5.99, 11.17, 16.35]; GW = 4.86; NX = [g + 0.18 for g in GX]; NW = 4.5


def gate(id, col, y, title, w=1.5, h=0.9, **kw):
    return N(id, NX[col] + (NW - w) / 2, y, w, h, title, kind="gate", **kw)


def stop_right(id, col, y, gw=1.5):
    x = NX[col] + (NW + gw) / 2 + 0.5
    return N(id, x, y, NX[col] + NW - x - 0.02, 0.45, "stop", kind="stop", title_pt=9)


SO_FLOW = {"type": "diagram", "title": "Standard Offering Deployment Flow", "kicker": "V1",
 "subtitle": "authored on Origin_DEV, proven on Origin_TEST, then every client org by the same tool with the same seven proofs",
 "nodes": [
 N("g1", GX[0], 2.0, GW, 7.05, "Origin_DEV", "authoring, the internal server", kind="group"),
 N("g2", GX[1], 2.0, GW, 7.05, "Origin_TEST", "proving, before any client", kind="group"),
 N("g3", GX[2], 2.0, GW, 7.05, "Client test org", "the client's own data", kind="group"),
 N("g4", GX[3], 2.0, GW, 7.05, "Client prod org", "read-only until the prod flag is given", kind="group"),
 N("g5", 0.81, 9.35, 20.4, 1.85, "After go-live", "every change is a tool run with the same proofs, never a hand edit", kind="group"),
 N("a1", NX[0], 2.75, NW, 1.0, "Workstreams tree", "domains, Ad Hoc views, reports and dashboards: the only content edited by hand", num=1),
 N("a2", NX[0], 3.9, NW, 0.8, "Export the org", "one API export task, polled, downloaded", num=2,
   tooltip="A REST export task on the internal server, polled until done, downloaded as a zip package."),
 N("a3", NX[0], 4.85, NW, 1.55, "Build the package", "inventory and classify the export; keep the offering list; one copy of each domain in one home; carry the datasource; rewrite every path; strip print wrappers; narrow the import index", num=3),
 gate("a4", 0, 6.65, "package verifies?", num=4, tooltip="No source host, org path or datasource name left in the package; every outside reference exists on the target; every field the views use resolves."),
 N("sa4", NX[0] + 0.02, 6.875, 0.98, 0.45, "stop", kind="stop", title_pt=9),
 N("b1", NX[1], 2.75, NW, 0.85, "Import, update in place", "polled; an importer warning counts as a failure", num=5),
 N("b2", NX[1], 3.75, NW, 0.85, "Re-export and compare", "byte-equal inside the scope, importer stamps ignored", num=6),
 N("b3", NX[1], 4.75, NW, 0.95, "Execute everything", "views by query, reports as PDF, domains by metadata and probe", num=7),
 gate("b4", 1, 5.9, "seven proofs pass?", num=8, tooltip=SEVEN),
 stop_right("sb4", 1, 6.125),
 N("b5", NX[1], 7.0, NW, 0.85, "Proven offering", "the package every client promotion starts from", center=True, num=9),
 N("c0", NX[2], 2.75, NW, 0.5, "datasource: the client's own export, carried byte for byte", kind="accent", title_pt=11,
   tooltip="The target org's own /DataSource export is unzipped and carried into the package unchanged; never an edited copy of the source's datasource."),
 N("c1", NX[2], 3.4, NW, 0.8, "Inventory snapshot", "every resource on the org before anything changes", num=10),
 N("c2", NX[2], 4.35, NW, 1.2, "Rebuild for the client", "the client's datasource carried; org path, folder, alias and tenant root rewritten by tested replacements", num=11),
 gate("c3", 2, 5.7, "package verified?", num=12, tooltip="No source host, org path or datasource name survives; every outside reference exists on the target; every field the views use resolves in its domain."),
 stop_right("sc3", 2, 5.925),
 N("c4", NX[2], 6.8, NW, 0.8, "Import, compare, execute", "the same three proofs as Origin_TEST", num=13),
 N("c5", NX[2], 7.75, NW, 1.0, "Sweep and sign off", "PASS, EMPTY, SLOW or FAIL per resource with timing; one document per org", num=14),
 N("d0", NX[3], 2.75, NW, 0.5, "explicit prod flag required", kind="accent",
   tooltip="Prod writes refuse to run without the explicit prod flag; every other command is read-only against prod."),
 N("d1", NX[3], 3.4, NW, 0.75, "Inventory snapshot", "the rollback baseline", num=15),
 N("d2", NX[3], 4.3, NW, 1.1, "Same promotion, same proofs", "target datasource carried; rewritten; verified; imported; compared; executed", num=16),
 gate("d3", 3, 5.55, "seven proofs pass?", num=17, tooltip=SEVEN),
 stop_right("sd3", 3, 5.775),
 N("d4", NX[3], 6.6, NW, 0.75, "Sweep and sign off", "on the client's prod numbers", num=18),
 N("d5", NX[3], 7.5, NW, 0.85, "Diff after = rollback record", "inventory before against after: nothing else moved", num=19),
 N("e1", 1.0, 9.95, 6.4, 1.05, "Additive-only domain patch", "the additions guard refuses any change to what is there; seven proofs per org; one-command restore"),
 N("e2", 7.8, 9.95, 6.4, 1.05, "Standardized Reports folder", "scheduled SQL reports in one folder; on Origin_DEV today, promoted to client orgs by the same tool when approved"),
 N("e3", 14.6, 9.95, 6.4, 1.05, "Sweep after every change", "the sign-off is regenerated; the first red row is the alert"),
 N("loopnote", 13.7, 1.45, 7.3, 0.35, "every later change re-enters at the client test org and repeats steps 10 to 19", kind="note")],
 "edges": [E("a1","a2"), E("a2","a3"), E("a3","a4"), E("a4","sa4", label="no"),
  E("a4","b1", via=[(5.83, 7.1), (5.83, 3.175)], label="yes", label_at=(4.4, 6.72), label_w=1.0),
  E("b1","b2"), E("b2","b3"), E("b3","b4"), E("b4","sb4", label="no"), E("b4","b5", label="yes"),
  E("b5","c1", via=[(11.01, 7.425), (11.01, 3.8)]),
  E("c0","c1"), E("c1","c2"), E("c2","c3"), E("c3","sc3", label="no"), E("c3","c4", label="yes"), E("c4","c5"),
  E("c5","d0", via=[(16.19, 8.25), (16.19, 3.0)]),
  E("d0","d1"), E("d1","d2"), E("d2","d3"), E("d3","sd3", label="no"), E("d3","d4", label="yes"), E("d4","d5"),
  E("d5","e3", via=[(18.78, 9.2), (17.8, 9.2)], to_side="top"),
  E("e3","c0", from_side="right", to_side="top", via=[(21.5, 10.475), (21.5, 1.85), (13.6, 1.85)])],
 "legend": "Orange diamonds are gates: yes continues, no stops the run and names the rollback. Numbers are the order of one full promotion. The Workstreams tree is never moved; the offering is a curated copy promoted org by org.",
 "legend_y": 11.3,
 "layers": {
  "Commands": [
   dict(x=1.0, y=5.95, w=4.3, h=0.42, title="build_standard_offering_package.py, then verify_standard_offering_package.py"),
   dict(x=6.2, y=3.15, w=4.3, h=0.42, title="jrs_promote.py --from internal:Origin_DEV --to test:Origin_TEST --resource /SmartCity/Report/Standard_Offering --ds Origin_TEST_DS"),
   dict(x=11.4, y=3.75, w=4.3, h=0.42, title="jrs_inventory.py snapshot --env test --orgs <Org>"),
   dict(x=11.4, y=5.1, w=4.3, h=0.42, title="jrs_promote.py --from test:Origin_TEST --to test:<Org> --resource /SmartCity/Report/Standard_Offering --ds <Org>_DS"),
   dict(x=11.4, y=8.4, w=4.3, h=0.42, title="jrs_run_sweep.py --env test --org <Org> --folder /SmartCity/Report/Standard_Offering; build_standard_offering_validation_doc.py --evidence"),
   dict(x=16.6, y=4.95, w=4.3, h=0.42, title="jrs_promote_test_to_prod.py --org <Org> --folder /SmartCity/Report/Standard_Offering --ds <DS> --i-mean-prod"),
   dict(x=1.0, y=10.55, w=6.2, h=0.42, title="jrs_domain_patch_apply.py --env test --org <Org> --domain <uri> --patch <module>  (--restore rolls back)")],
  "Checks": [
   dict(x=1.0, y=7.45, w=4.3, h=0.55, title="package gate", body="no source host / org / datasource string; every outside reference exists on the target; every view field resolves in its domain"),
   dict(x=6.2, y=6.9, w=4.3, h=0.75, title="seven proofs", body=SEVEN.split(": ", 1)[1]),
   dict(x=16.6, y=6.6, w=4.3, h=0.75, title="seven proofs, on prod", body=SEVEN.split(": ", 1)[1])]}}

# ---- Database deployment: the rollout across two rows with its gates and fail branches, the parallel baseline jobs,
# ---- the twice-daily loop with its cadence, and the objects each domain reads as one outlined stack per workstream
JOBS = ["FT", "Billed usage", "SQ usage", "GL distribution", "Measurement", "Usage", "Usage scalar detail", "SA snapshot refresh"]
job_nodes = [N(f"j{i}", 13.62 + (i % 4) * 1.92, 2.78 + (i // 4) * 0.52, 1.78, 0.42, j, center=True, title_pt=10) for i, j in enumerate(JOBS)]
cadence = []


def wsgroup(id, x, w, title):
    return N(id, x, 6.95, w, 2.6, title, kind="group")


DB_FLOW = {"type": "diagram", "title": "Database Deployment Flow", "kicker": "V2",
 "subtitle": "one client, from preflight to the twice-daily rolling refresh, and the objects every Standard Offering domain reads",
 "nodes": [
 N("p1", 0.81, 2.5, 2.5, 1.0, "Preflight", "the deploy user can read every source table and write the targets", num=1),
 N("p2", 3.61, 2.5, 2.9, 1.0, "Create the 7 snapshot tables", "empty, with their keys", num=2),
 N("p3", 6.81, 2.5, 3.1, 1.0, "Create the domain-support objects", "SA snapshot table, lookup seed, 8 CMS views, grants, synonyms", num=3),
 N("p4", 10.21, 2.5, 2.9, 1.0, "Deploy the procedures", "baseline (the retained 24 months, once) and operational per table; the SA aged-balance refresh", num=4),
 N("p5", 13.41, 2.15, 7.8, 1.65, "5. Submit 8 baselines as parallel scheduler jobs", "unattended; they survive a dropped connection", kind="group")] + job_nodes + [
 N("q1", 18.7, 4.45, 2.3, 0.95, "ready gate: every job SUCCEEDED?", kind="gate", title_pt=10, num=6,
   tooltip="The scheduler's job table is polled up to eight hours; every one-time baseline job must report SUCCEEDED; a FAILED or missing job stops the rollout."),
 N("sq1", 18.9, 5.75, 1.9, 0.42, "stop, fix, re-run", kind="stop", title_pt=9),
 N("q2", 15.6, 4.45, 2.6, 0.95, "validate and install gates pass?", kind="gate", title_pt=10, num=7,
   tooltip="Row counts, twelve monthly totals against the source, duplicate keys; no empty table; the CMS views valid, the lookup seeded, the aging buckets sum to the balance, FT parity."),
 N("sq2", 15.85, 5.75, 2.1, 0.42, "stop, fix, re-run", kind="stop", title_pt=9),
 N("q3", 12.7, 4.45, 2.4, 0.95, "Post-load indexes", "keys and dates the domains filter on", num=8),
 N("q4", 9.2, 4.45, 3.0, 0.95, "Rolling procedures", "3 months rebuilt, 24 kept; one operational refresh run by hand", num=9),
 N("q5", 6.5, 4.45, 2.2, 0.95, "validated again?", kind="gate", title_pt=10, num=10, tooltip="The same validation pack after the operational refresh, so the rolling result is compared to the baseline result."),
 N("sq5", 6.6, 3.65, 2.0, 0.42, "stop, fix, re-run", kind="stop", title_pt=9),
 N("q6", 3.35, 4.45, 2.7, 0.95, "Schedule", "twice daily from 10:00 and 16:00 UTC, 30-minute stagger; held on TEST until approved", num=11),
 N("q7", 0.81, 4.45, 2.1, 0.95, "Capture runs, data quality", "per client, kept with the log", num=12),
 N("cad", 0.81, 5.47, 3.8, 0.6, "runs at (UTC), one job every 30 minutes", "10:00 to 13:30, then again 16:00 to 19:30", kind="note")] + cadence + [
 N("big", 0.81, 6.3, 20.4, 4.5, "What the domains read", "created in steps 2 and 3, validated at step 7 before anything is scheduled; each outlined stack feeds the domain chip beneath it", kind="group"),
 wsgroup("wf", 0.95, 2.3, "Finance tables"), wsgroup("wb", 3.4, 2.3, "Billing tables"), wsgroup("wm", 5.85, 2.3, "Meter Ops tables"),
 wsgroup("wd", 8.6, 2.6, "Debt Mgmt objects"), wsgroup("wv", 11.5, 3.25, "Meter Ops views"), wsgroup("wo", 15.0, 3.35, "Field Ops views"), wsgroup("wc", 18.6, 2.4, "Customer Ops views"),
 N("t1", 1.05, 7.4, 2.1, 0.85, "FT_RPT_CURR", "financial transactions", kind="data", tooltip="Every financial transaction in the retained 24 months, refreshed twice daily"),
 N("t2", 1.05, 8.4, 2.1, 0.85, "FT_GL_DISTRIBUTION_RPT_CURR", "GL distribution", kind="data", title_pt=9),
 N("t3", 3.5, 7.4, 2.1, 0.85, "BSEG_BILLED_USAGE_RPT_CURR", "billed usage per segment", kind="data", title_pt=9),
 N("t4", 3.5, 8.4, 2.1, 0.85, "BSEG_SQ_USAGE_RPT_CURR", "service quantities", kind="data", title_pt=9),
 N("t5", 5.95, 7.4, 2.1, 0.62, "D1_MSRMT_RPT_CURR", "measurements", kind="data", title_pt=9),
 N("t6", 5.95, 8.12, 2.1, 0.62, "D1_USAGE_RPT_CURR", "usage transactions", kind="data", title_pt=9),
 N("t7", 5.95, 8.84, 2.1, 0.62, "D1_USAGE_SCALAR_DTL_RPT_CURR", "usage scalar detail", kind="data", title_pt=8.5),
 N("m1", 0.95, 9.85, 2.3, 0.6, "Finance domains", kind="domain"),
 N("m2", 3.4, 9.85, 2.3, 0.6, "Billing and Rates domains", kind="domain", title_pt=10),
 N("m3", 5.85, 9.85, 2.3, 0.6, "Usage and measurement domains", kind="domain", title_pt=10),
 N("s1", 8.7, 7.4, 2.4, 0.9, "CMS_SA_SNAPSHOT", "aged balance per SA, refreshed by procedure", kind="data", title_pt=10,
   tooltip="One end-of-day row per service agreement: current and payoff balance, ten aging buckets from frozen ARS transactions; credits retire the oldest debt first; buckets 1 to 5 sum to the current balance."),
 N("s2", 8.7, 8.45, 2.4, 0.7, "CM_SNAPSHOT_TYPE_FLG", "lookup seed: LDAY, EMON, ARCH, LEMN", center=True, title_pt=10, body_pt=9.5,
   tooltip="The domain inner-joins these four codes; a fresh database without the seed returns zero rows in every Ad Hoc view."),
 N("m4", 8.6, 9.85, 2.6, 0.6, "SA Snapshot Aged Balance domain", kind="domain", title_pt=10),
 N("v1", 11.6, 7.4, 3.05, 0.5, "CMS_D1_DVC_IDENTIFIER_VW", center=True, title_pt=9, tooltip="Device identifiers pivoted into columns: asset id, badge, serial, internal meter number, external and MDM ids, NIC id and serial"),
 N("v2", 11.6, 8.0, 3.05, 0.5, "CMS_D1_DVC_BODA_VW", center=True, title_pt=9, tooltip="The device's business-object data parsed from XML: business object, latest status, retirement date"),
 N("v3", 11.6, 8.6, 3.05, 0.5, "CMS_W1_ASSET_IDENTIFIER_VW", center=True, title_pt=9, tooltip="Asset identifiers pivoted into columns, the asset-side twin of the device identifier view"),
 N("m5", 11.5, 9.85, 1.55, 0.6, "Device domain", kind="domain", title_pt=10),
 N("m6", 13.2, 9.85, 1.55, 0.6, "Asset domain", kind="domain", title_pt=10),
 N("v4", 15.1, 7.4, 3.15, 0.5, "CMS_C1_REPRESENTATIVE_BODA_VW", center=True, title_pt=9, tooltip="Field representative mobile details parsed from XML: service areas and worker capabilities"),
 N("v5", 15.1, 8.0, 3.15, 0.5, "CMS_D1_ACTIVITY_CHAR_VW", center=True, title_pt=9, tooltip="Activity characteristics pivoted per activity: internal status, priority, third-party representative"),
 N("v6", 15.1, 8.6, 3.15, 0.5, "CMS_D1_ACTIVITY_D1FA_BODA_VW", center=True, title_pt=9, tooltip="Field activity business-object data parsed from XML: instructions, appointment window, requester, external references, contact names and phones"),
 N("m7", 15.0, 9.85, 1.6, 0.6, "Crew domain", kind="domain", title_pt=10),
 N("m8", 16.75, 9.85, 1.6, 0.6, "Field Activity domain", kind="domain", title_pt=10),
 N("v7", 18.7, 7.4, 2.2, 0.5, "CMS_CI_CASE_VW", center=True, title_pt=9, tooltip="One row per case with create and close times derived from the case log and the duration in minutes"),
 N("v8", 18.7, 8.0, 2.2, 0.5, "CMS_CI_CASE_LOG_VW", center=True, title_pt=9, tooltip="The case log as a timeline: each status change with the previous status and the time spent in each state"),
 N("m9", 18.6, 9.85, 2.4, 0.6, "Case domain", kind="domain", title_pt=10)],
 "edges": [E("p1","p2"), E("p2","p3"), E("p3","p4"), E("p4","p5"),
  E("p5","q1", from_side="bottom", to_side="top", via=[(17.31, 4.1), (19.85, 4.1)]),
  E("q1","sq1", label="no"), E("q1","q2", label="yes"), E("q2","sq2", label="no"), E("q2","q3", label="yes"), E("q3","q4"), E("q4","q5"), E("q5","sq5", label="no"), E("q5","q6", label="yes"), E("q6","q7"),
  E("q6","q4", from_side="bottom", to_side="bottom", via=[(4.7, 5.85), (10.7, 5.85)], label="every 12 hours: the newest 3 months rebuilt, older rows kept", label_at=(5.0, 5.5), label_w=6.0),
  E("wf","m1"), E("wb","m2"), E("wm","m3"), E("wd","m4"),
  E("wv","m5", from_side="bottom", to_side="top", via=[(13.125, 9.7), (12.27, 9.7)]),
  E("wv","m6", from_side="bottom", to_side="top", via=[(13.125, 9.7), (13.97, 9.7)]),
  E("wo","m7", from_side="bottom", to_side="top", via=[(16.675, 9.7), (15.8, 9.7)]),
  E("wo","m8", from_side="bottom", to_side="top", via=[(16.675, 9.7), (17.55, 9.7)]),
  E("wc","m9")],
 "legend": "Every box in the map is one database object the domains read: seven rolling snapshot tables, the SA aged-balance table with its lookup seed, and eight CMS views. Numbers are the order of one rollout; orange diamonds are gates: yes continues, no stops the rollout there. The loop under the second row is the twice-daily rolling refresh (3 months rebuilt, 24 kept; 6 months at CityCorp and Odessa).",
 "layers": {
  "Commands": [
   dict(x=0.9, y=3.05, w=2.3, h=0.42, title="prod_snapshot_rollout_25_4.sh <client>  (steps 1 to 8, logged)"),
   dict(x=3.7, y=3.05, w=6.0, h=0.42, title="run_snapshot_rollout_step.py --step baseline-and-validate --clients <c>  (tables, procedures, baselines, ready gate, validation, install gate)"),
   dict(x=12.8, y=4.95, w=2.2, h=0.42, title="clients/post_load_snapshot_indexes_direct.sql"),
   dict(x=6.6, y=5.0, w=5.5, h=0.42, title="run_snapshot_rollout_step.py --step cutover-and-validate --clients <c>"),
   dict(x=3.45, y=4.95, w=2.5, h=0.42, title="--step schedule-operational"),
   dict(x=0.9, y=4.95, w=1.9, h=0.42, title="08 capture, 13 data quality")],
  "Checks": [
   dict(x=18.5, y=3.6, w=2.6, h=0.55, title="03d ready gate", body="every JOB_BASELINE_*_ONCE job SUCCEEDED; none FAILED or missing"),
   dict(x=15.5, y=3.35, w=2.8, h=0.8, title="04 / 04b / 04c / 04d", body="row counts; 12 monthly totals vs source; duplicate keys; no empty table; CMS views valid; lookup seeded; ARS buckets sum to CUR_BAL; FT parity"),
   dict(x=8.7, y=3.7, w=2.8, h=0.45, title="04 again, after the operational refresh")]}}

# ---- The two tables of objects (unchanged)
VIEWS_A = {"type": "table", "title": "The Objects The Domains Depend On (1 of 2)", "kicker": "V3", "font": 16, "row_h": 1.45, "widths": [4.3, 2.0, 8.9, 5.2],
 "columns": ["Object", "Kind", "What it is", "Depended on by"], "rows": [
 ["CMS_SA_SNAPSHOT", "table + refresh procedure", "One end-of-day (LDAY) aged-balance row per service agreement: current and payoff balance, new charges, and ten aging buckets built from frozen ARS financial transactions dated up to today. Credits and payments retire the oldest debt first; excess credit sits in the current bucket; buckets 1 to 5 always sum to the current balance; future-dated amounts are excluded.", "Debt Management: the SA Snapshot Aged Balance domain, its account roll-up (a derived query over this table, not a second object), and every aged-debt view and dashboard on it"],
 ["CM_SNAPSHOT_TYPE_FLG", "lookup seed", "The four snapshot-type codes (LDAY, EMON, ARCH, LEMN) written into the C2M lookup tables. The domain inner-joins them, so a fresh database without the seed returns zero rows in every Ad Hoc view.", "Debt Management: SA Snapshot Aged Balance domain"],
 ["CMS_D1_DVC_IDENTIFIER_VW", "view", "One row per device with its identifiers pivoted from rows into columns: asset id, badge number, serial number, internal meter number, external and MDM ids, NIC id and serial, name, utility device id.", "Meter Operations: Device domain; Daily Installations, Disconnected Service Points, Meters Not Recently Read"],
 ["CMS_D1_DVC_BODA_VW", "view", "The device's business-object data area parsed out of its XML: business object code, latest status, retirement date and time. One row per device.", "Meter Operations: Device domain"],
 ["CMS_W1_ASSET_IDENTIFIER_VW", "view", "One row per asset with its identifiers pivoted into columns, the asset-side twin of the device identifier view, so the Asset domain can join by badge, serial or external id.", "Meter Operations: Asset domain; In Storage, Distribution of Installed Assets, Non-Meter Assets"]]}

VIEWS_B = {"type": "table", "title": "The Objects The Domains Depend On (2 of 2)", "kicker": "V4", "font": 16, "row_h": 1.45, "widths": [4.3, 2.0, 8.9, 5.2],
 "columns": ["Object", "Kind", "What it is", "Depended on by"], "rows": [
 ["CMS_C1_REPRESENTATIVE_BODA_VW", "view", "Field representative (crew member) mobile details parsed out of the representative's XML data area: the service areas they cover and their worker capabilities, one row per representative and area or capability.", "Field Operations: Crew domain and its views"],
 ["CMS_D1_ACTIVITY_CHAR_VW", "view", "Activity characteristics pivoted per field activity: internal field-activity status, priority, and the third-party representative code, so the domain filters on them as columns.", "Field Operations: Crew domain"],
 ["CMS_D1_ACTIVITY_D1FA_BODA_VW", "view", "The field activity's business-object data parsed from XML: instructions and comments, the appointment window and who took it, expiration, requester, external references, and the customer and contact names and phone numbers.", "Field Operations: Crew and Field Activity domains; Upcoming Field Work, Cancelations, Average Days per Field Task"],
 ["CMS_CI_CASE_VW", "view", "One row per case with its create and close timestamps derived from the case log (the case-created entry and the closing status entry) and the duration in minutes, measured to now while the case is open.", "Customer Operations: Case domain and every case view"],
 ["CMS_CI_CASE_LOG_VW", "view", "The case log as a timeline: every status change with the previous status, the previous log time, and how long the case sat in the previous and the current state.", "Customer Operations: Case domain (state durations and the case timeline views)"]],
 "legend": "All ten objects are created by one wrapper step in the rollout, validated by their own pack, and gated before the snapshots are scheduled; the CISREAD synonyms are repaired in the same step because CityCorp shipped with synonyms pointing at missing objects."}

VISUALS = [SO_FLOW, DB_FLOW, VIEWS_A, VIEWS_B]
