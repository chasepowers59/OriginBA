"""
Domain context from Domain Designs.xlsx for client-facing insights.
Loads output/domain_designs_metadata.json (generated from the workbook) to provide
table descriptions and justification hints so the AI can give domain-aware narratives.
"""

import json
from pathlib import Path

_DOMAIN_METADATA_PATH = Path(__file__).resolve().parent.parent / "output" / "domain_designs_metadata.json"
_cached_metadata: dict | None = None


def get_domain_metadata() -> dict:
    """Load domain_designs_metadata.json; return {} if missing or invalid."""
    global _cached_metadata
    if _cached_metadata is not None:
        return _cached_metadata
    if not _DOMAIN_METADATA_PATH.exists():
        _cached_metadata = {}
        return _cached_metadata
    try:
        with open(_DOMAIN_METADATA_PATH, encoding="utf-8") as f:
            _cached_metadata = json.load(f)
    except Exception:
        _cached_metadata = {}
    return _cached_metadata


def get_table_semantics(table_name: str) -> dict:
    """
    Return semantic metadata for a table: description, designer_notes, business_impact (when present).
    """
    meta = get_domain_metadata()
    desc = meta.get("table_descriptions") or {}
    entry = desc.get(table_name) or {}
    if isinstance(entry, dict):
        return {
            "description": entry.get("description"),
            "designer_notes": entry.get("designer_notes"),
            "business_impact": entry.get("business_impact"),
        }
    # Backwards compatibility: older JSON stored only description as string
    return {"description": entry if isinstance(entry, str) else None, "designer_notes": None, "business_impact": None}


def get_business_impact_for_table(table_name: str) -> str | None:
    """Return Business Impact text for a given table, if available."""
    semantics = get_table_semantics(table_name)
    impact = semantics.get("business_impact")
    if impact:
        return str(impact)
    # Fall back to designer notes when no explicit Business Impact column is present
    notes = semantics.get("designer_notes")
    return str(notes) if notes else None


def get_workstream_table_descriptions() -> str:
    """
    Return a short paragraph describing key tables used in the 7 workstreams,
    for inclusion in BI/NLQ system prompts so the AI can attribute insights correctly.
    """
    meta = get_domain_metadata()
    desc = meta.get("table_descriptions") or {}
    # Key tables per workstream (source of truth names); 9 workstreams
    workstream_tables = [
        ("Billing & Rates", ["CI_BILL", "CI_BSEG", "CI_FT", "CI_RS_L"]),
        ("Cashiering", ["CI_PAY_EVENT", "CI_PAY_TNDR", "CI_DEP_CTL"]),
        ("Meter/Device", ["D1_DVC", "D1_DVC_CFG", "D1_INSTALL_EVT", "CI_SP"]),
        ("Customer Operations", ["CI_ACCT", "CI_PER_NAME", "CI_ACCT_ALERT"]),
        ("New Services", ["CI_SA", "CI_SP_CHAR"]),
        ("Finance", ["CI_FT_GL", "CI_FT_PROC", "CI_FT"]),
        ("Common", ["CI_PREM", "CI_LOOKUP_VAL"]),
        ("Debt Management", ["CI_ACCT", "CI_FT", "CI_COLL_PROC"]),
        ("Field Operations", ["CI_SP", "D1_ACTIVITY"]),
        ("OCX & Field Tasks", ["F1_TSK", "F1_TSK_LOG", "CI_SP"]),  # F1 metadata + CI functional
    ]
    parts = []
    for ws_name, tables in workstream_tables:
        for t in tables:
            d = desc.get(t, {}) if isinstance(desc.get(t), dict) else {}
            short = d.get("description") if isinstance(d, dict) else desc.get(t)
            if isinstance(short, dict):
                short = short.get("description")
            if short:
                parts.append(f"{t}: {short}.")
    if not parts:
        return ""
    return "Domain (for client insights): " + " ".join(parts[:24])  # cap length


def get_semantic_layer_prompt_suffix() -> str:
    """
    Inject Justification and Designer Notes from Domain Designs.xlsx into the AI system prompt.
    Gives the AI business context (e.g. why arrears buckets matter, what D1_INSTALL_EVT means)
    so narratives are domain-aware. Use with get_workstream_table_descriptions() in generate_narrative.
    """
    meta = get_domain_metadata()
    desc = meta.get("table_descriptions") or {}
    hints = meta.get("workstream_insight_hints") or []

    # Designer notes for key workstream tables (business reason for the data)
    tables_with_notes = [
        "CI_BILL", "CI_BSEG", "CI_FT", "CI_RS_L",
        "CI_PAY_EVENT", "CI_PAY_TNDR", "CI_DEP_CTL",
        "D1_DVC", "D1_DVC_CFG", "D1_INSTALL_EVT", "CI_SP",
        "CI_ACCT", "CI_PER_NAME", "CI_ACCT_ALERT",
        "CI_SA", "CI_SP_CHAR", "CI_FT_GL", "CI_FT_PROC", "CI_FT",
        "CI_PREM", "CI_LOOKUP_VAL",
    ]
    parts = []
    for t in tables_with_notes:
        d = desc.get(t)
        if isinstance(d, dict) and d.get("designer_notes"):
            note = (d["designer_notes"] or "").strip()[:300]
            if note:
                parts.append(f"{t} (designer note): {note}.")
    # Workstream justification hints (why the table matters to the client)
    for h in hints[:12]:
        if isinstance(h, dict) and h.get("table") in tables_with_notes and h.get("hint"):
            parts.append(f"{h['table']} (client insight): {h['hint'][:250]}.")
    if not parts:
        return ""
    return " Business context from Domain Designs: " + " ".join(parts[:16])


def get_insight_hints_for_workstream(workstream: str) -> list[str]:
    """Return justification/hint strings for a workstream (e.g. 'billing', 'meter_ops') for the AI."""
    meta = get_domain_metadata()
    hints = meta.get("workstream_insight_hints") or []
    table_map = {
        "billing": ["CI_BILL", "CI_BSEG", "CI_FT", "CI_RS_L"],
        "cashiering": ["CI_PAY_EVENT", "CI_PAY_TNDR", "CI_DEP_CTL"],
        "meter_ops": ["D1_DVC", "D1_DVC_CFG", "D1_INSTALL_EVT", "D1_SP", "CI_SP"],
        "customer_ops": ["CI_ACCT", "CI_PER_NAME", "CI_ACCT_ALERT"],
        "new_services": ["CI_SA", "CI_SP_CHAR"],
        "finance": ["CI_FT_GL", "CI_FT_PROC", "CI_FT"],
        "common": ["CI_PREM", "CI_LOOKUP_VAL"],
        "debt_mgmt": ["CI_ACCT", "CI_FT", "CI_COLL_PROC"],
        "field_ops": ["CI_SP", "D1_ACTIVITY"],
        "field_tasks": ["F1_TSK", "F1_TSK_LOG", "CI_SP"],  # OCX & Field Tasks (F1 metadata + CI functional)
    }
    tables = table_map.get(workstream, [])
    out = []
    for h in hints:
        if isinstance(h, dict) and h.get("table") in tables and h.get("hint"):
            out.append(h["hint"])
    return out[:3]


def get_business_impact_for_workstream(workstream: str) -> str:
    """
    Aggregate Business Impact text for a workstream from table-level metadata.
    Useful for Business Snapshot persona to explain why data matters.
    """
    meta = get_domain_metadata()
    desc = meta.get("table_descriptions") or {}
    table_map = {
        "billing": ["CI_BILL", "CI_BSEG", "CI_FT", "CI_RS_L"],
        "cashiering": ["CI_PAY_EVENT", "CI_PAY_TNDR", "CI_DEP_CTL"],
        "meter_ops": ["D1_DVC", "D1_DVC_CFG", "D1_INSTALL_EVT", "CI_SP"],
        "customer_ops": ["CI_ACCT", "CI_PER_NAME", "CI_ACCT_ALERT"],
        "new_services": ["CI_SA", "CI_SP_CHAR"],
        "finance": ["CI_FT_GL", "CI_FT_PROC", "CI_FT"],
        "common": ["CI_PREM", "CI_LOOKUP_VAL"],
        "debt_mgmt": ["CI_ACCT", "CI_FT", "CI_COLL_PROC"],
        "field_ops": ["CI_SP", "D1_ACTIVITY"],
    }
    tables = table_map.get(workstream, [])
    parts: list[str] = []
    for t in tables:
        entry = desc.get(t)
        if isinstance(entry, dict):
            bi = entry.get("business_impact") or entry.get("designer_notes")
            if bi:
                parts.append(f"{t}: {str(bi).strip()[:300]}")
    return " ".join(parts[:6])
