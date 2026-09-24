"""Emit a JRS Ad Hoc domain schema (SL XMLSchema 1.3) from plain Python tables, joins, calculated
fields and sets -- the shape the Standard Offering builders share.

Rules the server taught (each cost a round trip, see the domain READMEs): explicit close tags only;
no empty <filterString>; the join tree's joinInfo alias is the ROOT TABLE id; a derived table is a
<jdbcQuery> whose SQL carries no bind syntax; every table takes the org's own datasource id.
"""
from __future__ import annotations

from xml.sax.saxutils import escape

Fields = list[tuple[str, str]]                 # (column, java type)
Tables = dict[str, tuple[str, Fields]]         # id -> (CISADM table, fields)
Derived = dict[str, tuple[str, Fields]]        # id -> (SQL, fields)
Joins = list[tuple[str, str, str, str]]        # (DomEL expr, left, right, type)
Calculated = list[tuple[str, str, str]]        # (field id, DomEL, java type)
Sets = list[tuple[str, str, list[tuple[str, str, str]]]]   # (set id, label, [(item id, label, TABLE.FIELD | calc id)])
Measures = list[tuple[str, str, str, str]]     # (item id, label, resource, default aggregation)


def schema(ds: str, root: str, tables: Tables, joins: Joins, calculated: Calculated, sets: Sets, measures: Measures,
           derived: Derived | None = None) -> str:
    derived = derived or {}
    root_table = tables[root][0]
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<schema xmlns="http://www.jaspersoft.com/2007/SL/XMLSchema" version="1.3">',
           '  <dataIslands>', '    <itemGroup id="JoinTree_1" label="JoinTree_1" resourceId="JoinTree_1"></itemGroup>', '  </dataIslands>',
           '  <dataSources>', f'    <jdbcDataSource id="{ds}">', '      <schemaMap>',
           '        <entry key="defaultSchema">', '          <string></string>', '        </entry>',
           '        <entry key="CISADM">', '          <string>CISADM</string>', '        </entry>',
           '      </schemaMap>', '    </jdbcDataSource>', '  </dataSources>', '  <itemGroups>']
    for sid, label, items in sets:
        out += [f'    <itemGroup id="{sid}" label="{escape(label)}" resourceId="JoinTree_1">', '      <items>']
        out += [f'        <item id="{i}" label="{escape(l)}" resourceId="JoinTree_1.{r}"></item>' for i, l, r in items]
        out += ['      </items>', '    </itemGroup>']
    out += ['    <itemGroup id="SET_METRICS" label="Measures" resourceId="JoinTree_1">', '      <items>']
    out += [f'        <item defaultAgg="{agg}" dimensionOrMeasure="Measure" id="{i}" label="{escape(l)}" resourceId="JoinTree_1.{r}"></item>' for i, l, r, agg in measures]
    out += ['      </items>', '    </itemGroup>', '  </itemGroups>', '  <resources>']
    for tid, (table, fields) in tables.items():
        out += [f'    <jdbcTable id="{tid}" datasourceId="{ds}" datasourceTableName="{table}" schemaAlias="CISADM">', '      <fieldList>']
        out += [f'        <field id="{f}" type="{t}"></field>' for f, t in fields]
        out += ['      </fieldList>', '    </jdbcTable>']
    for qid, (sql, fields) in derived.items():
        out += [f'    <jdbcQuery id="{qid}" datasourceId="{ds}">', '      <fieldList>']
        out += [f'        <field id="{f}" type="{t}"></field>' for f, t in fields]
        out += ['      </fieldList>', f'      <query>{escape(sql.strip())}</query>', '    </jdbcQuery>']
    out += [f'    <jdbcTable id="JoinTree_1" datasourceId="{ds}" datasourceTableName="{root_table}" schemaAlias="CISADM">', '      <fieldList>']
    for tid, (_, fields) in list(tables.items()) + [(q, (None, f)) for q, (_, f) in derived.items()]:
        out += [f'        <field id="{tid}.{f}" type="{t}"></field>' for f, t in fields]
    out += [f'        <field id="{fid}" dataSetExpression="{escape(expr)}" type="{t}"></field>' for fid, expr, t in calculated]
    out += ['      </fieldList>', f'      <joinInfo alias="{root}" referenceId="{root}"></joinInfo>', '      <joinList>']
    out += [f'        <join expr="{escape(e)}" left="{l}" right="{r}" type="{ty}" weight="1"></join>' for e, l, r, ty in joins]
    out += ['      </joinList>', '      <joinOptions></joinOptions>', '      <tableRefList>']
    out += [f'        <tableRef alwaysIncludeTable="false" tableAlias="{tid}" tableId="{tid}"></tableRef>' for tid in list(tables) + list(derived)]
    out += ['      </tableRefList>', '    </jdbcTable>', '  </resources>', '</schema>', '']
    return "\n".join(out)


# ------------------------------------------------------------------ the additive-only guard
# Chase, 2026-09-24: a change to a deployed domain must ADD; every existing id, label, join,
# resource, calculation and measure stays byte for byte, or the views and reports bound to the
# domain break. Every patch goes through this before it goes near a server.
import xml.etree.ElementTree as _ET  # noqa: E402

_NS = "{http://www.jaspersoft.com/2007/SL/XMLSchema}"


def _facts(xml: str) -> set[tuple]:
    r = _ET.fromstring(xml)
    facts: set[tuple] = set()
    for t in r.iter(_NS + "jdbcTable"):
        for f in t.iter(_NS + "field"):
            facts.add(("field", t.get("id"), f.get("id"), f.get("type"), f.get("dataSetExpression")))
        facts.add(("table", t.get("id"), t.get("datasourceId"), t.get("datasourceTableName"), t.get("schemaAlias")))
        for j in t.iter(_NS + "joinInfo"):
            facts.add(("joinInfo", t.get("id"), j.get("alias"), j.get("referenceId")))
        for j in t.iter(_NS + "join"):
            facts.add(("join", t.get("id"), j.get("expr"), j.get("left"), j.get("right"), j.get("type"), j.get("weight")))
        for f in t.iter(_NS + "filterString"):
            facts.add(("filter", t.get("id"), f.text))
    for q in r.iter(_NS + "jdbcQuery"):
        facts.add(("query", q.get("id"), q.get("datasourceId"), (q.find(_NS + "query").text or "").strip()))
        for f in q.iter(_NS + "field"):
            facts.add(("field", q.get("id"), f.get("id"), f.get("type"), f.get("dataSetExpression")))
    for g in r.iter(_NS + "itemGroup"):
        facts.add(("group", g.get("id"), g.get("label"), g.get("resourceId")))
        for i in g.iter(_NS + "item"):
            facts.add(("item", g.get("id"), i.get("id"), i.get("label"), i.get("resourceId"), i.get("defaultAgg"), i.get("dimensionOrMeasure")))
    for d in r.iter(_NS + "jdbcDataSource"):
        facts.add(("datasource", d.get("id")))
    return facts


def additions_only(before: str, after: str) -> list[str]:
    """Everything the old schema said is still said, unchanged, by the new one; the violations
    are what was removed or altered (an empty list is the proof)."""
    lost = _facts(before) - _facts(after)
    return sorted(" ".join(str(x) for x in f if x is not None) for f in lost)


# ------------------------------------------------------------------ additive patching of an exported schema
def add_to_schema(schema: str, tables: Tables, joins: list[tuple[str, str, str]], calculated: Calculated, sets: Sets, guard_id: str) -> str:
    """Return the exported schema with tables (before the join tree), their join-tree fields,
    calculated fields, outer joins, table refs and item groups ADDED; nothing existing is touched
    (prove it with additions_only). guard_id: a new table id whose presence means 'already patched'."""
    import re as _re
    from xml.sax.saxutils import escape as _esc
    if f'id="{guard_id}"' in schema:
        raise ValueError(f"the schema already carries {guard_id}: not patching twice")
    ds = _re.search(r'<jdbcDataSource id="([^"]+)"', schema).group(1)
    new_tables = "".join(f'    <jdbcTable id="{tid}" datasourceId="{ds}" datasourceTableName="{tb}" schemaAlias="CISADM">\n      <fieldList>\n'
                         + "".join(f'        <field id="{f}" type="{t}"></field>\n' for f, t in fields) + "      </fieldList>\n    </jdbcTable>\n"
                         for tid, (tb, fields) in tables.items())
    start = schema.index('<jdbcTable id="JoinTree_1"'); line_start = schema.rfind("\n", 0, start) + 1
    schema = schema[:line_start] + new_tables + schema[line_start:]
    jt0 = schema.index('<jdbcTable id="JoinTree_1"'); jt1 = schema.index("</jdbcTable>", jt0)
    tree = schema[jt0:jt1]
    fields = "".join(f'        <field id="{tid}.{f}" type="{t}"></field>\n' for tid, (_, fs) in tables.items() for f, t in fs)
    fields += "".join(f'        <field id="{fid}" dataSetExpression="{_esc(expr)}" type="{t}"></field>\n' for fid, expr, t in calculated)
    join_xml = "".join(f'        <join expr="{_esc(e)}" left="{l}" right="{r}" type="leftOuter" weight="1"></join>\n' for e, l, r in joins)
    refs = "".join(f'        <tableRef alwaysIncludeTable="false" tableAlias="{tid}" tableId="{tid}"></tableRef>\n' for tid in tables)
    tree = (tree.replace("      </fieldList>", fields + "      </fieldList>", 1).replace("      </joinList>", join_xml + "      </joinList>", 1)
                .replace("      </tableRefList>", refs + "      </tableRefList>", 1))
    schema = schema[:jt0] + tree + schema[jt1:]
    groups = "".join(f'    <itemGroup id="{sid}" label="{_esc(label)}" resourceId="JoinTree_1">\n      <items>\n'
                     + "".join(f'        <item id="{i}" label="{_esc(l)}" resourceId="JoinTree_1.{r}"></item>\n' for i, l, r in items) + "      </items>\n    </itemGroup>\n"
                     for sid, label, items in sets)
    return schema.replace("  </itemGroups>", groups + "  </itemGroups>", 1)
