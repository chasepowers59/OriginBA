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
