#!/usr/bin/env python3
"""
Generate Jaspersoft Domain schema XML for consolidation snapshot tables.

Reads 01_create_snapshot_table.sql, builds End_User_Friendly domain XML,
and writes copies to:
  - domains/exports/manual_imports/<TABLE>_End_User_Friendly.xml
  - sql/performance/snapshots/<path>/<TABLE>_End_User_Friendly.xml

Usage:
  python3 scripts/build_consolidation_domain_xml.py
  python3 scripts/build_consolidation_domain_xml.py --snapshot ACCT_CUSTOMER_RPT_CURR
"""

from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
NS = "http://www.jaspersoft.com/2007/SL/XMLSchema"
ET.register_namespace("", NS)

LABEL_TOKENS = {
    "ACCT": "Account",
    "SA": "Service Agreement",
    "D1": "D1",
    "DVC": "Device",
    "SP": "Service Point",
    "PREM": "Premise",
    "PER": "Person",
    "CRE": "Create",
    "DTTM": "Date Time",
    "DT": "Date",
    "CD": "Code",
    "DESC": "Description",
    "FLG": "Code",
    "AMT": "Amount",
    "BAL": "Balance",
    "CNT": "Count",
    "NBR": "Number",
    "ID": "ID",
    "UPR": "Uppercase",
    "EXCP": "Exception",
    "BSEG": "Bill Segment",
    "VEE": "VEE",
    "TD": "To-Do",
    "FK": "Foreign Key",
    "CFG": "Configuration",
    "EVT": "Event",
    "FA": "Field Activity",
    "PP": "Pay Plan",
    "TNDR": "Tender",
    "DEP": "Deposit",
    "WO": "Write Off",
    "ARS": "Arrears",
    "ILM": "Installment",
    "SW": "Switch",
    "TM": "Time",
    "MINS": "Minutes",
    "DAYS": "Days",
    "HOURS": "Hours",
    "MR": "Meter Read",
    "CC": "Customer Contact",
    "LL": "Landlord",
    "NB": "New Business",
    "FT": "Financial Transaction",
    "USG": "Usage",
    "US": "Usage Subscription",
    "BO": "Business Object",
    "STAT": "Status",
    "RSN": "Reason",
    "TMPL": "Template",
    "CTL": "Control",
    "SRC": "Source",
    "SRCE": "Source",
    "GEO": "Geo",
    "LAT": "Latitude",
    "LONG": "Longitude",
    "MDM": "MDM",
    "MXU": "MXU",
    "NIC": "NIC",
    "APPT": "Appointment",
    "APPOINTMENT": "Appointment",
    "MSRMT": "Measurement",
    "DIV": "Division",
    "MKT": "Market",
    "CYC": "Cycle",
    "RTE": "Route",
    "LS": "Line",
    "SL": "Service Line",
    "INT": "Internal",
    "EXT": "External",
    "REF": "Reference",
    "PROC": "Process",
    "QUEUE": "Queue",
    "BATCH": "Batch",
    "THREAD": "Thread",
    "INST": "Instance",
    "REC": "Record",
    "ERR": "Error",
    "RETRY": "Retry",
    "LOG": "Log",
    "FILE": "File",
    "DUR": "Duration",
    "COMPL": "Completion",
    "TRIGGER": "Trigger",
    "CRIT": "Critical",
    "PRIO": "Priority",
    "UNCOLL": "Uncollectible",
    "GOVERNED": "Governed",
    "OLDEST": "Oldest",
    "NEWEST": "Newest",
    "CHAR": "Characteristic",
    "SIC": "SIC",
    "ENRL": "Enrollment",
    "PROP": "Proposal",
    "STALE": "Stale",
    "PENDING": "Pending",
    "REVIEW": "Review",
    "SEVERITY": "Severity",
    "OPEN": "Open",
    "CLOSE": "Close",
    "NATURAL": "Natural",
    "KEY": "Key",
    "ANCHOR": "Anchor",
    "ASSIGNED": "Assigned",
    "COMPLETE": "Complete",
    "UNASSIGNED": "Unassigned",
    "MESSAGE": "Message",
    "SCHEDULER": "Scheduler",
    "RERUN": "Rerun",
    "RESTART": "Restart",
    "DO": "Do",
    "NOT": "Not",
    "PHONE": "Phone",
    "EMAIL": "Email",
    "ADDR": "Address",
    "CUST": "Customer",
    "COLL": "Collection",
    "BUD": "Budget",
    "PLAN": "Plan",
    "CIS": "CIS",
    "DIVISION": "Division",
    "CURRENCY": "Currency",
    "ACCESS": "Access",
    "GRP": "Group",
    "MAILING": "Mailing",
    "POSTPONE": "Postpone",
    "PROTECT": "Protect",
    "INFO": "Information",
    "BUS": "Business",
    "OR": "Or",
    "HOME": "Home",
    "CELL": "Cell",
    "WORK": "Work",
    "PRIMARY": "Primary",
    "LATEST": "Latest",
    "EARLIEST": "Earliest",
    "TOTAL": "Total",
    "ACTIVE": "Active",
    "DISTINCT": "Distinct",
    "SOLE": "Sole",
    "LANDLORD": "Landlord",
    "AGREEMENT": "Agreement",
    "LOAD": "Load",
    "SNAPSHOT": "Snapshot",
    "TYPE": "Type",
    "STATUS": "Status",
    "NAME": "Name",
    "USER": "User",
    "CONTACT": "Contact",
    "INSTR": "Instruction",
    "COMMENT": "Comment",
    "COMMENTS": "Comments",
    "PERSON": "Person",
    "TREND": "Trend",
    "AREA": "Area",
    "TIME": "Time",
    "ZONE": "Zone",
    "CITY": "City",
    "LIMIT": "Limit",
    "OK": "OK",
    "TO": "To",
    "ENTER": "Enter",
    "FIRST": "First",
    "ENTITY": "Entity",
    "METH": "Method",
    "CLOSED": "Closed",
    "MINUTES": "Minutes",
    "DURATION": "Duration",
    "RESP": "Responsible",
    "CASE": "Case",
    "COND": "Condition",
    "SVC": "Service",
    "START": "Start",
    "END": "End",
    "EXPIRE": "Expire",
    "RENEWAL": "Renewal",
    "OPT": "Option",
    "STRT": "Start",
    "STOP": "Stop",
    "REQED": "Requested",
    "BY": "By",
    "RULE": "Rule",
    "SPECIAL": "Special",
    "USAGE": "Usage",
    "BILL": "Bill",
    "PRT": "Print",
    "INTERCEPT": "Intercept",
    "POSTAL": "Postal",
    "COUNTY": "County",
    "COUNTRY": "Country",
    "UNTIL": "Until",
    "SINCE": "Since",
    "CREATED": "Created",
    "ACTIVITY": "Activity",
    "PARENT": "Parent",
    "CANCEL": "Cancel",
    "FIELD": "Field",
    "TASK": "Task",
    "RESCHEDULE": "Reschedule",
    "RETENTION": "Retention",
    "EFF": "Effective",
    "COMPLETED": "Completed",
    "TAKEN": "Taken",
    "WINDOW": "Window",
    "PICKUP": "Pickup",
    "REQUESTER": "Requester",
    "CELLPHONE": "Cell Phone",
    "CONT": "Contact",
    "MAINPHONE": "Main Phone",
    "EXPIRATION": "Expiration",
    "REFERENCE": "Reference",
    "PRIORITY": "Priority",
    "THRD": "Third",
    "PTY": "Party",
    "REP": "Representative",
    "DISCONN": "Disconnect",
    "LOC": "Location",
    "PREM": "Premise",
    "CREW": "Crew",
    "WORKER": "Worker",
    "CAPABILITY": "Capability",
    "AVG": "Average",
    "OLDEST": "Oldest",
    "OPEN": "Open",
    "DEVICE": "Device",
    "MANUFACTURER": "Manufacturer",
    "MODEL": "Model",
    "SPR": "Service Provider",
    "ARMING": "Arming",
    "HEAD": "Head",
    "REGISTR": "Registration",
    "REGISTR_STATUS": "Registration Status",
    "SHIFT": "Shift",
    "CMD": "Command",
    "SET": "Set",
    "SERIAL": "Serial",
    "BADGE": "Badge",
    "UTILITY": "Utility",
    "IDENTIFIER": "Identifier",
    "ASSET": "Asset",
    "OWNERSHIP": "Ownership",
    "SPECIFICATION": "Specification",
    "ACQUISITION": "Acquisition",
    "INSTALL": "Install",
    "REMOVAL": "Removal",
    "ARM": "Arm",
    "CURRENTLY": "Currently",
    "INSTALLED": "Installed",
    "PAY": "Payment",
    "DOC": "Document",
    "CAN": "Cancel",
    "MATCH": "Match",
    "VAL": "Value",
    "NON": "Non",
    "DISTINCT": "Distinct",
    "CHARGE": "Charge",
    "LINE": "Line",
    "BILLABLE": "Billable",
    "CHG": "Charge",
    "SHOW": "Show",
    "ON": "On",
    "APP": "Application",
    "IN": "In",
    "SUMM": "Summary",
    "DST": "Distribution",
    "MEMO": "Memo",
    "DEBT": "Debt",
    "CL": "Class",
    "GOVERNED": "Governed",
    "OVER": "Over",
    "AGE": "Age",
    "COMPL": "Completion",
    "DIFF": "Difference",
    "INACTIVE": "Inactive",
    "NEXT": "Next",
    "EVENT": "Event",
    "SEQ": "Sequence",
    "SOURCE": "Source",
    "ENTRY": "Entry",
    "ROLE": "Role",
    "BATCH": "Batch",
    "RUN": "Run",
    "TEXT": "Text",
    "DETAILS": "Details",
}


@dataclass(frozen=True)
class GroupRule:
    group_id: str
    group_label: str
    patterns: tuple[str, ...]


@dataclass(frozen=True)
class SnapshotSpec:
    table: str
    label: str
    rel_dir: str
    keys: tuple[str, ...]
    rules: tuple[GroupRule, ...]


def _label_for_column(col: str) -> str:
    if col == "LOAD_DTTM":
        return "Snapshot Load Date Time"
    parts = col.upper().split("_")
    out: list[str] = []
    i = 0
    while i < len(parts):
        matched = False
        for size in (3, 2, 1):
            if i + size <= len(parts):
                token = "_".join(parts[i : i + size])
                if token in LABEL_TOKENS:
                    out.append(LABEL_TOKENS[token])
                    i += size
                    matched = True
                    break
        if not matched:
            out.append(parts[i].title())
            i += 1
    label = " ".join(out)
    if col.endswith("_desc"):
        label = label.replace(" Description", "") if label.endswith(" Description") else label
        if not label.endswith("Description"):
            label = label + " Description" if "Desc" in label else label
    if col.endswith("_cd") and not label.endswith("Code"):
        label = label.replace(" Code", "") + " Code" if "Code" not in label else label
    if col.endswith("_flg") and not label.endswith("Code"):
        label = label + " Code" if not label.endswith("Code") else label
    if col.endswith("_sw") and not label.endswith("Switch"):
        label = label + " Switch" if not label.endswith("Switch") else label
    if col.endswith("_id") and not label.endswith("ID"):
        label = label + " ID" if not label.endswith(" ID") else label
    if col.endswith("_dt") and "Date" not in label:
        label = label + " Date"
    if col.endswith("_dttm") and "Date Time" not in label:
        label = label + " Date Time"
    if col.endswith("_amt") and "Amount" not in label:
        label = label + " Amount"
    if col.endswith("_count") and "Count" not in label:
        label = label + " Count"
    return re.sub(r"\s+", " ", label).strip()


def _oracle_type_to_java(oracle_type: str) -> str:
    t = oracle_type.upper()
    if t.startswith("VARCHAR") or t.startswith("CHAR"):
        return "java.lang.String"
    if t.startswith("NUMBER"):
        return "java.math.BigDecimal"
    if t.startswith("DATE") or t.startswith("TIMESTAMP"):
        return "java.sql.Timestamp"
    return "java.lang.String"


def parse_create_table(path: Path) -> list[tuple[str, str]]:
    text = path.read_text(encoding="utf-8")
    cols: list[tuple[str, str]] = []
    for line in text.splitlines():
        m = re.match(r"^\s+([a-z0-9_]+)\s+([A-Z0-9]+(?:\([^)]*\))?)", line, re.I)
        if not m:
            continue
        name, typ = m.group(1).upper(), m.group(2)
        if name in {"CONSTRAINT", "PRIMARY", "UNIQUE", "CHECK", "FOREIGN"}:
            continue
        cols.append((name, typ.split("(")[0].upper()))
    return cols


def assign_groups(columns: Iterable[str], spec: SnapshotSpec) -> dict[str, list[str]]:
    remaining = list(columns)
    grouped: dict[str, list[str]] = {}

    def take(rule: GroupRule) -> None:
        grouped.setdefault(rule.group_id, [])
        kept: list[str] = []
        for col in remaining:
            if any(col == p or col.startswith(p) for p in rule.patterns):
                grouped[rule.group_id].append(col)
            else:
                kept.append(col)
        remaining[:] = kept

    for rule in spec.rules:
        take(rule)

    if remaining:
        grouped.setdefault("GENERAL", [])
        grouped["GENERAL"].extend(remaining)
    return grouped


def _sub(parent: ET.Element, tag: str, **attrs: str) -> ET.Element:
    el = ET.SubElement(parent, f"{{{NS}}}{tag}")
    for k, v in attrs.items():
        el.set(k, v)
    return el


def build_xml(spec: SnapshotSpec, columns: list[tuple[str, str]]) -> ET.ElementTree:
    col_names = [c for c, _ in columns]
    rule_by_id = {r.group_id: r for r in spec.rules}
    grouped = assign_groups(col_names, spec)

    schema = ET.Element(f"{{{NS}}}schema", {"version": "1.3"})

    data_islands = _sub(schema, "dataIslands")
    _sub(
        data_islands,
        "itemGroup",
        id=spec.table,
        label=spec.label,
        resourceId=spec.table,
    )

    data_sources = _sub(schema, "dataSources")
    ds = _sub(data_sources, "jdbcDataSource", id="Origin_DEV_DS")
    schema_map = _sub(ds, "schemaMap")
    entry_default = _sub(schema_map, "entry", key="defaultSchema")
    _sub(entry_default, "string")
    entry_cis = _sub(schema_map, "entry", key="CISADM")
    _sub(entry_cis, "string").text = "CISADM"

    item_groups = _sub(schema, "itemGroups")
    group_order = [r.group_id for r in spec.rules if r.group_id in grouped]
    if "GENERAL" in grouped:
        group_order.append("GENERAL")

    for gid in group_order:
        cols_in_group = grouped.get(gid, [])
        if not cols_in_group:
            continue
        glabel = rule_by_id.get(gid, GroupRule(gid, "General", ())).group_label
        if gid == "GENERAL":
            glabel = "Additional Fields"
        grp = _sub(
            item_groups,
            "itemGroup",
            id=f"{spec.table}_{gid}",
            label=glabel,
            resourceId=spec.table,
        )
        items = _sub(grp, "items")
        for col in cols_in_group:
            _sub(
                items,
                "item",
                id=col,
                label=_label_for_column(col),
                resourceId=f"{spec.table}.{col}",
            )

    resources = _sub(schema, "resources")
    jdbc = _sub(
        resources,
        "jdbcTable",
        id=spec.table,
        datasourceId="Origin_DEV_DS",
        datasourceTableName=spec.table,
        schemaAlias="CISADM",
    )
    field_list = _sub(jdbc, "fieldList")
    for col, ora_type in columns:
        _sub(field_list, "field", id=col, type=_oracle_type_to_java(ora_type))

    return ET.ElementTree(schema)


def _rule(gid: str, label: str, *patterns: str) -> GroupRule:
    return GroupRule(gid, label, patterns)


SPECS: list[SnapshotSpec] = [
    SnapshotSpec(
        "ACCT_CUSTOMER_RPT_CURR",
        "Account Customer Snapshot",
        "customer_ops/acct_customer",
        ("ACCT_ID",),
        (
            _rule("AUDIT", "Snapshot Audit", "LOAD_DTTM"),
            _rule("ACCOUNT", "Account", "ACCT_", "SETUP_DT", "BILL_CYC_", "CUST_CL_", "COLL_CL_",
                  "ACCT_MGMT_", "BUD_PLAN_", "CIS_DIVISION", "CURRENCY_CD", "ACCESS_GRP_", "MAILING_",
                  "BILL_AFTER_DT", "CR_REVIEW_", "POSTPONE_", "INT_CR_", "NO_DEP_", "PROTECT_", "ALERT_INFO"),
            _rule("CUSTOMER", "Customer And Contact", "PER_ID", "CUSTOMER_", "BILL_RTE_", "PER_OR_BUS_",
                  "ADDRESS", "CITY", "STATE", "POSTAL", "COUNTRY", "EMAIL", "LS_SL_", "HOME_PHONE",
                  "CELL_PHONE", "WORK_PHONE", "PRIMARY_EMAIL"),
            _rule("ALERTS", "Account Alerts", "ALERT_COUNT", "OPEN_ALERT", "LATEST_ALERT"),
            _rule("SA_SUMMARY", "Service Agreement Summary", "ACTIVE_SA_", "TOTAL_SA_", "DISTINCT_ACTIVE",
                  "SOLE_ACTIVE", "EARLIEST_SA_", "LATEST_SA_"),
            _rule("LANDLORD", "Landlord", "LANDLORD_", "PRIMARY_LL_"),
        ),
    ),
    SnapshotSpec(
        "CASE_PREM_CONTACT_RPT_CURR",
        "Case Premise Contact Snapshot",
        "customer_ops/case_prem_contact",
        ("CASE_ID",),
        (
            _rule("AUDIT", "Snapshot Audit", "LOAD_DTTM"),
            _rule("CASE", "Case", "CASE_"),
            _rule("CONTACT", "Customer Contact", "CONTACT_", "PHONE", "EXTENSION", "COMMENT_",
                  "USER_ID", "RESP_", "CASE_PERSON_"),
            _rule("ACCOUNT", "Account", "ACCT_"),
            _rule("PREMISE", "Premise", "PREM_"),
            _rule("CC", "Customer Contact History", "CC_", "FIRST_CC_", "LATEST_CC_"),
        ),
    ),
    SnapshotSpec(
        "NEW_SERVICE_PIPELINE_RPT_CURR",
        "New Service Pipeline Snapshot",
        "new_services/pipeline",
        ("SA_ID",),
        (
            _rule("AUDIT", "Snapshot Audit", "LOAD_DTTM"),
            _rule("SA", "Service Agreement", "SA_", "PROP_SA_", "ENRL_", "SA_REL_", "OLD_ACCT_",
                  "CURRENCY_CD", "START_", "END_", "EXPIRE_", "RENEWAL_", "CRE_DTTM", "STRT_", "STOP_",
                  "NB_", "SIC_", "SPECIAL_USAGE_", "CHAR_PREM_"),
            _rule("ACCOUNT", "Account And Customer", "ACCT_", "PER_ID", "CUSTOMER_", "BILL_CYC_",
                  "COLL_CL_", "CUST_CL_", "BUD_PLAN_", "BILL_PRT_"),
            _rule("PREMISE", "Premise", "PREM_", "ADDRESS", "CITY", "STATE", "POSTAL", "COUNTY",
                  "COUNTRY", "TREND_", "MR_", "TIME_ZONE_", "IN_CITY_"),
            _rule("PIPELINE", "Pipeline Metrics", "FT_BAL_", "DAYS_", "STALE_"),
        ),
    ),
    SnapshotSpec(
        "FIELD_ACTIVITY_RPT_CURR",
        "Field Activity Snapshot",
        "field_ops/field_activity",
        ("D1_ACTIVITY_ID",),
        (
            _rule("AUDIT", "Snapshot Audit", "LOAD_DTTM"),
            _rule("ACTIVITY", "Field Activity", "D1_ACTIVITY_", "PARENT_", "ACTIVITY_", "ACT_",
                  "BO_STATUS_", "BUS_OBJ_", "CANCEL_", "FIELD_TASK_", "RESCHEDULE_", "RETENTION_",
                  "EFF_", "START_", "END_", "STATUS_UPD_", "DAYS_"),
            _rule("APPOINTMENT", "Appointment", "APPOINTMENT_", "CM_ML_"),
            _rule("CONTACT", "Activity Contact", "COMMENTS", "CR_", "REQUESTER_", "D1_CELL", "D1_CONT",
                  "D1_CONTACT", "D1_CUSTOMER", "D1_INSTR", "D1_MAIN", "EMAIL_", "EXPIRATION_",
                  "EXT_", "EXTERNAL_", "FA_INT_", "FA_PRIORITY_", "THRD_"),
            _rule("SERVICE_POINT", "D1 Service Point", "D1_SP_", "ACCESS_GRP_", "SP_BO_", "SP_BUS_",
                  "DIVISION_", "MKT_", "MSRMT_", "DISCONN_", "SP_SRC_", "D1_LS_", "D1_GEO_", "SP_ADDRESS",
                  "SP_CITY", "SP_STATE", "SP_POSTAL", "POSTAL_5", "SP_COUNTY", "SP_COUNTRY", "TIME_ZONE_",
                  "IN_CITY_"),
            _rule("PREMISE_ACCOUNT", "Premise And Account", "SP_ID", "PREM_", "ACCT_"),
        ),
    ),
    SnapshotSpec(
        "CREW_OPS_RPT_CURR",
        "Crew Operations Snapshot",
        "field_ops/crew_ops",
        ("CREW_ID",),
        (
            _rule("AUDIT", "Snapshot Audit", "LOAD_DTTM"),
            _rule("CREW", "Crew", "CREW_", "BO_STATUS_", "BUS_OBJ_", "REP_", "NT_XID_"),
            _rule("WORKER", "Worker", "PER_ID", "USER_", "SVC_AREA", "WORKER_"),
            _rule("FA_METRICS", "Field Activity Metrics", "FA_", "COMPLETED_FA_", "OPEN_FA_",
                  "DISTINCT_FA_", "LATEST_FA_", "OLDEST_OPEN_", "AVG_DAYS_"),
        ),
    ),
    SnapshotSpec(
        "DEVICE_SP_RPT_CURR",
        "Device Service Point Snapshot",
        "meter_ops/device_sp",
        ("D1_DVC_ID",),
        (
            _rule("AUDIT", "Snapshot Audit", "LOAD_DTTM"),
            _rule("DEVICE", "Device", "D1_DVC_", "DEVICE_", "DVC_", "MANUFACTURER_", "D1_MODEL_",
                  "MODEL_", "D1_SPR_", "SPR_", "ACCESS_GRP_", "ARMING_", "HEAD_END_", "IN_DATA_",
                  "D1_CMD_", "CMD_"),
            _rule("IDENTIFIERS", "Device Identifiers", "ASSET_ID", "SERIAL_", "BADGE_", "EXTERNAL_",
                  "UTILITY_", "IDENTIFIER_", "MDM_"),
            _rule("ASSET", "Asset", "ASSET_", "MXU_"),
            _rule("CONFIG", "Device Configuration", "DEVICE_CONFIG_", "CFG_"),
            _rule("INSTALL", "Install Event", "INSTALL_", "REMOVAL_", "ARM_STAT_"),
            _rule("SERVICE_POINT", "Service Point And Premise", "D1_SP_", "SP_", "DIVISION_", "MKT_",
                  "MSRMT_", "CI_SP_", "PREM_"),
            _rule("USAGE_SUBSCRIPTION", "Usage Subscription", "US_", "ACTIVE_US_", "INSTALL_EVENT_",
                  "DEVICE_CONFIG_COUNT", "CURRENTLY_INSTALLED_"),
        ),
    ),
    SnapshotSpec(
        "PAY_EVENT_RPT_CURR",
        "Payment Event Snapshot",
        "payments_cashiering/pay_event",
        ("PAY_ID",),
        (
            _rule("AUDIT", "Snapshot Audit", "LOAD_DTTM"),
            _rule("PAYMENT", "Payment", "PAY_", "DOC_", "DAYS_OLD"),
            _rule("ACCOUNT", "Account And Customer", "ACCT_", "PER_ID", "CUSTOMER_"),
            _rule("TENDER", "Tender Summary", "EVENT_TENDER_", "DISTINCT_TENDER_", "SOLE_TENDER_"),
            _rule("TENDER_CONTROL", "Tender Control", "EVENT_TNDR_", "PRIMARY_TNDR_"),
            _rule("DEPOSIT", "Deposit Control", "EVENT_DEP_", "PRIMARY_DEP_"),
            _rule("PAY_PLAN", "Pay Plan", "ACCT_PP_", "ACTIVE_PP_", "PRIMARY_PP_"),
        ),
    ),
    SnapshotSpec(
        "BILLABLE_CHARGE_RPT_CURR",
        "Billable Charge Snapshot",
        "finance/billable_charge",
        ("BILLABLE_CHG_ID", "LINE_SEQ"),
        (
            _rule("AUDIT", "Snapshot Audit", "LOAD_DTTM"),
            _rule("CHARGE", "Charge Line", "BILLABLE_", "LINE_", "CHARGE_", "BILL_CHG_", "ILM_",
                  "SHOW_ON_", "APP_IN_", "DST_", "MEMO_"),
            _rule("SA_ACCOUNT", "Service Agreement And Account", "SA_", "ACCT_", "CHAR_PREM_",
                  "PER_ID", "CUSTOMER_", "CIS_DIVISION"),
            _rule("CLASSIFICATION", "Classification", "BILL_CYC_", "COLL_CL_", "CUST_CL_", "BUD_PLAN_"),
        ),
    ),
    SnapshotSpec(
        "SA_AGED_BAL_RPT_CURR",
        "SA Aged Balance Snapshot",
        "debt_mgmt/sa_aged_bal",
        ("SA_ID",),
        (
            _rule("AUDIT", "Snapshot Audit", "LOAD_DTTM"),
            _rule("SA", "Service Agreement", "SA_", "DEBT_CL_", "CHAR_PREM_", "GOVERNED_"),
            _rule("ACCOUNT", "Account And Customer", "ACCT_", "PER_ID", "CUSTOMER_"),
            _rule("CLASSIFICATION", "Classification", "BILL_CYC_", "COLL_CL_", "CUST_CL_",
                  "ACCT_MGMT_", "BUD_PLAN_"),
            _rule("PREMISE", "Premise", "PREM_", "ADDRESS", "CITY", "STATE", "POSTAL"),
            _rule("DEBT", "Debt Buckets", "TOTAL_DEBT", "DEBT_0_", "DEBT_31_", "DEBT_61_",
                  "DEBT_OVER_", "OLDEST_", "NEWEST_"),
        ),
    ),
    SnapshotSpec(
        "WO_PROC_RPT_CURR",
        "Write Off Process Snapshot",
        "debt_mgmt/wo_proc",
        ("WO_PROC_ID",),
        (
            _rule("AUDIT", "Snapshot Audit", "LOAD_DTTM"),
            _rule("PROCESS", "Write Off Process", "WO_PROC_", "WO_CNTL_", "WO_STATUS_", "WO_STAT_",
                  "UNCOLL_", "CRIT_", "TRIGGER_", "COMMENTS", "PROCESS_", "DAYS_OLD"),
            _rule("ACCOUNT", "Account And Customer", "ACCT_", "PER_ID", "CUSTOMER_", "CURRENCY_CD"),
            _rule("ARREARS", "Arrears Amounts", "ARS_"),
            _rule("SA_SUMMARY", "Write Off SA Summary", "WO_SA_"),
            _rule("CLASSIFICATION", "Classification", "BILL_CYC_", "COLL_CL_", "CUST_CL_",
                  "ACCT_MGMT_", "BUD_PLAN_"),
            _rule("EVENTS", "Process Events", "EVENT_", "OPEN_EVENT_", "COMPLETED_EVENT_",
                  "FIRST_", "LAST_", "NEXT_", "LATEST_"),
        ),
    ),
    SnapshotSpec(
        "OPS_EXCEPTION_RPT_CURR",
        "Operations Exception Snapshot",
        "common/ops_exception",
        ("EXCP_SOURCE", "EXCP_NATURAL_KEY"),
        (
            _rule("AUDIT", "Snapshot Audit", "LOAD_DTTM"),
            _rule("EXCEPTION", "Exception Header", "EXCP_", "OPEN_CLOSE_", "EXCP_SEVERITY_",
                  "BUS_OBJ_", "BO_STATUS_", "STATUS_UPD_"),
            _rule("BSEG", "Bill Segment Exception", "BSEG_"),
            _rule("ACCOUNT", "Account Context", "SA_ID", "ACCT_", "CUSTOMER_", "BILL_CYC_",
                  "CUST_CL_", "COLL_CL_", "ACCT_MGMT_", "BUD_PLAN_", "SA_TYPE_", "SA_STATUS_"),
            _rule("USAGE", "Usage Exception", "USAGE_", "D1_USAGE_", "USG_", "USG_RULE_"),
            _rule("VEE", "VEE Exception", "VEE_", "INIT_MSRMT_", "EXCP_TYPE_"),
            _rule("SERVICE_POINT", "Service Point Context", "D1_SP_", "SP_"),
            _rule("TODO", "To-Do Linkage", "TD_"),
        ),
    ),
    SnapshotSpec(
        "WORKFLOW_QUEUE_RPT_CURR",
        "Workflow Queue Snapshot",
        "common/workflow_queue",
        ("QUEUE_SOURCE", "QUEUE_NATURAL_KEY"),
        (
            _rule("AUDIT", "Snapshot Audit", "LOAD_DTTM"),
            _rule("QUEUE", "Queue Keys", "QUEUE_"),
            _rule("TODO", "To-Do Entry", "TD_", "ENTRY_", "ROLE_", "ASSIGNED_", "COMPLETE_",
                  "MESSAGE_", "DAYS_OLD", "ASSIGNED_TM_", "COMPLETE_TM_", "UNASSIGNED_TM_"),
            _rule("FK_OVERLAY", "Foreign Key Overlay", "FK_"),
            _rule("PERSON_PREMISE", "Person And Premise", "PERSON_", "PREM_"),
            _rule("PREMISE_ATTR", "Premise Attributes", "TREND_", "TIME_ZONE_", "POSTAL_5"),
            _rule("BATCH", "Batch Process", "SCHEDULER_", "BATCH_", "THREAD_", "REC_", "INST_",
                  "DURATION_"),
        ),
    ),
]


def write_xml(tree: ET.ElementTree, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="UTF-8", xml_declaration=True)
    # Normalize declaration to match existing domain exports.
    text = path.read_text(encoding="utf-8")
    if text.startswith("<?xml version='1.0'"):
        text = text.replace("<?xml version='1.0' encoding='UTF-8'?>", '<?xml version="1.0" encoding="UTF-8"?>', 1)
    path.write_text(text, encoding="utf-8")


def generate_one(spec: SnapshotSpec) -> Path:
    ddl = ROOT / "sql/performance/snapshots" / spec.rel_dir / "01_create_snapshot_table.sql"
    columns = parse_create_table(ddl)
    if not columns:
        raise SystemExit(f"No columns parsed from {ddl}")
    tree = build_xml(spec, columns)
    filename = f"{spec.table}_End_User_Friendly.xml"
    import_path = ROOT / "domains/exports/manual_imports" / filename
    workspace_path = ROOT / "sql/performance/snapshots" / spec.rel_dir / filename
    write_xml(tree, import_path)
    write_xml(tree, workspace_path)
    return import_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", help="Generate one table (e.g. ACCT_CUSTOMER_RPT_CURR)")
    args = parser.parse_args()
    targets = SPECS
    if args.snapshot:
        targets = [s for s in SPECS if s.table == args.snapshot.upper()]
        if not targets:
            raise SystemExit(f"Unknown snapshot: {args.snapshot}")

    print("[INFO] Generating consolidation domain XML files")
    for spec in targets:
        path = generate_one(spec)
        print(f"  {spec.table} -> {path.relative_to(ROOT)}")
    print(f"[SUMMARY] {len(targets)} domain XML file(s) written (import + workspace copies)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
