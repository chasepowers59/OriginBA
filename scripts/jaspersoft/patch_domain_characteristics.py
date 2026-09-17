#!/usr/bin/env python3
"""Turn a CISADM domain's characteristic tables into derived tables that answer Ad Hoc honestly.

Applies to a Standard Offering schema.data (Service Agreement 360 today) that joins
CI_SA_CHAR / CI_PREM_CHAR and their CI_CHAR_TYPE_L / CI_CHAR_VAL_L labels as raw tables.
Three things were wrong with that shape, all found reviewing the 2026-09-17 change:

1. A label table is a table of EVERYTHING. Dragging "Characteristic Type Code" from
   CI_CHAR_TYPE_L offers every characteristic type in the system (account, person, SA,
   premise...), and selecting label fields alone queries the label table alone. With the
   type and value descriptions folded INTO the characteristic row, the values a user sees
   are exactly the characteristics that exist on premises (or SAs), nothing else.
2. Characteristics are effective-dated (PK entity + type + EFFDT). Every version was a
   row and nothing said which one is current. IS_CURRENT_SW marks the latest version
   whose EFFDT is not in the future; no row is removed, so history stays available.
3. "Value Description" came from CI_CHAR_VAL_L, which only describes predefined (DFV)
   types; ad hoc (ADV) and foreign-key (FKV) characteristics showed nothing. CHAR_VALUE
   resolves by CI_CHAR_TYPE.CHAR_TYPE_FLG: DFV -> the label (or the code), ADV -> the ad
   hoc text, FKV -> the foreign key.

The derived tables keep the ORIGINAL table ids (CI_SA_CHAR, CI_PREM_CHAR), so every join,
join-tree field and item resourceId that named them still resolves and saved Ad Hoc views
keep working; the label-table items are repointed to the folded columns under their
existing item ids. Also fixed while here: SA_ID_DIST counted CI_SA_CONTERM.SA_ID (SAs
with contract terms), now CI_SA.SA_ID.

The datasource id is read from the schema itself and must be unique: a domain cannot
join across datasource ids, and the id must be the one the domain wrapper references.

    python3 scripts/jaspersoft/patch_domain_characteristics.py IN.xml OUT.xml
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

# entity column, the two label-table aliases the raw shape used, the item-group id
TARGETS = {
    "CI_SA_CHAR":   {"key": "SA_ID",   "type_l": "CI_CHAR_TYPE_L",   "val_l": "CI_CHAR_VAL_L"},
    "CI_PREM_CHAR": {"key": "PREM_ID", "type_l": "CI_CHAR_TYPE_L_2", "val_l": "CI_CHAR_VAL_L_2"},
}
RAW_COLS = ["CHAR_TYPE_CD", "EFFDT", "CHAR_VAL", "ADHOC_CHAR_VAL", "SRCH_CHAR_VAL",
            "CHAR_VAL_FK1", "CHAR_VAL_FK2", "CHAR_VAL_FK3", "CHAR_VAL_FK4", "CHAR_VAL_FK5", "VERSION"]
NEW_COLS = [  # column, java type, item label
    ("CHAR_TYPE_DESCR", "java.lang.String", "Characteristic Type Description"),
    ("CHAR_TYPE_FLG",   "java.lang.String", "Characteristic Type Kind"),
    ("CHAR_VAL_DESCR",  "java.lang.String", "Characteristic Value Description"),
    ("CHAR_VALUE",      "java.lang.String", "Characteristic Value"),
    ("IS_CURRENT_SW",   "java.lang.String", "Is Current Characteristic"),
]
TYPES = {"EFFDT": "java.sql.Timestamp", "VERSION": "java.math.BigDecimal"}


def derived_sql(table: str, key: str) -> str:
    """Parser-safe (starts with SELECT, one wrapper, no CTE, no bind, no semicolon)."""
    raw = ", ".join(f"c.{col}" for col in RAW_COLS if col not in ("CHAR_TYPE_CD",))
    return (
        f"SELECT {key}, CHAR_TYPE_CD, CHAR_TYPE_DESCR, CHAR_TYPE_FLG, EFFDT, CHAR_VAL, CHAR_VAL_DESCR, "
        f"CHAR_VALUE, ADHOC_CHAR_VAL, SRCH_CHAR_VAL, CHAR_VAL_FK1, CHAR_VAL_FK2, CHAR_VAL_FK3, "
        f"CHAR_VAL_FK4, CHAR_VAL_FK5, VERSION, IS_CURRENT_SW FROM ("
        f"SELECT c.{key}, c.CHAR_TYPE_CD, ctl.DESCR AS CHAR_TYPE_DESCR, TRIM(ct.CHAR_TYPE_FLG) AS CHAR_TYPE_FLG, "
        f"{raw}, cvl.DESCR AS CHAR_VAL_DESCR, "
        f"CASE TRIM(ct.CHAR_TYPE_FLG) WHEN 'ADV' THEN c.ADHOC_CHAR_VAL WHEN 'FKV' THEN c.CHAR_VAL_FK1 "
        f"ELSE COALESCE(cvl.DESCR, c.CHAR_VAL) END AS CHAR_VALUE, "
        f"CASE WHEN c.EFFDT = MAX(CASE WHEN c.EFFDT <= CURRENT_DATE THEN c.EFFDT END) "
        f"OVER (PARTITION BY c.{key}, c.CHAR_TYPE_CD) THEN 'Y' ELSE 'N' END AS IS_CURRENT_SW "
        f"FROM CISADM.{table} c "
        f"LEFT JOIN CISADM.CI_CHAR_TYPE ct ON ct.CHAR_TYPE_CD = c.CHAR_TYPE_CD "
        f"LEFT JOIN CISADM.CI_CHAR_TYPE_L ctl ON ctl.CHAR_TYPE_CD = c.CHAR_TYPE_CD AND ctl.LANGUAGE_CD = 'ENG' "
        f"LEFT JOIN CISADM.CI_CHAR_VAL_L cvl ON cvl.CHAR_TYPE_CD = c.CHAR_TYPE_CD "
        f"AND cvl.CHAR_VAL = c.CHAR_VAL AND cvl.LANGUAGE_CD = 'ENG') X"
    )


def _jdbc_query(table: str, key: str, ds: str) -> str:
    fields = [(key, "java.lang.String")] + [(c, TYPES.get(c, "java.lang.String")) for c in RAW_COLS]
    fields += [(c, t) for c, t, _ in NEW_COLS]
    body = "\n".join(f'        <field id="{c}" type="{t}"></field>' for c, t in fields)
    return (f'    <jdbcQuery id="{table}" datasourceId="{ds}">\n      <fieldList>\n{body}\n      </fieldList>\n'
            f'      <query>{escape(derived_sql(table, key))}</query>\n    </jdbcQuery>\n')


def _drop_table(schema: str, table_id: str) -> str:
    out, n = re.subn(rf'\s*<jdbcTable id="{table_id}"[^>]*>.*?</jdbcTable>', "", schema, count=1, flags=re.S)
    if not n:
        raise SystemExit(f"jdbcTable {table_id} not found")
    return out


def patch(schema: str) -> str:
    ds_ids = re.findall(r'<jdbcDataSource id="([^"]+)"', schema)
    if len(set(ds_ids)) != 1:
        raise SystemExit(f"expected exactly one datasource id, found {ds_ids}")
    ds = ds_ids[0]
    if "<jdbcQuery" in schema:
        raise SystemExit("schema already carries derived tables; refusing to patch twice")

    for table, t in TARGETS.items():
        key, type_l, val_l = t["key"], t["type_l"], t["val_l"]
        # the raw table and its two labels become one derived table under the same id
        for tid in (table, type_l, val_l):
            schema = _drop_table(schema, tid)
        schema = schema.replace('    <jdbcTable id="JoinTree_1"', _jdbc_query(table, key, ds) + '    <jdbcTable id="JoinTree_1"', 1)
        # label joins, refs and join-tree fields go; the characteristic join itself stays
        for lab in (type_l, val_l):
            schema, n = re.subn(rf'\s*<join [^>]*right="{lab}"[^>]*></join>', "", schema)
            assert n == 1, f"join to {lab}: {n}"
            schema, n = re.subn(rf'\s*<tableRef [^>]*tableId="{lab}"[^>]*></tableRef>', "", schema)
            assert n == 1, f"tableRef {lab}: {n}"
            schema = re.sub(rf'\s*<field id="{lab}\.[^"]*"[^>]*></field>', "", schema)
        # new join-tree fields after the table's VERSION field
        anchor = f'<field id="{table}.VERSION" type="java.math.BigDecimal"></field>'
        assert anchor in schema, anchor
        schema = schema.replace(anchor, anchor + "".join(
            f'\n        <field id="{table}.{c}" type="{jt}"></field>' for c, jt, _ in NEW_COLS), 1)
        # items: repoint the two label items, add the resolved value, kind and current flag
        schema = schema.replace(f'resourceId="JoinTree_1.{type_l}.DESCR"', f'resourceId="JoinTree_1.{table}.CHAR_TYPE_DESCR"')
        schema = schema.replace(f'resourceId="JoinTree_1.{val_l}.DESCR"', f'resourceId="JoinTree_1.{table}.CHAR_VAL_DESCR"')
        item_anchor = re.search(rf'<item id="{table}_VERSION"[^>]*></item>', schema)
        assert item_anchor, f"{table}_VERSION item"
        extra = "".join(f'\n        <item id="{table}_{c}" label="{lbl}" resourceId="JoinTree_1.{table}.{c}"></item>'
                        for c, _, lbl in NEW_COLS if c not in ("CHAR_TYPE_DESCR", "CHAR_VAL_DESCR"))
        schema = schema[:item_anchor.end()] + extra + schema[item_anchor.end():]

    # a distinct-SA count that counts SAs, not SAs with contract terms
    schema = schema.replace("CountDistinct(CI_SA_CONTERM.SA_ID, 'Current')", "CountDistinct(CI_SA.SA_ID, 'Current')")
    # the premise-characteristic group's key is the SA's characteristic premise
    schema = schema.replace('<item id="CI_PREM_CHAR_PREM_ID" label="Premise ID"', '<item id="CI_PREM_CHAR_PREM_ID" label="Characteristic Premise ID"')
    return schema


def main() -> int:
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    dst.write_text(patch(src.read_text(encoding="utf-8")), encoding="utf-8")
    print(f"wrote {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
