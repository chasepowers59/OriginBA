#!/usr/bin/env python3
"""Build the portal catalog from the dbt REPORTING LAYER instead of the CISADM snapshots.

WHY THIS REPLACES build_snapshot_explorer_catalog.py
----------------------------------------------------
The portal was built on the `*_RPT_CURR` tables -- client-built snapshots of CISADM,
refreshed by hand-maintained SQL, described by hand-maintained registry metadata, and
typed by Domain XML exports that had to be re-exported whenever a column moved. Three
sources of truth for one catalog, none of them generated from the thing they describe.

The dbt project is now the transformation layer, and it already produces everything this
catalog needs, generated rather than curated:

    models/marts/reporting/_reporting.yml   38 canvases, 1,373 columns, enforced
                                            contracts -- name, type and description, and
                                            the canvas's own header prose as its summary
    docs/column_lineage.json                every column traced to the CISADM column it
                                            came from, and the transform applied

So the catalog is now DERIVED. A column added to a canvas appears here on the next build;
a column renamed cannot silently keep its old entry, because there is no hand-written
entry to keep. That is the whole reason to move.

WHAT CHANGES FOR THE PORTAL
---------------------------
`schema` becomes `reporting` and `table_name` becomes `rpt_*`. Everything else keeps the
shape the portal already consumes -- fields / dimensions / measures / date_fields /
premade_reports / data_model -- so the explorer, the report library and the dashboards
need no change to read it.

Dimension or measure is decided by TYPE, not by a name pattern: numeric is a measure,
everything else is a dimension, and a boolean is a dimension because a flag is something
you split by, never something you sum. The old classifier guessed from the column name,
which is why it had a list of exceptions.

    python3 scripts/build_dbt_reporting_catalog.py
    python3 scripts/build_dbt_reporting_catalog.py --dbt-project ~/originba_dbt
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DBT = Path.home() / "originba_dbt"

# Canvas -> workstream. The portal's workstream vocabulary is kept exactly as it is, so
# existing dashboards and the workstream pages keep working; only what fills them changes.
WORKSTREAM = {
    "rpt_customer_account": "customer_ops", "rpt_account_person": "customer_ops",
    "rpt_customer_contact": "customer_ops", "rpt_customer_notification": "customer_ops",
    "rpt_service_task_history": "customer_ops", "rpt_case": "customer_ops",
    "rpt_characteristics": "common",

    "rpt_bill_segment": "billing", "rpt_billed_charge": "billing",
    "rpt_billed_usage": "billing", "rpt_bill_segment_read": "billing",
    "rpt_billable_charge": "billing", "rpt_unbilled_revenue": "billing",
    "rpt_rate_configuration": "billing", "rpt_bill_factor_price": "billing",
    "rpt_rate_schedule_history": "billing", "rpt_service_agreement": "billing",

    "rpt_financial_txn": "finance", "rpt_gl": "finance",
    "rpt_revenue_reconciliation": "finance",

    "rpt_payment": "cashiering", "rpt_payment_tender": "cashiering",
    "rpt_tender_control": "cashiering",

    "rpt_aged_debt": "debt", "rpt_sa_aged_balance": "debt",
    "rpt_debt_process": "debt", "rpt_pay_plan": "debt",
    "rpt_credit_rating_history": "debt",

    "rpt_device_asset": "meter_ops", "rpt_premise_sp": "meter_ops",
    "rpt_measurement": "meter_ops", "rpt_usage_txn": "meter_ops",
    "rpt_device_event": "meter_ops", "rpt_on_off_history": "meter_ops",
    "rpt_asset_location": "meter_ops",

    "rpt_field_activity": "field_ops", "rpt_exception": "field_ops",
    "rpt_todo": "common", "rpt_batch": "common",
}

WORKSTREAM_LABELS = {
    "finance": "Finance", "billing": "Billing & Rates", "meter_ops": "Meter Operations",
    "cashiering": "Cashiering & Payments", "debt": "Collections & Debt",
    "customer_ops": "Customer Operations", "field_ops": "Field Operations",
    "new_services": "New Services", "common": "Operations & Shared Services",
}
WORKSTREAM_ORDER = ["billing", "finance", "cashiering", "debt", "customer_ops",
                    "meter_ops", "field_ops", "common"]

NUMERIC = {"numeric", "bigint", "integer", "int", "double precision", "real", "decimal"}

# A measure the portal will allow SUM on. Everything numeric qualifies EXCEPT the columns
# that are already a ratio or an average: summing "Average Price Per Unit" across rate
# schedules produces a number with no meaning, and the whole point of the trusted-measure
# guard is to refuse that before a client sees it. Taking the first five measures instead,
# as the first version did, was not a rule at all -- it just happened to exclude the right
# ones twice and the wrong ones everywhere else.
NOT_SUMMABLE = re.compile(r"\b(Average|Avg|Rate|Ratio|Percent|Per Unit|Per Device|%)\b|%",
                          re.I)
TEMPORAL = {"timestamp", "timestamp without time zone", "date",
            "timestamp with time zone"}


def load_contracts(dbt: Path) -> dict[str, dict[str, Any]]:
    """Parse _reporting.yml without a YAML dependency.

    The file is generated by build_data_dictionary.py in a fixed shape -- model name,
    description block, then a columns list of name/data_type/description -- so a targeted
    reader is more honest here than pulling in a parser and pretending the input is
    arbitrary YAML.
    """
    text = (dbt / "models" / "marts" / "reporting" / "_reporting.yml").read_text()
    out: dict[str, dict[str, Any]] = {}
    blocks = re.split(r"\n  - name: ", text)[1:]
    for b in blocks:
        name = b.split("\n", 1)[0].strip()
        desc = ""
        m = re.search(r"description: \|\n((?:      .*\n|\n)+)", b)
        if m:
            desc = "\n".join(line[6:] for line in m.group(1).rstrip().split("\n"))
        cols = []
        for cm in re.finditer(
            r'- name: "([^"]+)"\n\s+quote: true\n\s+data_type: (\S+)'
            r'(?:\n\s+description: "((?:[^"\\]|\\.)*)")?', b):
            cols.append({"name": cm.group(1), "type": cm.group(2),
                         "description": (cm.group(3) or "").replace('\\"', '"')})
        if cols:
            out[name] = {"description": desc, "columns": cols}
    return out


def grain_and_summary(desc: str) -> tuple[str, str, str]:
    """(grain, summary, use_case) from the canvas's own header prose.

    Written when the model was built and kept in the contract verbatim, which is why it
    is worth reading rather than restating: it already says what the canvas is for.
    """
    grain, summary, use_case = "", "", ""
    gm = re.search(r"GRAIN: one row per (.+?)\.", desc)
    if gm:
        grain = gm.group(1).strip()
    body = [l.strip() for l in desc.split("\n") if l.strip()]
    for i, line in enumerate(body):
        if "—" in line and line.split("—")[0].isupper():
            summary = line.split("—", 1)[1].strip().rstrip(".")
            if i + 2 < len(body):
                use_case = body[i + 2].rstrip(".")
            break
    if not summary:
        summary = next((l for l in body if not l.startswith("GRAIN")), "")[:200]
    return grain, summary, use_case[:240]


def label_of(col: str) -> str:
    return col


def classify(col: str, dtype: str) -> str:
    """dimension | measure | date, decided by TYPE.

    A boolean is a DIMENSION. It is a flag: something to split by or filter on, never
    something to sum -- and the dictionary already tells readers "filter on it; do not sum
    it". Classifying by name pattern, as the CISADM build did, needed an exception list
    to reach the same answer.
    """
    # Match the BASE type. The contract carries precision -- numeric(17,3),
    # varchar(60), timestamptz -- and comparing the whole string against a set of bare
    # names classified "Replacement Cost" as a dimension and left rpt_device_asset with
    # no measures at all.
    d = re.split(r"[(\s]", dtype.lower().strip())[0]
    if d.startswith("timestamp") or d == "date":
        return "date"
    if d in NUMERIC and not col.rstrip().endswith(" ID"):
        return "measure"
    return "dimension"


QUESTION_CATALOG = ROOT / "apps" / "analytics-portal" / "src" / "lib" / "c2m-question-catalog.js"

# The question catalogue's own vocabulary -> the portal's report library packs.
PACKS = {
    "customer": ("customer_operations", "Customer Operations",
                 "Who the utility serves, how they are reached, and whether they were told.",
                 "Customer service and billing operations"),
    "meter":    ("meter_and_assets", "Metering & Assets",
                 "The physical estate: devices, service points, installs and asset records.",
                 "Meter operations and asset management"),
    "usage":    ("usage_and_billing", "Usage & Billing",
                 "Measurement to charge: what was consumed, priced and billed.",
                 "Billing analysts and revenue assurance"),
    "financial":("financials", "Financials & Payments",
                 "Money in and money owed, through to the general ledger.",
                 "Finance and cashiering"),
    "credit":   ("credit_and_collections", "Credit & Collections",
                 "Arrears, collection processes, pay plans and the customers behind them.",
                 "Collections and credit risk"),
    "field":    ("field_and_operations", "Field & Operations",
                 "Field activity, device events, exceptions, work queues and batch.",
                 "Operations and field management"),
}


def parse_questions() -> list[dict[str, str]]:
    """Read the question catalogue's metadata.

    Only the metadata: the SQL in that file targets the canvases directly, while the
    portal builds its own query from dimensions and measures. Taking the SQL would
    bypass the governed query builder and its row caps, which is the one thing a
    client-facing app must not do.

    WHICH IS WHY A QUESTION MUST DECLARE ITS FILTERS SEPARATELY. Reading only the axis
    and the measure meant every WHERE clause in that file was dropped on the floor, and
    the tile the client saw was the unrestricted aggregate under the question's own
    words. "What was billed" says in its description that it counts frozen segments
    only; the chart counted cancelled and in-flight ones too. Worse, a revenue chart
    ranked "Payment Arrangement" top -- money that reschedules debt already billed
    elsewhere -- because the exclusion lived in SQL nobody here read. A caption that
    promises a restriction the query does not apply is the most expensive kind of wrong:
    it looks answered.

    Declared as metadata rather than parsed out of the SQL, because the query builder
    validates every field and operator it is handed, and a regex over a WHERE clause
    would be a second, weaker parser feeding the same governed path.
    """
    if not QUESTION_CATALOG.exists():
        return []
    text = QUESTION_CATALOG.read_text()
    out = []
    for block in text.split("\n  q({")[1:]:
        def field(name):
            m = re.search(name + r':\s*"((?:[^"\\]|\\.)*)"', block)
            return m.group(1).replace('\\"', '"') if m else ""

        def filters():
            m = re.search(r"filters:\s*(\[.*?\])\s*,\s*\n", block, re.S)
            if not m:
                return []
            try:
                # Written with quoted keys in the catalogue so it is JSON as well as JS.
                # A malformed literal returns no filters rather than raising: attach()
                # then drops the report, which is the same honest signal as a bad column.
                got = json.loads(m.group(1))
            except json.JSONDecodeError:
                return [{"field": "!malformed", "op": "eq", "value": None}]
            return got if isinstance(got, list) else []

        out.append({
            "id": field("id"), "title": field("title"), "why": field("why"),
            "canvas": field("canvas"), "axis": field("axis"), "value": field("value"),
            "kind": field("kind"), "process": field("process"),
            "workstream": field("workstream"), "target": field("target"),
            "filters": filters(),
        })
    return [q for q in out if q["id"] and q["canvas"]]


def attach_reports(snapshots: dict[str, Any]) -> list[dict[str, Any]]:
    """Turn the questions into premade reports, dropping any that do not validate.

    A question naming a column the canvas does not have is a question about an older
    model, and shipping it would put a broken tile in a client-facing library. Silently
    correcting it would be worse -- the count printed at the end is the honest signal.
    """
    CHART = {"total": "bar", "count": "bar", "distribution": "pie",
             "outlier": "bar", "ranking": "bar"}
    by_process: dict[str, list[dict[str, Any]]] = {}
    kept = dropped = 0

    for q in parse_questions():
        snap = snapshots.get(q["canvas"])
        if not snap:
            dropped += 1
            continue
        dims = {d["id"] for d in snap["dimensions"]}
        meas = {m["id"] for m in snap["measures"]}
        if q["axis"] not in dims:
            dropped += 1
            continue
        # The value column is a measure where the canvas has one, and a row count
        # otherwise -- a question like "how many accounts" has no measure to sum.
        if q["value"] in meas:
            measure = {"field": q["value"], "agg": "max" if q["kind"] == "outlier" else "sum"}
        else:
            measure = {"field": "*", "agg": "count"}
        # A filter is held to the same standard as the axis: it must name a real field on
        # this canvas, or the question is about an older model and the whole report is
        # dropped. Filters may reference a boolean the canvas exposes as a dimension, or
        # any other selectable field, so both sets count as valid.
        selectable = dims | meas
        bad_filter = any(
            not isinstance(f, dict) or f.get("field") not in selectable
            for f in q["filters"]
        )
        if bad_filter:
            dropped += 1
            continue
        report = {
            "id": q["id"].replace("-", "_"),
            "title": q["title"],
            "description": q["why"],
            "dimensions": [q["axis"]],
            "measures": [measure],
            "filters": q["filters"],
            "chart_type": CHART.get(q["kind"], "bar"),
            "workstream_label": q["workstream"],
        }
        if q["target"]:
            report["benchmark"] = q["target"]
        snap["premade_reports"].append(report)
        by_process.setdefault(q["process"], []).append(
            {"snapshot_id": q["canvas"], "report_id": report["id"]})
        kept += 1

    packs = []
    for proc, refs in by_process.items():
        pid, title, desc, audience = PACKS.get(
            proc, (proc, proc.title(), "", "All users"))
        packs.append({"id": pid, "title": title, "description": desc,
                      "audience": audience, "reports": refs})
    print(f"  question catalogue: {kept} reports attached, {dropped} dropped "
          f"(column not on the canvas)")
    return packs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dbt-project", type=Path, default=DEFAULT_DBT)
    # catalog_dbt.json, NOT snapshot_explorer_catalog.json. The catalogs were split per
    # engine when tenants started choosing between them; leaving the old default here
    # meant every regeneration wrote a file nothing reads, and the API went on serving a
    # stale catalog with no sign that the build had done nothing.
    ap.add_argument("--out", type=Path, default=ROOT / "output" / "catalog_dbt.json")
    ap.add_argument("--client", default="originba")
    args = ap.parse_args()

    dbt = args.dbt_project.expanduser()
    contracts = load_contracts(dbt)
    lin_path = dbt / "docs" / "column_lineage.json"
    lineage = json.loads(lin_path.read_text()) if lin_path.exists() else {}

    snapshots: dict[str, dict[str, Any]] = {}
    for canvas, spec in sorted(contracts.items()):
        ws = WORKSTREAM.get(canvas, "common")
        grain, summary, use_case = grain_and_summary(spec["description"])

        fields, dims, meas, dates = [], [], [], []
        for c in spec["columns"]:
            role = classify(c["name"], c["type"])
            fields.append({"id": c["name"], "label": label_of(c["name"]),
                           "type": c["type"], "role": role,
                           "group": ws, "description": c["description"]})
            if role == "measure":
                meas.append({"id": c["name"], "label": c["name"],
                             "aggs": ["sum", "avg", "min", "max"]})
            elif role == "date":
                dates.append({"id": c["name"], "label": c["name"]})
            else:
                dims.append({"id": c["name"], "label": c["name"]})
        meas.insert(0, {"id": "*", "label": "Number of records", "aggs": ["count"]})

        # The lineage IS the data model here. The CISADM build parsed refresh SQL to
        # guess at source tables; this is generated from the models themselves.
        cl = lineage.get(canvas, {})
        sources = sorted({v["source_table"].upper() for v in cl.values()
                          if v.get("source_table")})
        traced = sum(1 for v in cl.values() if v.get("source_column"))

        snapshots[canvas] = {
            "table_name": canvas,
            "schema": "reporting",
            "workstream": ws,
            "workstream_label": WORKSTREAM_LABELS[ws],
            "label": canvas.replace("rpt_", "").replace("_", " ").title(),
            "grain": grain or canvas,
            "grain_description": f"One row per {grain}" if grain else "",
            "summary": summary,
            "use_case": use_case,
            # NO MANDATORY DATE WINDOW on a dbt canvas, and this is a design decision
            # rather than an omission. The portal REQUIRES a filter on
            # required_date_field and injects a default preset when the caller sends
            # none. That guard exists for the raw CISADM snapshots, which are millions of
            # rows and must never be scanned whole.
            #
            # A canvas is not that. It is contract-governed, grain-asserted and row-capped
            # already. Auto-picking its first date column and forcing a window on it
            # silently emptied results: rpt_aged_debt got "Oldest Charge Date in Band",
            # a per-band derived date, and every query came back with zero rows and no
            # error to say why. Worse, half the canvases -- rate configuration, asset
            # locations, the price list -- are dimension tables where a transaction window
            # means nothing at all.
            #
            # Date fields stay in date_fields for OPTIONAL filtering. The portal's own
            # row cap is what protects the database.
            "required_date_label": None,
            "trusted_measures": [m["id"] for m in meas[1:]
                                 if not NOT_SUMMABLE.search(m["id"])],
            "required_date_field": None,
            "fields": fields,
            "dimensions": dims,
            "measures": meas,
            "date_fields": dates,
            "default_date_field": dates[0]["id"] if dates else None,
            "premade_reports": [],          # filled below from the question catalogue
            "scope_filters": [],
            "usage_guidance": None,
            "related_snapshot": None,
            "max_rows": 500,
            "portal_enabled": True,
            "poc_enabled": True,
            "large_domain": False,
            "skip_sample_rows": False,
            "default_date_preset": "last_12_months",
            "data_model": {
                "snapshot_table": f"reporting.{canvas}",
                "domain_table": canvas,
                "grain": grain or canvas,
                "grain_description": f"One row per {grain}" if grain else "",
                "grain_preservation": (
                    "Grain is asserted by a singular test in the dbt project, so a join "
                    "that multiplied this population would fail the build."),
                "trusted_measures": [m["id"] for m in meas[1:]
                                     if not NOT_SUMMABLE.search(m["id"])],
                "driving_table": sources[0] if sources else None,
                "source_tables": sources,
                "join_paths": [],
                "population_filter": None,
                "refresh_sql": f"models/marts/reporting/{canvas}.sql",
                "columns_traced_to_cisadm": traced,
                "field_groups": [{"id": ws, "label": WORKSTREAM_LABELS[ws],
                                  "fields": [f["id"] for f in fields]}],
            },
        }

    packs = attach_reports(snapshots)

    catalog = {
        "client": args.client,
        "source": "dbt reporting layer",
        "workstream_order": WORKSTREAM_ORDER,
        "workstream_labels": WORKSTREAM_LABELS,
        "portal_snapshots": sorted(snapshots),
        "poc_enabled": sorted(snapshots),
        "workstream_featured": {
            ws: sorted(c for c, s in snapshots.items() if s["workstream"] == ws)[:4]
            for ws in WORKSTREAM_ORDER
        },
        "report_library_packs": packs,
        "business_processes": [],
        "snapshots": snapshots,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(catalog, indent=1, sort_keys=True))
    nd = sum(len(s["dimensions"]) for s in snapshots.values())
    nm = sum(len(s["measures"]) - 1 for s in snapshots.values())
    try:
        shown = args.out.relative_to(ROOT)
    except ValueError:
        shown = args.out
    print(f"{shown}  {len(snapshots)} canvases from the dbt "
          f"reporting layer: {nd} dimensions, {nm} measures, "
          f"{sum(len(s['date_fields']) for s in snapshots.values())} date fields")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
