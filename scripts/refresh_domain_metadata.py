"""
Refresh output/domain_designs_metadata.json from Domain Designs.xlsx.
Run from repo root: python scripts/refresh_domain_metadata.py
Use this after updating the workbook so BI/NLQ narratives and Business Snapshots
get the latest table descriptions, designer notes, and Business Impact text.
"""

import json
import sys
from pathlib import Path

# Project root
ROOT = Path(__file__).resolve().parent.parent


def _norm_text(val) -> str:
    if val is None:
        return ""
    text = str(val).replace("\xa0", " ").strip()
    text = " ".join(text.split())
    return "" if text.lower() == "nan" else text


def _as_table_name(raw: str) -> str | None:
    token = (raw or "").strip().split(" ")[0]
    if token.startswith("CI_") or token.startswith("D1_") or token.startswith("F1_") or token.startswith("C1_"):
        return token
    return None


def _extract_table_name_and_justification(df, default_sheet_name: str) -> tuple[str | None, str | None]:
    table_name = None
    justification = None
    for i in range(min(20, len(df))):
        row_vals = [_norm_text(x) for x in df.iloc[i].tolist()]
        joined = " | ".join([x for x in row_vals if x])
        if not joined:
            continue
        if "Table Name" in joined:
            # Handle forms like "Table Name: CI_BILL" and split-cell forms
            if ":" in joined:
                after = joined.split(":", 1)[1].strip()
                t = _as_table_name(after)
                if t:
                    table_name = t
            if table_name is None:
                for token in row_vals:
                    t = _as_table_name(token)
                    if t:
                        table_name = t
                        break
        if "Justification" in joined and not justification:
            # Most sheets place text in next column; fallback to whole joined row
            if df.shape[1] > 1:
                j = _norm_text(df.iloc[i, 1])
                if len(j) > 20:
                    justification = j[:500]
            if not justification and len(joined) > 20:
                justification = joined[:500]
    if table_name is None:
        table_name = _as_table_name(default_sheet_name.split(" ")[0])
    return table_name, justification


def _extract_fields(df, table_name: str | None) -> list[dict]:
    fields: list[dict] = []
    if table_name is None:
        return fields
    header_idx = None
    table_col = None
    field_col = None
    desc_col = None
    for i in range(min(80, len(df))):
        row_vals = [_norm_text(x) for x in df.iloc[i].tolist()]
        if "Field Name" not in row_vals:
            continue
        for idx, v in enumerate(row_vals):
            if v in ("Table Name", "Table"):
                table_col = idx
            elif v == "Field Name":
                field_col = idx
            elif "Description" in v and desc_col is None:
                desc_col = idx
        if field_col is not None:
            header_idx = i
            break
    if header_idx is None:
        return fields
    seen = set()
    reserved = {
        "SELECT", "FROM", "WHERE", "JOIN", "INNER", "LEFT", "RIGHT", "ON",
        "ORDER", "GROUP", "BY", "COUNT", "FILTER", "COMBINATION",
    }
    for _, row in df.iloc[header_idx + 1:].iterrows():
        row_vals = [_norm_text(x) for x in row.tolist()]
        table_val = row_vals[table_col] if table_col is not None and table_col < len(row_vals) else table_name
        field_val = row_vals[field_col] if field_col is not None and field_col < len(row_vals) else ""
        desc_val = row_vals[desc_col] if desc_col is not None and desc_col < len(row_vals) else None
        desc_missing = (not desc_val) or (str(desc_val).strip().lower() == "nan")
        if not field_val:
            continue
        # Stop at first blank block after field section.
        if field_val.lower().startswith("select ") or field_val.lower().startswith("where "):
            break
        table_token = _as_table_name(table_val) or table_name
        if not table_token:
            continue
        field_token = field_val.split(" ")[0].strip().upper()
        if field_token == "NAN":
            continue
        if not field_token or not field_token.replace("_", "").isalnum():
            continue
        if desc_missing:
            continue
        if field_token in reserved:
            continue
        key = (table_token, field_token)
        if key in seen:
            continue
        seen.add(key)
        fields.append(
            {
                "table": table_token,
                "name": field_token,
                "description": None if desc_missing else desc_val,
            }
        )
    return fields


def main() -> None:
    try:
        import pandas as pd
    except ImportError:
        print("pandas and openpyxl required: pip install pandas openpyxl", file=sys.stderr)
        sys.exit(1)

    xlsx = ROOT / "Domain Designs.xlsx"
    if not xlsx.exists():
        print(f"Not found: {xlsx}", file=sys.stderr)
        sys.exit(1)

    x = pd.ExcelFile(xlsx)
    out = {"tables": {}, "workstream_insight_hints": [], "table_descriptions": {}}

    # Summary sheet: Table Name -> Description, Designer Notes, and Business Impact (if present)
    if "Summary" in x.sheet_names:
        df = pd.read_excel(x, sheet_name="Summary", header=0)
        cols = list(df.columns)
        tbl_col = desc_col = notes_col = impact_col = None
        for i, c in enumerate(cols):
            label = str(c) if c is not None else ""
            if "Table" in label and "Name" in label:
                tbl_col = i
            if "Description" in label:
                desc_col = i
            if "Notes" in label and "Designer" in label:
                notes_col = i
            if "Business" in label and "Impact" in label:
                impact_col = i
        if tbl_col is None:
            tbl_col = 0
        if desc_col is None and len(cols) > 1:
            desc_col = 1
        for _, row in df.iterrows():
            t = row.iloc[tbl_col] if tbl_col is not None else None
            if pd.isna(t):
                continue
            t = str(t).strip()
            if not (t.startswith("CI_") or t.startswith("D1_")):
                continue
            d = row.iloc[desc_col] if desc_col is not None else None
            n = row.iloc[notes_col] if notes_col is not None and notes_col < len(row) else None
            b = row.iloc[impact_col] if impact_col is not None and impact_col < len(row) else None
            d = None if pd.isna(d) else str(d).strip()[:400]
            n = None if pd.isna(n) else str(n).strip()[:300]
            b = None if pd.isna(b) else str(b).strip()[:400]
            out["table_descriptions"][t] = {
                "description": d,
                "designer_notes": n,
                "business_impact": b,
            }

    # Per-sheet justifications and fields (for workstream_insight_hints and reporting dictionary)
    for name in x.sheet_names:
        if name in ("Constants", "Tabulation", "Pivot", "Summary", "Manual Labels", "SP upgrades", "BODA", "Malformed XML DA"):
            continue
        if "EXCP" in name or "Archive" in name:
            continue
        df = pd.read_excel(x, sheet_name=name, header=None)
        if df.empty or df.shape[0] < 6:
            continue
        table_name, justification = _extract_table_name_and_justification(df, name)
        key = table_name or _as_table_name(name.split(" ")[0])
        if not key:
            continue
        if key not in out["tables"]:
            out["tables"][key] = {"justification": justification, "designer": None, "fields": []}
        elif justification and not out["tables"][key].get("justification"):
            out["tables"][key]["justification"] = justification

        for f in _extract_fields(df, key):
            target = f["table"]
            if target not in out["tables"]:
                out["tables"][target] = {"justification": None, "designer": None, "fields": []}
            existing = {(x.get("table"), x.get("name")) for x in out["tables"][target].get("fields", [])}
            fk = (f["table"], f["name"])
            if fk not in existing:
                out["tables"][target]["fields"].append(f)

        if justification and key not in [h.get("table") for h in out["workstream_insight_hints"]]:
            out["workstream_insight_hints"].append({"table": key, "hint": justification[:300]})

    out_path = ROOT / "output" / "domain_designs_metadata.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(
        f"Wrote {out_path} "
        f"(table_descriptions: {len(out['table_descriptions'])}, tables: {len(out['tables'])})"
    )


if __name__ == "__main__":
    main()
