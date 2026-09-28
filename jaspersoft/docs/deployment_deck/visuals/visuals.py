"""The four visual slides: shared between the main deck and the standalone visuals file."""
def N(id, x, y, w, h, title, body="", kind="step", **kw):
    d = dict(id=id, x=x, y=y, w=w, h=h, title=title, kind=kind)
    if body: d["body"] = body
    d.update(kw); return d
def E(a, b, **kw):
    d = {"from": a, "to": b}; d.update(kw); return d

# ---- Standard Offering: four org columns left to right, a gate at the end of each, the after-go-live band below
GX = [0.81, 5.99, 11.17, 16.35]; GW = 4.86; NX = [g + 0.18 for g in GX]; NW = 4.5
def gate(id, col, y, title, w=1.7, h=0.9, **kw):
    return N(id, NX[col] + (NW - w) / 2, y, w, h, title, kind="gate", **kw)
SO_FLOW = {"type": "diagram", "title": "Standard Offering Deployment Flow", "kicker": "V1", "nodes": [
 N("g1", GX[0], 2.0, GW, 6.55, "Origin_DEV", "authoring, the internal server", kind="group"),
 N("g2", GX[1], 2.0, GW, 6.55, "Origin_TEST", "proving, before any client", kind="group"),
 N("g3", GX[2], 2.0, GW, 6.55, "Client test org", "the client's own data", kind="group"),
 N("g4", GX[3], 2.0, GW, 6.55, "Client prod org", "read-only until the prod flag is given", kind="group"),
 N("g5", 0.81, 8.85, 20.4, 1.95, "After go-live", "every change is a tool run with the same proofs, never a hand edit", kind="group"),
 N("a1", NX[0], 2.75, NW, 1.0, "Workstreams tree", "domains, Ad Hoc views, reports and dashboards: the only content edited by hand"),
 N("a2", NX[0], 3.90, NW, 0.8, "Export the org", "one API export task, polled, downloaded"),
 N("a3", NX[0], 4.85, NW, 1.55, "Build the package", "inventory and classify the export; keep the offering list; one copy of each domain in one home; carry the datasource; rewrite every path; strip print wrappers; narrow the import index"),
 gate("a4", 0, 6.70, "package verifies?"),
 N("b1", NX[1], 2.75, NW, 0.85, "Import, update in place", "polled; an importer warning counts as a failure"),
 N("b2", NX[1], 3.75, NW, 0.85, "Re-export and compare", "byte-equal inside the scope, importer stamps ignored"),
 N("b3", NX[1], 4.75, NW, 0.95, "Execute everything", "views by query, reports as PDF, domains by metadata and probe"),
 gate("b4", 1, 5.90, "seven proofs pass?"),
 N("b5", NX[1], 7.00, NW, 0.85, "Proven offering", "the package every client promotion starts from", center=True),
 N("c1", NX[2], 2.75, NW, 0.8, "Inventory snapshot", "every resource on the org before anything changes"),
 N("c2", NX[2], 3.70, NW, 1.2, "Rebuild for the client", "the client's own datasource export carried byte for byte; org path, folder, alias and tenant root rewritten"),
 gate("c3", 2, 5.05, "verified? no source strings, references exist, fields resolve", w=2.6, h=1.05, title_pt=10),
 N("c4", NX[2], 6.25, NW, 0.8, "Import, compare, execute", "the same three proofs as Origin_TEST"),
 N("c5", NX[2], 7.20, NW, 1.0, "Sweep and sign off", "PASS, EMPTY, SLOW or FAIL per resource with timing; one document per org"),
 N("d0", NX[3], 2.75, NW, 0.5, "explicit prod flag required", kind="accent"),
 N("d1", NX[3], 3.40, NW, 0.75, "Inventory snapshot", "the rollback baseline"),
 N("d2", NX[3], 4.30, NW, 1.1, "Same promotion, same proofs", "target datasource carried; rewritten; verified; imported; compared; executed"),
 gate("d3", 3, 5.55, "seven proofs pass?"),
 N("d4", NX[3], 6.60, NW, 0.75, "Sweep and sign off", "on the client's prod numbers"),
 N("d5", NX[3], 7.50, NW, 0.85, "Diff after = rollback record", "inventory before against after: nothing else moved"),
 N("e1", 1.0, 9.45, 6.4, 1.15, "Additive-only domain patch", "the additions guard refuses any change to what is there; seven proofs per org; one-command restore"),
 N("e2", 7.8, 9.45, 6.4, 1.15, "Standardized Reports folder", "scheduled SQL reports in one place on every org, promoted by the same tool"),
 N("e3", 14.6, 9.45, 6.4, 1.15, "Sweep after every change", "the sign-off is regenerated; the first red row is the alert")],
 "edges": [E("a1","a2"), E("a2","a3"), E("a3","a4"),
  E("a4","b1", via=[(5.83, 7.15), (5.83, 3.17)]),
  E("b1","b2"), E("b2","b3"), E("b3","b4"), E("b4","b5"),
  E("b5","c1", via=[(11.01, 7.42), (11.01, 3.15)]),
  E("c1","c2"), E("c2","c3"), E("c3","c4"), E("c4","c5"),
  E("c5","d0", via=[(16.19, 7.7), (16.19, 3.0)]),
  E("d0","d1"), E("d1","d2"), E("d2","d3"), E("d3","d4"), E("d4","d5"),
  E("d5","e3", via=[(18.6, 8.68), (17.8, 8.68)], to_side="top")],
 "legend": "Orange diamonds are gates: a failed gate stops the run and names the rollback. The Workstreams tree is never moved; the offering is a curated copy promoted org by org."}

# ---- Database deployment: the rollout across two rows, the parallel baseline jobs, the twice-daily loop, and the objects each domain reads
JOBS = ["FT", "Billed usage", "SQ usage", "GL distribution", "Measurement", "Usage", "Usage scalar detail", "SA snapshot refresh"]
job_nodes = [N(f"j{i}", 13.62 + (i % 4) * 1.92, 2.78 + (i // 4) * 0.52, 1.78, 0.42, j, center=True, title_pt=10) for i, j in enumerate(JOBS)]
def col_label(id, x, w, title):
    return N(id, x, 6.92, w, 0.35, title, kind="note")
DB_FLOW = {"type": "diagram", "title": "Database Deployment Flow", "kicker": "V2", "nodes": [
 N("p1", 0.81, 2.5, 2.5, 1.0, "Preflight", "the deploy user can read every source table and write the targets"),
 N("p2", 3.61, 2.5, 2.9, 1.0, "Create the 7 snapshot tables", "empty, with their keys"),
 N("p3", 6.81, 2.5, 3.1, 1.0, "Create the domain-support objects", "SA snapshot table, lookup seed, 8 CMS views, grants, synonyms"),
 N("p4", 10.21, 2.5, 2.9, 1.0, "Deploy the procedures", "baseline (24 months, once) and operational per table; SA refresh"),
 N("p5", 13.41, 2.15, 7.8, 1.65, "Submit 8 baselines as parallel scheduler jobs", "unattended; they survive a dropped connection", kind="group")] + job_nodes + [
 N("q1", 18.7, 4.4, 2.3, 1.05, "ready gate: every job SUCCEEDED?", kind="gate", title_pt=10),
 N("q2", 15.6, 4.4, 2.6, 1.05, "validate and install gates pass?", kind="gate", title_pt=10),
 N("q3", 12.7, 4.5, 2.4, 0.85, "Post-load indexes", "keys and dates the domains filter on"),
 N("q4", 9.2, 4.45, 3.0, 0.95, "Rolling procedures", "3 months rebuilt, 24 kept; one operational refresh run by hand"),
 N("q5", 6.5, 4.4, 2.2, 1.05, "validated again?", kind="gate", title_pt=10),
 N("q6", 3.35, 4.45, 2.7, 0.95, "Schedule", "twice daily, 30-minute stagger, held on TEST until approved"),
 N("q7", 0.81, 4.45, 2.1, 0.95, "Capture runs, data quality", "per client, kept with the log"),
 N("big", 0.81, 6.3, 20.4, 4.5, "What the domains read", "created in steps 2 and 3, validated and gated before anything is scheduled; each stack feeds the domain chip beneath it", kind="group"),
 col_label("l1", 0.95, 2.3, "Finance"), col_label("l2", 3.4, 2.3, "Billing and Rates"), col_label("l3", 5.85, 2.3, "Meter Operations"),
 col_label("l4", 8.6, 2.6, "Debt Management"), col_label("l5", 11.5, 3.25, "Meter Operations views"), col_label("l6", 15.0, 3.35, "Field Operations views"), col_label("l7", 18.6, 2.4, "Customer Operations views"),
 N("t1", 0.95, 7.3, 2.3, 0.9, "FT_RPT_CURR", "financial transactions", kind="data"),
 N("t2", 0.95, 8.35, 2.3, 0.9, "FT_GL_DISTRIBUTION_RPT_CURR", "GL distribution", kind="data", title_pt=9.5),
 N("t3", 3.4, 7.3, 2.3, 0.9, "BSEG_BILLED_USAGE_RPT_CURR", "billed usage per segment", kind="data", title_pt=9.5),
 N("t4", 3.4, 8.35, 2.3, 0.9, "BSEG_SQ_USAGE_RPT_CURR", "service quantities", kind="data", title_pt=9.5),
 N("t5", 5.85, 7.3, 2.3, 0.65, "D1_MSRMT_RPT_CURR", "measurements", kind="data", title_pt=9.5),
 N("t6", 5.85, 8.05, 2.3, 0.65, "D1_USAGE_RPT_CURR", "usage transactions", kind="data", title_pt=9.5),
 N("t7", 5.85, 8.8, 2.3, 0.65, "D1_USAGE_SCALAR_DTL_RPT_CURR", "usage scalar detail", kind="data", title_pt=9),
 N("m1", 0.95, 9.85, 2.3, 0.6, "Finance domains", kind="domain"),
 N("m2", 3.4, 9.85, 2.3, 0.6, "Billing and Rates domains", kind="domain", title_pt=10),
 N("m3", 5.85, 9.85, 2.3, 0.6, "Usage and measurement domains", kind="domain", title_pt=10),
 N("s1", 8.6, 7.3, 2.6, 0.95, "CMS_SA_SNAPSHOT", "aged balance per SA, refreshed by procedure", kind="data", title_pt=10),
 N("s2", 8.6, 8.45, 2.6, 0.7, "CM_SNAPSHOT_TYPE_FLG", "lookup seed: LDAY, EMON, ARCH, LEMN", center=True, title_pt=10, body_pt=9.5),
 N("m4", 8.6, 9.85, 2.6, 0.6, "SA Snapshot Aged Balance domain", kind="domain", title_pt=10),
 N("v1", 11.5, 7.3, 3.25, 0.5, "CMS_D1_DVC_IDENTIFIER_VW", center=True, title_pt=9),
 N("v2", 11.5, 7.9, 3.25, 0.5, "CMS_D1_DVC_BODA_VW", center=True, title_pt=9),
 N("v3", 11.5, 8.5, 3.25, 0.5, "CMS_W1_ASSET_IDENTIFIER_VW", center=True, title_pt=9),
 N("m5", 11.5, 9.85, 1.55, 0.6, "Device domain", kind="domain", title_pt=10),
 N("m6", 13.2, 9.85, 1.55, 0.6, "Asset domain", kind="domain", title_pt=10),
 N("v4", 15.0, 7.3, 3.35, 0.5, "CMS_C1_REPRESENTATIVE_BODA_VW", center=True, title_pt=9),
 N("v5", 15.0, 7.9, 3.35, 0.5, "CMS_D1_ACTIVITY_CHAR_VW", center=True, title_pt=9),
 N("v6", 15.0, 8.5, 3.35, 0.5, "CMS_D1_ACTIVITY_D1FA_BODA_VW", center=True, title_pt=9),
 N("m7", 15.0, 9.85, 1.6, 0.6, "Crew domain", kind="domain", title_pt=10),
 N("m8", 16.75, 9.85, 1.6, 0.6, "Field Activity domain", kind="domain", title_pt=10),
 N("v7", 18.6, 7.3, 2.4, 0.5, "CMS_CI_CASE_VW", center=True, title_pt=9),
 N("v8", 18.6, 7.9, 2.4, 0.5, "CMS_CI_CASE_LOG_VW", center=True, title_pt=9),
 N("m9", 18.6, 9.85, 2.4, 0.6, "Case domain", kind="domain", title_pt=10)],
 "edges": [E("p1","p2"), E("p2","p3"), E("p3","p4"), E("p4","p5"),
  E("p5","q1", from_side="bottom", to_side="top", via=[(19.85, 4.05)]),
  E("q1","q2"), E("q2","q3"), E("q3","q4"), E("q4","q5"), E("q5","q6"), E("q6","q7"),
  E("q6","q4", from_side="bottom", to_side="bottom", via=[(4.7, 5.85), (10.7, 5.85)], label="every 12 hours: the newest 3 months rebuilt, older rows kept", label_at=(5.0, 5.5), label_w=6.0),
  E("t2","m1"), E("t4","m2"), E("t7","m3"), E("s2","m4"), E("v2","m5", from_side="left", to_side="top", via=[(11.3, 8.15), (11.3, 9.55), (12.27, 9.55)]), E("v3","m6", from_side="bottom", to_side="top", via=[(13.12, 9.55), (13.97, 9.55)]),
  E("v6","m7", from_side="bottom", to_side="top", via=[(16.675, 9.4), (15.8, 9.4)]),
  E("v6","m8", from_side="bottom", to_side="top", via=[(16.675, 9.4), (17.55, 9.4)]),
  E("v8","m9")],
 "legend": "Cylinders are the tables the domains read; the boxes under the three view columns are the CMS views; orange diamonds are gates that stop the rollout. The loop under the second row is the twice-daily rolling refresh."}

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
