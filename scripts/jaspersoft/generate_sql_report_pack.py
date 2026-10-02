#!/usr/bin/env python3
"""Generate the SmartCity finance report pack: SQL JRXML main reports with a subreport each,
runnable at ANY client because the SQL names only base-product tables, lifecycle constants
and label tables -- never a client-configured code.

    python3 scripts/jaspersoft/generate_sql_report_pack.py          # writes reports/ + server/input_controls/

Why generated: eight JRXML files share one style block, one page geometry, one parameter set
and one band layout; hand-editing them drifts. Each report is a SPEC below (query, columns,
subreport); the emitter owns the JRXML 7 model: the SmartCity server is JasperReports
Server 10.0 (JasperReports 7), which cannot load 6.x JRXML at all. Proofs: tests/test_sql_report_pack.py (structure, validator, the
SQL runs on the Ellensburg slice) and the JasperReports 6.20.6 compile in that test when a
JDK is present.

SQL conventions (portable Oracle <-> local Postgres slice, same text):
  TRIM() on every CHAR flag; COALESCE not NVL; TO_CHAR(dt,'YYYY-MM') for months;
  a window is  dt >= $P{FROM_DT} AND dt < $P{TO_DT} + INTERVAL '1' DAY  (inclusive TO date);
  labels LEFT JOIN on the full key with LANGUAGE_CD = 'ENG'.
Money semantics (docs/BILLING_AMOUNT_SEMANTICS.md): billed = calc headers of FROZEN segments
on COMPLETED bills; payments = tenders with no cancel reason; adjustments FROZEN ('50');
GL = CI_FT_GL lines of frozen FTs by accounting date.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REPORTS = REPO / "reports"
SUBS = REPORTS / "subreports"
CONTROLS = REPO / "server" / "input_controls"

PAGE_W, PAGE_H, MARGIN = 842, 595, 20
COL_W = PAGE_W - 2 * MARGIN          # 802
ROW_H, HDR_H = 16, 18
MONEY = "#,##0.00;(#,##0.00)"
INT = "#,##0"

STYLES = """    <style name="Base" default="true" fontName="SansSerif" fontSize="9"/>
    <style name="TitleSapphire" style="Base" fontSize="18" bold="true" forecolor="#006FAC"/>
    <style name="H3" style="Base" fontSize="9" forecolor="#0F4761"/>
    <style name="HeaderSapphire" style="Base" fontSize="9" bold="true" forecolor="#FFFFFF" backcolor="#006FAC" mode="Opaque"/>
    <style name="RowBand" style="Base" fontSize="9" bold="true" forecolor="#000000" backcolor="#E7F2F8" mode="Opaque"/>
    <style name="SubHeader" style="Base" fontSize="8" forecolor="#5B6470"/>
    <style name="SubText" style="Base" fontSize="8" forecolor="#000000"/>
    <style name="SubTotal" style="Base" fontSize="8" bold="true" forecolor="#0F4761"/>
    <style name="TotalText" style="Base" fontSize="9" bold="true" forecolor="#000000" backcolor="#E7F2F8" mode="Opaque"/>
    <style name="FooterConfidential" style="Base" fontSize="7" forecolor="#5B6470"/>
"""
FOOTER = '"@2026, Origin Utility, Inc / Proprietary & Confidential"'


@dataclass
class Col:
    name: str | None          # None = a blank cell that holds the main report's column position
    label: str
    cls: str = "java.lang.String"
    width: int = 80
    align: str = "Center"     # text and dates centre under their header; amounts pass "Right" so decimals line up
    pattern: str | None = None
    total: bool = False       # Sum variable + summary cell


@dataclass
class Sub:
    name: str
    key_param: str            # parameter the main passes (the row's key)
    key_field: str            # main-report field holding the key
    sql: str
    columns: list[Col]
    intro: str                # (unused since the layout rework: the main row already names the key)
    extra_keys: dict = field(default_factory=dict)   # more param -> main field pairs (a compound key)
    header: bool = False      # print the subreport's own column header (only when its columns are not the main grid)

    def keys(self) -> dict:
        return {self.key_param: self.key_field, **self.extra_keys}


@dataclass
class Filter:
    """An OPTIONAL input control: left empty it selects everything (the predicate is
    `$P{X} IS NULL OR ...`), filled it narrows both the main query and the subreport. The
    main and the subreport may need different predicates because their aliases differ."""
    param: str
    label: str
    main_pred: str
    sub_pred: str
    cls: str = "java.lang.String"
    control: str = "singleValueText"
    lov_sql: str | None = None   # a pick-list: SELECT <code> AS CODE, <label> AS DESCR ... on the same datasource
    multi: bool = False          # several values at once: java.util.Collection, $X{IN, col, PARAM} (empty = all)
    required: bool = False       # the report cannot run without it (a mandatory control, never "blank = all")


@dataclass
class Spec:
    name: str
    label: str
    description: str
    sql: str
    columns: list[Col]
    sub: Sub
    order_note: str = ""
    params: dict = field(default_factory=dict)   # extra parameters name -> (class, default expr)
    filters: list[Filter] = field(default_factory=list)
    window_label: str = "Date"                    # the column the FROM/TO window filters on, as the user knows it
    constants: dict = field(default_factory=dict) # extra literals the SQL may compare against: base-product lifecycle
                                                  # codes or lookup FIELD_NAMEs only, each with the reason it is safe
    as_of: bool = False                           # a POSITION report: one AS_OF_DT instead of the FROM/TO window
    year: bool = False                            # the window defaults to the last calendar year, not the last month

    def date_params(self) -> tuple[str, ...]:
        return ("AS_OF_DT",) if self.as_of else ("FROM_DT", "TO_DT")

    def all_params(self) -> dict:
        return {**self.params, **{f.param: ("java.util.Collection" if f.multi else f.cls, "null") for f in self.filters}}

    def main_sql(self) -> str:
        return _with_filters(self.sql, [f.main_pred for f in self.filters])

    def sub_sql(self) -> str:
        return _with_filters(self.sub.sql, [f.sub_pred for f in self.filters])


def _with_filters(sql: str, preds: list[str]) -> str:
    """Append the optional predicates to the query's (first) WHERE clause -- before GROUP BY /
    ORDER BY. Queries here have one WHERE at their driving level; the TOP-N subquery is the
    exception and is handled by placing the marker comment where the filters belong.

    The block that receives them gets NO_EXPAND: with binds Oracle OR-expands each
    "$P{X} IS NULL OR ..." into a UNION-ALL branch that re-scans the driving table (Billing by
    Cycle at College Station: cost 140K vs 35K, over 600 s cold; measured 2026-10-02). Postgres
    reads the hint as a comment."""
    preds = [p for p in preds if p]   # a filter applied inside the query's own logic adds no predicate
    if not preds:
        return sql
    extra = "".join(f"\n  AND {p}" for p in preds)
    if "/*FILTERS*/" in sql:
        inserted = extra.lstrip("\n")
        sql = sql.replace("/*FILTERS*/", inserted)   # a template may carry the marker in two blocks
        ats = [i for i in range(len(sql)) if sql.startswith(inserted, i)]
    else:
        at = next((i for i in (sql.find(kw) for kw in ("\nGROUP BY", "\nORDER BY")) if i >= 0), len(sql))
        sql = sql[:at] + extra + sql[at:]
        ats = [at]
    for at in reversed(ats):
        sql = _hint_block(sql, at)
    return sql


def _hint_block(sql: str, at: int) -> str:
    """NO_EXPAND on the SELECT that owns position `at` (the nearest SELECT before it), merged
    into a hint comment the template already put there (Oracle reads only the first)."""
    depth, i = 0, at   # walk back past any subquery (a scalar lookup, an EXISTS) to the block's own SELECT
    while i > 0:
        i -= 1
        if sql[i] == ")":
            depth += 1
        elif sql[i] == "(":
            depth -= 1
        elif depth <= 0 and sql.startswith("SELECT", i) and (i == 0 or not sql[i - 1].isalnum()):
            break
    rest = sql[i + len("SELECT"):]
    if rest.startswith(" /*+ "):
        return sql[:i] + "SELECT /*+ NO_EXPAND " + rest[len(" /*+ "):]
    return sql[:i] + "SELECT /*+ NO_EXPAND */" + rest


# ------------------------------------------------------------------ JRXML 7 emitter
# The SmartCity server is JasperReports Server 10.0 (measured: /rest_v2/serverInfo, 2026-09-17),
# which runs JasperReports 7 and cannot load the 6.x JRXML model at all. JRXML 7 is the flat
# vocabulary the letterprint templates use: <element kind="textField" ...><expression>, styles
# with default/bold, <query>, parameters with forPrompting, no xmlns on the root.

def _select_first(sql: str) -> str:
    """JRS 10 refuses a report query that starts with WITH (a generic "An error has occurred",
    before the query runs; measured on Origin_DEV 2026-10-01). Oracle takes the same CTEs inside
    an inline view, and keeps the inner ORDER BY there as in its documented top-N idiom."""
    sql = sql.strip()
    return f"SELECT * FROM (\n{sql}\n) q" if sql.upper().startswith("WITH") else sql


def _xml_esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _params(extra: dict[str, tuple[str, str]], as_of: bool = False, year: bool = False) -> str:
    base = {"AS_OF_DT": ("java.sql.Date", 'java.sql.Date.valueOf(java.time.LocalDate.now().toString())')} if as_of else {
        "FROM_DT": ("java.sql.Date", 'java.sql.Date.valueOf(java.time.LocalDate.now().minusYears(1).withDayOfYear(1).toString())'),
        "TO_DT": ("java.sql.Date", 'java.sql.Date.valueOf(java.time.LocalDate.now().withDayOfYear(1).minusDays(1).toString())'),
    } if year else {
        "FROM_DT": ("java.sql.Date", 'java.sql.Date.valueOf(java.time.LocalDate.now().withDayOfMonth(1).minusMonths(1).toString())'),
        "TO_DT": ("java.sql.Date", 'java.sql.Date.valueOf(java.time.LocalDate.now().withDayOfMonth(1).minusDays(1).toString())'),
    }
    base.update(extra)
    return "\n".join(
        f'    <parameter name="{n}" class="{cls}">\n        <defaultValueExpression><![CDATA[{default}]]></defaultValueExpression>\n    </parameter>'
        for n, (cls, default) in base.items())


def _fields(cols: list[Col]) -> str:
    return "\n".join(f'    <field name="{c.name}" class="{c.cls}"/>' for c in cols if c.name)


def _variables(cols: list[Col]) -> str:
    return "\n".join(
        f'    <variable name="SUM_{c.name}" class="{c.cls}" calculation="Sum">\n'
        f'        <expression><![CDATA[$F{{{c.name}}}]]></expression>\n    </variable>'
        for c in cols if c.total and c.name)


def _rule(x: int, y: int, w: int, seed: str, width: str = "0.5", color: str = "#B9C6D2") -> str:
    return (f'            <element kind="line" x="{x}" y="{y}" width="{w}" height="1">'
            f'<pen lineWidth="{width}" lineColor="{color}"/></element>')


def _text(x: int, y: int, w: int, h: int, expr: str, style: str, align: str, seed: str,
          pattern: str | None = None, evaluation: str | None = None) -> str:
    pat = f' pattern="{pattern}"' if pattern else ""
    ev = f' evaluationTime="{evaluation}"' if evaluation else ""
    return (f'            <element kind="textField" x="{x}" y="{y}" width="{w}" height="{h}" style="{style}" '
            f'hTextAlign="{align}" vTextAlign="Middle" blankWhenNull="true" textAdjust="StretchHeight"{pat}{ev}>'
            f'<expression><![CDATA[{expr}]]></expression></element>')


def _static(x: int, y: int, w: int, h: int, text: str, style: str, align: str, seed: str) -> str:
    return (f'            <element kind="staticText" x="{x}" y="{y}" width="{w}" height="{h}" style="{style}" '
            f'hTextAlign="{align}" vTextAlign="Middle"><text><![CDATA[{_xml_esc(text)}]]></text></element>')


def _header_row(cols: list[Col], style: str, seed: str, h: int = HDR_H, y: int = 0) -> str:
    x, out = 0, []
    for c in cols:
        if style == "HeaderSapphire" or c.name:
            # a header label sits exactly where its column's cells sit: same alignment (Chase, 2026-09-23)
            out.append(_static(x, y, c.width, h, c.label if c.name else "", style, c.align, f"{seed}/h/{c.name}"))
        x += c.width
    return "\n".join(out)


def _detail_row(cols: list[Col], style: str, seed: str, h: int = ROW_H, y: int = 0) -> str:
    x, out = 0, []
    for c in cols:
        if c.name:
            out.append(_text(x, y, c.width, h, f"$F{{{c.name}}}", style, c.align, f"{seed}/d/{c.name}", c.pattern))
        elif style == "RowBand":
            out.append(_static(x, y, c.width, h, "", style, "Left", f"{seed}/d/blank{x}"))
        x += c.width
    return "\n".join(out)


def _total_row(cols: list[Col], style: str, seed: str, label: str, h: int = ROW_H, y: int = 0) -> str:
    x, out = 0, []
    first = True
    for c in cols:
        if c.total and c.name:
            out.append(_text(x, y, c.width, h, f"$V{{SUM_{c.name}}}", style, c.align, f"{seed}/t/{c.name}", c.pattern))
        elif first:
            out.append(_static(x, y, c.width, h, label, style, "Left", f"{seed}/t/label"))
            first = False
        elif style == "TotalText":
            out.append(_static(x, y, c.width, h, "", style, "Left", f"{seed}/t/{c.name}"))
        x += c.width
    return "\n".join(out)


def _head(name: str, page_w: int, page_h: int, margin: int, col_w: int, orientation: str = "Landscape") -> str:
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<jasperReport name="{name}" pageWidth="{page_w}" pageHeight="{page_h}" orientation="{orientation}"\n'
            f'    columnWidth="{col_w}" leftMargin="{margin}" rightMargin="{margin}" topMargin="{margin}" bottomMargin="{margin}"\n'
            f'    whenNoDataType="AllSectionsNoDetail">\n'
            f'    <property name="net.sf.jasperreports.query.timeout" value="600"/>\n'
            f'    <property name="net.sf.jasperreports.export.xls.remove.empty.space.between.rows" value="true"/>\n')


def main_jrxml(s: Spec) -> str:
    sub_params = "\n".join(
        f'                <parameter name="{p}"><expression><![CDATA[$P{{{p}}}]]></expression></parameter>'
        for p in (*s.date_params(), *s.all_params()))
    sub_key = "\n".join(f'                <parameter name="{p}"><expression><![CDATA[$F{{{f}}}]]></expression></parameter>'
                        for p, f in s.sub.keys().items())
    window = ((f'"{s.window_label} " + new java.text.SimpleDateFormat("yyyy-MM-dd").format($P{{AS_OF_DT}})' if s.as_of else
               f'"{s.window_label} " + new java.text.SimpleDateFormat("yyyy-MM-dd").format($P{{FROM_DT}}) '
               '+ " to " + new java.text.SimpleDateFormat("yyyy-MM-dd").format($P{TO_DT})')
              + (f' + "  |  {s.order_note}"' if s.order_note else "")
              + "".join((f' + ($P{{{f.param}}} == null || $P{{{f.param}}}.isEmpty() ? "" : "  |  {f.label}: " + String.join(", ", $P{{{f.param}}}))'
                         if f.multi else f' + ($P{{{f.param}}} == null ? "" : "  |  {f.label}: " + $P{{{f.param}}})') for f in s.filters))
    return (_head(s.name, PAGE_W, PAGE_H, MARGIN, COL_W) + STYLES +
            f'    <query language="SQL"><![CDATA[\n{_select_first(s.main_sql())}\n]]></query>\n'
            + _params(s.all_params(), s.as_of, s.year) + "\n"
            + _fields(s.columns) + "\n" + _variables(s.columns) + "\n"
            f'    <title height="52">\n'
            + _text(0, 0, COL_W, 26, f'"{s.label}"', "TitleSapphire", "Left", s.name + "/title") + "\n"
            + _text(0, 28, COL_W, 16, window, "H3", "Left", s.name + "/window") + "\n"
            f'    </title>\n'
            f'    <columnHeader height="{HDR_H}">\n' + _header_row(s.columns, "HeaderSapphire", s.name) + "\n"
            f'    </columnHeader>\n'
            f'    <detail>\n        <band height="{ROW_H + 6}" splitType="Prevent">\n'
            + _rule(0, 2, COL_W, s.name + "/rule", "0.75", "#006FAC") + "\n"
            + _detail_row(s.columns, "RowBand", s.name, ROW_H + 2, 3) + "\n"
            f'        </band>\n        <band height="20" splitType="Stretch">\n'
            f'            <element kind="subreport" x="24" y="0" width="{COL_W - 24}" height="20" positionType="Float" '
            f'removeLineWhenBlank="true" usingCache="false">\n'
            + sub_params + "\n" + sub_key + "\n"
            f'                <connectionExpression><![CDATA[$P{{REPORT_CONNECTION}}]]></connectionExpression>\n'
            f'                <expression><![CDATA["repo:{s.sub.name}"]]></expression>\n'
            f'            </element>\n        </band>\n    </detail>\n'
            f'    <pageFooter height="14">\n'
            + _text(0, 0, 600, 14, FOOTER, "FooterConfidential", "Left", s.name + "/foot") + "\n"
            + _text(600, 0, 150, 14, '"Page " + $V{PAGE_NUMBER} + " of"', "FooterConfidential", "Right", s.name + "/page") + "\n"
            + _text(750, 0, 52, 14, '" " + $V{PAGE_NUMBER}', "FooterConfidential", "Left", s.name + "/pages", evaluation="Report") + "\n"
            f'    </pageFooter>\n'
            f'    <summary height="{ROW_H + 8}">\n'
            + _rule(0, 2, COL_W, s.name + "/trule", "1.0", "#006FAC") + "\n"
            + _total_row(s.columns, "TotalText", s.name, "Total", ROW_H + 2, 4) + "\n"
            f'    </summary>\n</jasperReport>\n')


def sub_jrxml(s: Spec) -> str:
    sub, w = s.sub, COL_W - 24
    params = _params({**{k: ("java.lang.String", '""') for k in sub.keys()}, **s.all_params()}, s.as_of, s.year)
    header = (f'    <columnHeader height="13">\n' + _header_row(sub.columns, "SubHeader", sub.name, 12) + "\n"
              + _rule(0, 12, w, sub.name + "/hrule") + "\n    </columnHeader>\n") if sub.header else ""
    return (_head(sub.name, w, PAGE_H, 0, w) + STYLES +
            f'    <query language="SQL"><![CDATA[\n{_select_first(s.sub_sql())}\n]]></query>\n'
            + params + "\n"
            + _fields(sub.columns) + "\n" + _variables(sub.columns) + "\n"
            + header
            + f'    <detail>\n        <band height="12">\n' + _detail_row(sub.columns, "SubText", sub.name, 12) + "\n"
            f'        </band>\n    </detail>\n'
            f'    <summary height="20">\n'
            + _rule(0, 1, w, sub.name + "/srule") + "\n"
            + _total_row(sub.columns, "SubTotal", sub.name, "Subtotal", 12, 2) + "\n"
            f'    </summary>\n</jasperReport>\n')


def controls(s: Spec) -> tuple[dict, list]:
    ics = [{"id": "AS_OF_DT", "label": s.window_label, "type": "singleValueDate", "mandatory": True, "visible": True}] if s.as_of else [
        {"id": "FROM_DT", "label": f"{s.window_label} from (inclusive)", "type": "singleValueDate", "mandatory": True, "visible": True},
        {"id": "TO_DT", "label": f"{s.window_label} to (inclusive)", "type": "singleValueDate", "mandatory": True, "visible": True},
    ]
    for n, (cls, default) in s.params.items():
        ics.append({"id": n, "label": n.replace("_", " ").title(), "type": "singleValueNumber" if "Integer" in cls else "singleValueText",
                    "mandatory": False, "visible": True, "defaultValue": default.strip('"')})
    for f in s.filters:
        ic = {"id": f.param, "label": f.label if f.required else f"{f.label} (blank = all)",
              "type": ("multiSelectQuery" if f.multi else "singleSelectQuery") if f.lov_sql else f.control,
              "mandatory": f.required, "visible": True}
        if f.lov_sql:
            ic["query"] = f.lov_sql
        ics.append(ic)
    doc = {"reportUnitUri": f"{FOLDERS[s.name]}/{s.name}", "label": s.label, "description": s.description,
           "dataSources": {"DEV": "ORIGIN_DEV_DS", "QA": "C2M_QA_DS", "PROD": "C2M_PROD_DS"},
           "subreport": f"reports/subreports/{s.sub.name}.jrxml  (a local jrxml resource of the unit named {s.sub.name}; the main says repo:{s.sub.name})",
           "inputControls": ics}
    rest = [{"id": ic["id"], "type": ic["type"], "label": ic["label"], "mandatory": ic["mandatory"], "visible": ic["visible"],
             "uri": f"{FOLDERS[s.name]}/{s.name}_files/{ic['id']}"} for ic in ics]
    return doc, rest


# Where each unit lives on the server: the Standard Offering tree the tenants already carry
# (tenant-relative -- the import ZIP never names an organization). The datasource is bound
# on the report unit at import time (/DataSource/<tenant>_DS), never inside the JRXML.
# Chase, 2026-09-24: every static SQL report lives in ONE folder so a client schedules them from one
# place instead of hunting the module folders (the 2026-09 layout put each under its module).
FOLDER = "/SmartCity/Report/Standard_Offering/Standardized_Reports"
FOLDERS = {name: FOLDER for name in ("billing_by_cycle_period", "payments_by_tender_type_period", "adjustments_by_type_period",
                                     "gl_by_distribution_code_period", "adj_ap_requests_control", "aged_debt_as_of",
                                     "top_usage_customers")}

# ------------------------------------------------------------------ the specs
WINDOW = "{col} >= $P{{FROM_DT}} AND {col} < $P{{TO_DT}} + INTERVAL '1' DAY"

# the CMS_SA_SNAPSHOT arithmetic (sql/performance/snapshots/debt_mgmt/cms_sa_snapshot) for ANY day: eligible frozen
# arrears FTs with ars_dt on or before the day AND, unless As Known Today, frozen by that day; credits retire the
# oldest debt first; excess credit nets bucket 1; buckets sum to the balance.
# At College Station (35.8M FTs) the first shape joined every FT to its SA, account, segment and
# bill before anything else -- the SA/account joins served only the optional filters and the
# segment/bill joins only Age By = DUE -- then copied all 35M rows to TEMP for two passes; it ran
# 15 minutes and lost its connection (2026-10-02). Now: base reads CI_FT alone (filters are guarded
# EXISTS, the due date a scalar subquery Oracle evaluates only in the DUE branch), is INLINE so each
# pass is a scan rather than a TEMP copy, and the FIFO window runs only over SAs with a balance (an
# SA at zero is excluded from every output anyway).
AGED = '''WITH base AS (
  SELECT /*+ INLINE */ ft.sa_id, ft.ft_id, TRUNC(ft.ars_dt) AS ars_dt,
         COALESCE(ft.cur_amt, 0) AS cur_amt, COALESCE(ft.tot_amt, 0) AS tot_amt,
         CASE WHEN COALESCE(ft.cur_amt, 0) > 0 THEN ft.cur_amt ELSE 0 END AS debt_amt,
         CASE WHEN COALESCE(ft.cur_amt, 0) < 0 THEN -ft.cur_amt ELSE 0 END AS credit_amt,
         CASE WHEN $P{{AGE_BY}} = 'DUE' AND TRIM(ft.ft_type_flg) IN ('BS', 'BX')
              THEN COALESCE((SELECT TRUNC(b.due_dt) FROM CISADM.CI_BSEG bs JOIN CISADM.CI_BILL b ON b.bill_id = bs.bill_id WHERE bs.bseg_id = ft.sibling_id), TRUNC(ft.ars_dt))
              ELSE TRUNC(ft.ars_dt) END AS aging_dt
  FROM CISADM.CI_FT ft
  WHERE TRIM(ft.freeze_sw) = 'Y' AND TRIM(ft.not_in_ars_sw) = 'N' AND ft.ars_dt IS NOT NULL
    AND TRUNC(ft.ars_dt) <= $P{{AS_OF_DT}}
    AND ($P{{AS_KNOWN_TODAY}} = 'Y' OR ft.freeze_dttm < $P{{AS_OF_DT}} + INTERVAL '1' DAY){restrict}
    /*FILTERS*/
),
sa_tot AS (
  SELECT /*+ MATERIALIZE */ sa_id, SUM(cur_amt) AS cur_bal, SUM(tot_amt) AS tot_bal, SUM(debt_amt) AS total_debt, SUM(credit_amt) AS total_credit
  FROM base
  GROUP BY sa_id
),
debt_rows AS (
  SELECT b.sa_id, b.aging_dt, b.debt_amt,
         SUM(b.debt_amt) OVER (PARTITION BY b.sa_id ORDER BY b.ars_dt, b.ft_id ROWS UNBOUNDED PRECEDING) AS cum_debt
  FROM base b
  JOIN sa_tot t ON t.sa_id = b.sa_id AND t.cur_bal <> 0
  WHERE b.debt_amt > 0
),
unpaid AS (
  SELECT d.sa_id, d.aging_dt,
         GREATEST(0, d.cum_debt - t.total_credit) - GREATEST(0, d.cum_debt - d.debt_amt - t.total_credit) AS unpaid_amt
  FROM debt_rows d
  JOIN sa_tot t ON t.sa_id = d.sa_id
),
aged AS (
  SELECT sa_id,
         SUM(CASE WHEN GREATEST(0, $P{{AS_OF_DT}} - aging_dt) BETWEEN 0 AND 30 THEN unpaid_amt ELSE 0 END) AS ars_amt1,
         SUM(CASE WHEN GREATEST(0, $P{{AS_OF_DT}} - aging_dt) BETWEEN 31 AND 60 THEN unpaid_amt ELSE 0 END) AS ars_amt2,
         SUM(CASE WHEN GREATEST(0, $P{{AS_OF_DT}} - aging_dt) BETWEEN 61 AND 90 THEN unpaid_amt ELSE 0 END) AS ars_amt3,
         SUM(CASE WHEN GREATEST(0, $P{{AS_OF_DT}} - aging_dt) BETWEEN 91 AND 120 THEN unpaid_amt ELSE 0 END) AS ars_amt4,
         SUM(CASE WHEN GREATEST(0, $P{{AS_OF_DT}} - aging_dt) > 120 THEN unpaid_amt ELSE 0 END) AS ars_amt5
  FROM unpaid
  GROUP BY sa_id
),
sa_pos AS (
  SELECT t.sa_id, t.cur_bal, t.tot_bal,
         COALESCE(a.ars_amt1, 0) - GREATEST(0, t.total_credit - t.total_debt) AS ars_amt1,
         COALESCE(a.ars_amt2, 0) AS ars_amt2, COALESCE(a.ars_amt3, 0) AS ars_amt3,
         COALESCE(a.ars_amt4, 0) AS ars_amt4, COALESCE(a.ars_amt5, 0) AS ars_amt5
  FROM sa_tot t
  LEFT JOIN aged a ON a.sa_id = t.sa_id
)
'''

SPECS: list[Spec] = [
    Spec(
        name="billing_by_cycle_period", label="Billing by Cycle",
        window_label="Bill date",
        description="Completed bills in a bill-date window: bills, accounts, frozen segments and billed amount per bill cycle, with a service-type breakdown under each cycle.",
        order_note="completed bills, frozen segments; billed = calc headers",
        sql=f"""
SELECT COALESCE(NULLIF(TRIM(b.bill_cyc_cd), ''), '(none)') AS BILL_CYC_CD,
       COALESCE(cl.descr, CASE WHEN NULLIF(TRIM(b.bill_cyc_cd), '') IS NULL THEN 'Off-cycle / no bill cycle' ELSE TRIM(b.bill_cyc_cd) END) AS BILL_CYC_DESCR,
       COUNT(DISTINCT b.bill_id)  AS BILLS,
       COUNT(DISTINCT b.acct_id)  AS ACCOUNTS,
       COUNT(DISTINCT s.bseg_id)  AS SEGMENTS,
       COUNT(DISTINCT CASE WHEN TRIM(s.est_sw) = 'Y' THEN s.bseg_id END) AS ESTIMATED_SEGMENTS,
       COALESCE(SUM(h.calc_amt), 0) AS BILLED_AMT
FROM CISADM.CI_BILL b
JOIN CISADM.CI_BSEG s ON s.bill_id = b.bill_id AND TRIM(s.bseg_stat_flg) = '50'
LEFT JOIN CISADM.CI_BSEG_CALC h ON h.bseg_id = s.bseg_id
LEFT JOIN CISADM.CI_BILL_CYC_L cl ON cl.bill_cyc_cd = b.bill_cyc_cd AND cl.language_cd = 'ENG'
WHERE TRIM(b.bill_stat_flg) = 'C' AND {WINDOW.format(col='b.bill_dt')}
GROUP BY COALESCE(NULLIF(TRIM(b.bill_cyc_cd), ''), '(none)'),
         COALESCE(cl.descr, CASE WHEN NULLIF(TRIM(b.bill_cyc_cd), '') IS NULL THEN 'Off-cycle / no bill cycle' ELSE TRIM(b.bill_cyc_cd) END)
ORDER BY BILLED_AMT DESC""",
        columns=[Col("BILL_CYC_CD", "Cycle", width=70), Col("BILL_CYC_DESCR", "Bill Cycle", width=252),
                 Col("BILLS", "Bills", "java.lang.Long", 90, "Right", INT, True), Col("ACCOUNTS", "Accounts", "java.lang.Long", 90, "Right", INT, True),
                 Col("SEGMENTS", "Segments", "java.lang.Long", 90, "Right", INT, True), Col("ESTIMATED_SEGMENTS", "Estimated", "java.lang.Long", 90, "Right", INT, True),
                 Col("BILLED_AMT", "Billed Amount", "java.math.BigDecimal", 120, "Right", MONEY, True)],
        sub=Sub(
            name="billing_by_cycle_service_type", key_param="BILL_CYC_CD", key_field="BILL_CYC_CD",
            intro='"By service type in cycle " + $P{BILL_CYC_CD}',
            sql=f"""
SELECT SVC_TYPE_CD, SVC_TYPE_DESCR, SERVICE_AGREEMENTS, SEGMENTS, ESTIMATED_SEGMENTS, BILLED_AMT FROM (
  SELECT /*+ RESULT_CACHE */ COALESCE(NULLIF(TRIM(b.bill_cyc_cd), ''), '(none)') AS BILL_CYC_CD,
         TRIM(t.svc_type_cd) AS SVC_TYPE_CD, COALESCE(sl.descr, TRIM(t.svc_type_cd)) AS SVC_TYPE_DESCR,
         COUNT(DISTINCT s.sa_id) AS SERVICE_AGREEMENTS,
         COUNT(DISTINCT s.bseg_id) AS SEGMENTS,
         COUNT(DISTINCT CASE WHEN TRIM(s.est_sw) = 'Y' THEN s.bseg_id END) AS ESTIMATED_SEGMENTS,
         COALESCE(SUM(h.calc_amt), 0) AS BILLED_AMT
  FROM CISADM.CI_BILL b
  JOIN CISADM.CI_BSEG s ON s.bill_id = b.bill_id AND TRIM(s.bseg_stat_flg) = '50'
  JOIN CISADM.CI_SA sa ON sa.sa_id = s.sa_id
  JOIN CISADM.CI_SA_TYPE t ON t.sa_type_cd = sa.sa_type_cd AND t.cis_division = sa.cis_division
  LEFT JOIN CISADM.CI_SVC_TYPE_L sl ON sl.svc_type_cd = t.svc_type_cd AND sl.language_cd = 'ENG'
  LEFT JOIN CISADM.CI_BSEG_CALC h ON h.bseg_id = s.bseg_id
  WHERE TRIM(b.bill_stat_flg) = 'C' AND {WINDOW.format(col='b.bill_dt')}
    /*FILTERS*/
  GROUP BY COALESCE(NULLIF(TRIM(b.bill_cyc_cd), ''), '(none)'), TRIM(t.svc_type_cd), COALESCE(sl.descr, TRIM(t.svc_type_cd))
) x
WHERE x.BILL_CYC_CD = $P{{BILL_CYC_CD}}
ORDER BY BILLED_AMT DESC""",
            header=True,
            columns=[Col("SVC_TYPE_CD", "Type", width=46), Col("SVC_TYPE_DESCR", "Service Type", width=252),
                     Col(None, "", width=90), Col("SERVICE_AGREEMENTS", "SAs", "java.lang.Long", 90, "Right", INT, True),
                     Col("SEGMENTS", "Segments", "java.lang.Long", 90, "Right", INT, True),
                     Col("ESTIMATED_SEGMENTS", "Estimated", "java.lang.Long", 90, "Right", INT, True),
                     Col("BILLED_AMT", "Billed Amount", "java.math.BigDecimal", 120, "Right", MONEY, True)]),
        filters=[
            Filter("BILL_CYC_CD_F", "Bill cycles",
                   "$X{IN, TRIM(b.bill_cyc_cd), BILL_CYC_CD_F}",
                   "$X{IN, TRIM(b.bill_cyc_cd), BILL_CYC_CD_F}", multi=True,
                   lov_sql="SELECT TRIM(bill_cyc_cd) AS CODE, TRIM(bill_cyc_cd) || ' - ' || descr AS DESCR FROM CISADM.CI_BILL_CYC_L l WHERE l.language_cd = 'ENG' AND EXISTS (SELECT 1 FROM CISADM.CI_BILL b WHERE b.bill_cyc_cd = l.bill_cyc_cd AND b.bill_dt >= CURRENT_DATE - INTERVAL '3' YEAR) ORDER BY 1"),
            Filter("SVC_TYPE_CD_F", "Service type",
                   "($P{SVC_TYPE_CD_F} IS NULL OR EXISTS (SELECT 1 FROM CISADM.CI_SA fsa JOIN CISADM.CI_SA_TYPE ft ON ft.sa_type_cd = fsa.sa_type_cd AND ft.cis_division = fsa.cis_division WHERE fsa.sa_id = s.sa_id AND TRIM(ft.svc_type_cd) = TRIM($P{SVC_TYPE_CD_F})))",
                   "($P{SVC_TYPE_CD_F} IS NULL OR TRIM(t.svc_type_cd) = TRIM($P{SVC_TYPE_CD_F}))",
                   lov_sql="SELECT TRIM(svc_type_cd) AS CODE, TRIM(svc_type_cd) || ' - ' || descr AS DESCR FROM CISADM.CI_SVC_TYPE_L l WHERE l.language_cd = 'ENG' AND EXISTS (SELECT 1 FROM CISADM.CI_SA_TYPE t JOIN CISADM.CI_SA sa ON sa.sa_type_cd = t.sa_type_cd AND sa.cis_division = t.cis_division WHERE t.svc_type_cd = l.svc_type_cd AND (sa.end_dt IS NULL OR sa.end_dt >= CURRENT_DATE - INTERVAL '3' YEAR)) ORDER BY 1"),
            Filter("CIS_DIVISION_F", "CIS division",
                   "($P{CIS_DIVISION_F} IS NULL OR EXISTS (SELECT 1 FROM CISADM.CI_ACCT fa WHERE fa.acct_id = b.acct_id AND TRIM(fa.cis_division) = TRIM($P{CIS_DIVISION_F})))",
                   "($P{CIS_DIVISION_F} IS NULL OR TRIM(sa.cis_division) = TRIM($P{CIS_DIVISION_F}))",
                   lov_sql="SELECT TRIM(cis_division) AS CODE, TRIM(cis_division) || ' - ' || descr AS DESCR FROM CISADM.CI_CIS_DIVISION_L l WHERE l.language_cd = 'ENG' AND EXISTS (SELECT 1 FROM CISADM.CI_SA sa WHERE sa.cis_division = l.cis_division AND (sa.end_dt IS NULL OR sa.end_dt >= CURRENT_DATE - INTERVAL '3' YEAR)) ORDER BY 1"),
            Filter("ACCT_ID_F", "Account ID",
                   "($P{ACCT_ID_F} IS NULL OR TRIM(b.acct_id) = TRIM($P{ACCT_ID_F}))",
                   "($P{ACCT_ID_F} IS NULL OR TRIM(b.acct_id) = TRIM($P{ACCT_ID_F}))"),
        ]),

    Spec(
        name="payments_by_tender_type_period", label="Payments by Tender Type",
        window_label="Payment date",
        description="Tenders in a payment-date window by tender type: count and amount of live tenders, cancelled tenders shown apart, with a month-by-month breakdown under each type.",
        order_note="cancelled = tender carries a cancel reason",
        sql=f"""
SELECT TRIM(t.tender_type_cd) AS TENDER_TYPE_CD, COALESCE(tl.descr, TRIM(t.tender_type_cd)) AS TENDER_TYPE_DESCR,
       COUNT(CASE WHEN NULLIF(TRIM(t.can_rsn_cd), '') IS NULL THEN 1 END) AS TENDERS,
       COALESCE(SUM(CASE WHEN NULLIF(TRIM(t.can_rsn_cd), '') IS NULL THEN t.tender_amt ELSE 0 END), 0) AS TENDER_AMT,
       COUNT(CASE WHEN NULLIF(TRIM(t.can_rsn_cd), '') IS NOT NULL THEN 1 END) AS CANCELLED,
       COALESCE(SUM(CASE WHEN NULLIF(TRIM(t.can_rsn_cd), '') IS NOT NULL THEN t.tender_amt ELSE 0 END), 0) AS CANCELLED_AMT,
       COUNT(DISTINCT t.payor_acct_id) AS PAYOR_ACCOUNTS
FROM CISADM.CI_PAY_TNDR t
JOIN CISADM.CI_PAY_EVENT e ON e.pay_event_id = t.pay_event_id
LEFT JOIN CISADM.CI_TENDER_TYPE_L tl ON tl.tender_type_cd = t.tender_type_cd AND tl.language_cd = 'ENG'
WHERE {WINDOW.format(col='e.pay_dt')}
GROUP BY TRIM(t.tender_type_cd), COALESCE(tl.descr, TRIM(t.tender_type_cd))
ORDER BY TENDER_AMT DESC""",
        columns=[Col("TENDER_TYPE_CD", "Type", width=60), Col("TENDER_TYPE_DESCR", "Tender Type", width=232),
                 Col("TENDERS", "Tenders", "java.lang.Long", 80, "Right", INT, True), Col("TENDER_AMT", "Amount", "java.math.BigDecimal", 120, "Right", MONEY, True),
                 Col("CANCELLED", "Cancelled", "java.lang.Long", 80, "Right", INT, True), Col("CANCELLED_AMT", "Cancelled Amt", "java.math.BigDecimal", 120, "Right", MONEY, True),
                 Col("PAYOR_ACCOUNTS", "Payors", "java.lang.Long", 110, "Right", INT, True)],
        sub=Sub(
            name="payments_by_tender_type_month", key_param="TENDER_TYPE_CD", key_field="TENDER_TYPE_CD",
            intro='"By month for tender type " + $P{TENDER_TYPE_CD}',
            sql=f"""
SELECT TO_CHAR(e.pay_dt, 'YYYY-MM') AS PAY_MONTH,
       COUNT(CASE WHEN NULLIF(TRIM(t.can_rsn_cd), '') IS NULL THEN 1 END) AS TENDERS,
       COALESCE(SUM(CASE WHEN NULLIF(TRIM(t.can_rsn_cd), '') IS NULL THEN t.tender_amt ELSE 0 END), 0) AS TENDER_AMT,
       COUNT(CASE WHEN NULLIF(TRIM(t.can_rsn_cd), '') IS NOT NULL THEN 1 END) AS CANCELLED,
       COUNT(DISTINCT t.payor_acct_id) AS PAYOR_ACCOUNTS
FROM CISADM.CI_PAY_TNDR t
JOIN CISADM.CI_PAY_EVENT e ON e.pay_event_id = t.pay_event_id
WHERE {WINDOW.format(col='e.pay_dt')} AND TRIM(t.tender_type_cd) = TRIM($P{{TENDER_TYPE_CD}})
GROUP BY TO_CHAR(e.pay_dt, 'YYYY-MM')
ORDER BY PAY_MONTH""",
            columns=[Col("PAY_MONTH", "Month", width=268), Col("TENDERS", "Tenders", "java.lang.Long", 80, "Right", INT, True),
                     Col("TENDER_AMT", "Amount", "java.math.BigDecimal", 120, "Right", MONEY, True), Col("CANCELLED", "Cancelled", "java.lang.Long", 80, "Right", INT, True),
                     Col(None, "", width=120), Col("PAYOR_ACCOUNTS", "Payors", "java.lang.Long", 110, "Right", INT, True)]),
        filters=[
            Filter("TENDER_TYPE_CD_F", "Tender types",
                   "$X{IN, TRIM(t.tender_type_cd), TENDER_TYPE_CD_F}",
                   "$X{IN, TRIM(t.tender_type_cd), TENDER_TYPE_CD_F}", multi=True,
                   lov_sql="SELECT TRIM(tender_type_cd) AS CODE, TRIM(tender_type_cd) || ' - ' || descr AS DESCR FROM CISADM.CI_TENDER_TYPE_L l WHERE l.language_cd = 'ENG' AND EXISTS (SELECT 1 FROM CISADM.CI_PAY_TNDR t JOIN CISADM.CI_PAY_EVENT e ON e.pay_event_id = t.pay_event_id WHERE t.tender_type_cd = l.tender_type_cd AND e.pay_dt >= CURRENT_DATE - INTERVAL '3' YEAR) ORDER BY 1"),
            Filter("PAYOR_ACCT_ID_F", "Payor account ID",
                   "($P{PAYOR_ACCT_ID_F} IS NULL OR TRIM(t.payor_acct_id) = TRIM($P{PAYOR_ACCT_ID_F}))",
                   "($P{PAYOR_ACCT_ID_F} IS NULL OR TRIM(t.payor_acct_id) = TRIM($P{PAYOR_ACCT_ID_F}))"),
            Filter("TNDR_CTL_ID_F", "Tender control ID",
                   "($P{TNDR_CTL_ID_F} IS NULL OR TRIM(t.tndr_ctl_id) = TRIM($P{TNDR_CTL_ID_F}))",
                   "($P{TNDR_CTL_ID_F} IS NULL OR TRIM(t.tndr_ctl_id) = TRIM($P{TNDR_CTL_ID_F}))"),
            Filter("MIN_AMT_F", "Minimum tender amount",
                   "($P{MIN_AMT_F} IS NULL OR t.tender_amt >= $P{MIN_AMT_F})",
                   "($P{MIN_AMT_F} IS NULL OR t.tender_amt >= $P{MIN_AMT_F})", "java.math.BigDecimal", "singleValueNumber"),
        ]),

    Spec(
        name="adjustments_by_type_period", label="Adjustments by Type",
        window_label="Adjustment created date",
        description="Frozen adjustments created in a date window by adjustment type: count, net amount, largest and smallest, with the ten largest adjustments (account and customer) under each type.",
        order_note="frozen adjustments by creation date",
        params={"TOP_N": ("java.lang.Integer", "10")},
        sql=f"""
SELECT TRIM(a.adj_type_cd) AS ADJ_TYPE_CD, COALESCE(al.descr, TRIM(a.adj_type_cd)) AS ADJ_TYPE_DESCR,
       COUNT(*) AS ADJUSTMENTS, COALESCE(SUM(a.adj_amt), 0) AS NET_AMT,
       COALESCE(SUM(CASE WHEN a.adj_amt > 0 THEN a.adj_amt ELSE 0 END), 0) AS DEBIT_AMT,
       COALESCE(SUM(CASE WHEN a.adj_amt < 0 THEN a.adj_amt ELSE 0 END), 0) AS CREDIT_AMT,
       MAX(a.adj_amt) AS LARGEST, MIN(a.adj_amt) AS SMALLEST
FROM CISADM.CI_ADJ a
LEFT JOIN CISADM.CI_ADJ_TYPE_L al ON al.adj_type_cd = a.adj_type_cd AND al.language_cd = 'ENG'
WHERE TRIM(a.adj_status_flg) = '50' AND {WINDOW.format(col='a.cre_dt')}
GROUP BY TRIM(a.adj_type_cd), COALESCE(al.descr, TRIM(a.adj_type_cd))
ORDER BY ABS(COALESCE(SUM(a.adj_amt), 0)) DESC""",
        columns=[Col("ADJ_TYPE_CD", "Type", width=70), Col("ADJ_TYPE_DESCR", "Adjustment Type", width=222),
                 Col("ADJUSTMENTS", "Count", "java.lang.Long", 60, "Right", INT, True), Col("NET_AMT", "Net Amount", "java.math.BigDecimal", 110, "Right", MONEY, True),
                 Col("DEBIT_AMT", "Debits", "java.math.BigDecimal", 100, "Right", MONEY, True), Col("CREDIT_AMT", "Credits", "java.math.BigDecimal", 100, "Right", MONEY, True),
                 Col("LARGEST", "Largest", "java.math.BigDecimal", 70, "Right", MONEY), Col("SMALLEST", "Smallest", "java.math.BigDecimal", 70, "Right", MONEY)],
        sub=Sub(
            name="adjustments_by_type_top", key_param="ADJ_TYPE_CD", key_field="ADJ_TYPE_CD",
            intro='"Largest adjustments of type " + $P{ADJ_TYPE_CD}',
            sql=f"""
SELECT x.ADJ_ID, x.CRE_DT, x.SA_ID, TRIM(sa.acct_id) AS ACCT_ID, pn.entity_name AS CUSTOMER_NAME, x.ADJ_AMT
FROM (
  SELECT /*+ RESULT_CACHE */ TRIM(a.adj_type_cd) AS ADJ_TYPE_CD, TRIM(a.adj_id) AS ADJ_ID, a.cre_dt AS CRE_DT, a.sa_id AS SA_ID, a.adj_amt AS ADJ_AMT,
         ROW_NUMBER() OVER (PARTITION BY TRIM(a.adj_type_cd) ORDER BY ABS(a.adj_amt) DESC, a.adj_id) AS RN
  FROM CISADM.CI_ADJ a
  WHERE TRIM(a.adj_status_flg) = '50' AND {WINDOW.format(col='a.cre_dt')}
    /*FILTERS*/
) x
JOIN CISADM.CI_SA sa ON sa.sa_id = x.SA_ID
LEFT JOIN CISADM.CI_ACCT_PER ap ON ap.acct_id = sa.acct_id AND TRIM(ap.main_cust_sw) = 'Y'
LEFT JOIN CISADM.CI_PER_NAME pn ON pn.per_id = ap.per_id AND TRIM(pn.name_type_flg) = 'PRIM'
WHERE x.ADJ_TYPE_CD = TRIM($P{{ADJ_TYPE_CD}}) AND x.RN <= $P{{TOP_N}}
ORDER BY x.RN""",
            header=True,
            columns=[Col("ADJ_ID", "Adjustment", width=90), Col("CRE_DT", "Created", "java.sql.Timestamp", 80, "Center", "yyyy-MM-dd"),
                     Col("SA_ID", "SA", width=90), Col("ACCT_ID", "Account", width=90), Col("CUSTOMER_NAME", "Main Customer", width=308),
                     Col("ADJ_AMT", "Amount", "java.math.BigDecimal", 120, "Right", MONEY, True)]),
        filters=[
            Filter("ADJ_TYPE_CD_F", "Adjustment type",
                   "($P{ADJ_TYPE_CD_F} IS NULL OR TRIM(a.adj_type_cd) = TRIM($P{ADJ_TYPE_CD_F}))",
                   "($P{ADJ_TYPE_CD_F} IS NULL OR TRIM(a.adj_type_cd) = TRIM($P{ADJ_TYPE_CD_F}))",
                   lov_sql="SELECT TRIM(adj_type_cd) AS CODE, TRIM(adj_type_cd) || ' - ' || descr AS DESCR FROM CISADM.CI_ADJ_TYPE_L l WHERE l.language_cd = 'ENG' AND EXISTS (SELECT 1 FROM CISADM.CI_ADJ a WHERE a.adj_type_cd = l.adj_type_cd AND a.cre_dt >= CURRENT_DATE - INTERVAL '3' YEAR) ORDER BY 1"),
            Filter("ACCT_ID_F", "Account ID",
                   "($P{ACCT_ID_F} IS NULL OR EXISTS (SELECT 1 FROM CISADM.CI_SA fsa WHERE fsa.sa_id = a.sa_id AND TRIM(fsa.acct_id) = TRIM($P{ACCT_ID_F})))",
                   "($P{ACCT_ID_F} IS NULL OR EXISTS (SELECT 1 FROM CISADM.CI_SA fsa WHERE fsa.sa_id = a.sa_id AND TRIM(fsa.acct_id) = TRIM($P{ACCT_ID_F})))"),
            Filter("SA_ID_F", "Service agreement ID",
                   "($P{SA_ID_F} IS NULL OR TRIM(a.sa_id) = TRIM($P{SA_ID_F}))",
                   "($P{SA_ID_F} IS NULL OR TRIM(a.sa_id) = TRIM($P{SA_ID_F}))"),
            Filter("MIN_ABS_AMT_F", "Minimum absolute amount",
                   "($P{MIN_ABS_AMT_F} IS NULL OR ABS(a.adj_amt) >= $P{MIN_ABS_AMT_F})",
                   "($P{MIN_ABS_AMT_F} IS NULL OR ABS(a.adj_amt) >= $P{MIN_ABS_AMT_F})", "java.math.BigDecimal", "singleValueNumber"),
        ]),

    Spec(
        name="gl_by_distribution_code_period", label="GL Activity by Distribution Code",
        window_label="Accounting date",
        description="GL lines of frozen financial transactions in an accounting-date window by distribution code and GL account: lines, debits, credits and net, with a month-by-month breakdown under each code.",
        order_note="frozen FTs by accounting date; net = sum of GL amounts",
        sql=f"""
SELECT TRIM(g.dst_id) AS DST_ID, COALESCE(TRIM(g.gl_acct), '(no GL account)') AS GL_ACCT,
       COUNT(*) AS GL_LINES, COUNT(DISTINCT f.ft_id) AS TRANSACTIONS,
       COALESCE(SUM(CASE WHEN g.amount > 0 THEN g.amount ELSE 0 END), 0) AS DEBIT_AMT,
       COALESCE(SUM(CASE WHEN g.amount < 0 THEN -g.amount ELSE 0 END), 0) AS CREDIT_AMT,
       COALESCE(SUM(g.amount), 0) AS NET_AMT
FROM CISADM.CI_FT_GL g
JOIN CISADM.CI_FT f ON f.ft_id = g.ft_id
WHERE TRIM(f.freeze_sw) = 'Y' AND {WINDOW.format(col='f.accounting_dt')}
GROUP BY TRIM(g.dst_id), COALESCE(TRIM(g.gl_acct), '(no GL account)')
ORDER BY ABS(COALESCE(SUM(g.amount), 0)) DESC""",
        columns=[Col("DST_ID", "Distribution Code", width=120), Col("GL_ACCT", "GL Account", width=232),
                 Col("GL_LINES", "Lines", "java.lang.Long", 70, "Right", INT, True), Col("TRANSACTIONS", "FTs", "java.lang.Long", 70, "Right", INT, True),
                 Col("DEBIT_AMT", "Debits", "java.math.BigDecimal", 100, "Right", MONEY, True), Col("CREDIT_AMT", "Credits", "java.math.BigDecimal", 100, "Right", MONEY, True),
                 Col("NET_AMT", "Net", "java.math.BigDecimal", 110, "Right", MONEY, True)],
        sub=Sub(
            name="gl_by_distribution_code_month", key_param="DST_ID", key_field="DST_ID",
            extra_keys={"GL_ACCT": "GL_ACCT"},
            intro='"By accounting month for distribution code " + $P{DST_ID} + ", GL account " + $P{GL_ACCT}',
            sql=f"""
SELECT ACCT_MONTH, GL_LINES, DEBIT_AMT, CREDIT_AMT, NET_AMT FROM (
  SELECT /*+ RESULT_CACHE */ TRIM(g.dst_id) AS DST_ID, COALESCE(TRIM(g.gl_acct), '(no GL account)') AS GL_ACCT,
         TO_CHAR(f.accounting_dt, 'YYYY-MM') AS ACCT_MONTH, COUNT(*) AS GL_LINES,
         COALESCE(SUM(CASE WHEN g.amount > 0 THEN g.amount ELSE 0 END), 0) AS DEBIT_AMT,
         COALESCE(SUM(CASE WHEN g.amount < 0 THEN -g.amount ELSE 0 END), 0) AS CREDIT_AMT,
         COALESCE(SUM(g.amount), 0) AS NET_AMT
  FROM CISADM.CI_FT_GL g
  JOIN CISADM.CI_FT f ON f.ft_id = g.ft_id
  WHERE TRIM(f.freeze_sw) = 'Y' AND {WINDOW.format(col='f.accounting_dt')}
    /*FILTERS*/
  GROUP BY TRIM(g.dst_id), COALESCE(TRIM(g.gl_acct), '(no GL account)'), TO_CHAR(f.accounting_dt, 'YYYY-MM')
) x
WHERE x.DST_ID = TRIM($P{{DST_ID}}) AND x.GL_ACCT = $P{{GL_ACCT}}
ORDER BY ACCT_MONTH""",
            columns=[Col("ACCT_MONTH", "Month", width=328), Col("GL_LINES", "Lines", "java.lang.Long", 70, "Right", INT, True),
                     Col(None, "", width=70),
                     Col("DEBIT_AMT", "Debits", "java.math.BigDecimal", 100, "Right", MONEY, True), Col("CREDIT_AMT", "Credits", "java.math.BigDecimal", 100, "Right", MONEY, True),
                     Col("NET_AMT", "Net", "java.math.BigDecimal", 110, "Right", MONEY, True)]),
        filters=[
            Filter("DST_ID_F", "Distribution code",
                   "($P{DST_ID_F} IS NULL OR TRIM(g.dst_id) = TRIM($P{DST_ID_F}))",
                   "($P{DST_ID_F} IS NULL OR TRIM(g.dst_id) = TRIM($P{DST_ID_F}))",
                   lov_sql="SELECT TRIM(dst_id) AS CODE, TRIM(dst_id) || ' - ' || descr AS DESCR FROM CISADM.CI_DST_CODE_L l WHERE l.language_cd = 'ENG' AND EXISTS (SELECT 1 FROM CISADM.CI_FT_GL g JOIN CISADM.CI_FT f ON f.ft_id = g.ft_id WHERE g.dst_id = l.dst_id AND f.accounting_dt >= CURRENT_DATE - INTERVAL '3' YEAR) ORDER BY 1"),
            Filter("GL_ACCT_F", "GL account (exact)",
                   "($P{GL_ACCT_F} IS NULL OR TRIM(g.gl_acct) = TRIM($P{GL_ACCT_F}))",
                   "($P{GL_ACCT_F} IS NULL OR TRIM(g.gl_acct) = TRIM($P{GL_ACCT_F}))"),
            Filter("GL_DIVISION_F", "GL division",
                   "($P{GL_DIVISION_F} IS NULL OR TRIM(f.gl_division) = TRIM($P{GL_DIVISION_F}))",
                   "($P{GL_DIVISION_F} IS NULL OR TRIM(f.gl_division) = TRIM($P{GL_DIVISION_F}))",
                   lov_sql="SELECT TRIM(gl_division) AS CODE, TRIM(gl_division) || ' - ' || descr AS DESCR FROM CISADM.CI_GL_DIVISION_L l WHERE l.language_cd = 'ENG' AND EXISTS (SELECT 1 FROM CISADM.CI_FT f WHERE f.gl_division = l.gl_division AND f.accounting_dt >= CURRENT_DATE - INTERVAL '3' YEAR) ORDER BY 1"),
            Filter("CIS_DIVISION_F", "CIS division",
                   "($P{CIS_DIVISION_F} IS NULL OR TRIM(f.cis_division) = TRIM($P{CIS_DIVISION_F}))",
                   "($P{CIS_DIVISION_F} IS NULL OR TRIM(f.cis_division) = TRIM($P{CIS_DIVISION_F}))",
                   lov_sql="SELECT TRIM(cis_division) AS CODE, TRIM(cis_division) || ' - ' || descr AS DESCR FROM CISADM.CI_CIS_DIVISION_L l WHERE l.language_cd = 'ENG' AND EXISTS (SELECT 1 FROM CISADM.CI_SA sa WHERE sa.cis_division = l.cis_division AND (sa.end_dt IS NULL OR sa.end_dt >= CURRENT_DATE - INTERVAL '3' YEAR)) ORDER BY 1"),
            Filter("FT_TYPE_FLG_F", "FT type (BS, BX, AD, AX, PS, PX)",
                   "($P{FT_TYPE_FLG_F} IS NULL OR TRIM(f.ft_type_flg) = TRIM($P{FT_TYPE_FLG_F}))",
                   "($P{FT_TYPE_FLG_F} IS NULL OR TRIM(f.ft_type_flg) = TRIM($P{FT_TYPE_FLG_F}))",
                   lov_sql="SELECT TRIM(field_value) AS CODE, TRIM(field_value) || ' - ' || descr AS DESCR FROM CISADM.CI_LOOKUP_VAL_L l WHERE l.field_name = 'FT_TYPE_FLG' AND l.language_cd = 'ENG' AND EXISTS (SELECT 1 FROM CISADM.CI_FT f WHERE f.ft_type_flg = l.field_value AND f.accounting_dt >= CURRENT_DATE - INTERVAL '3' YEAR) ORDER BY 1"),
        ]),
    Spec(
        name="adj_ap_requests_control", label="Adjustment A/P Requests - Control",
        window_label="Adjustment created date",
        description="Every adjustment A/P request in a window, grouped by request status and adjustment status, with the action each combination needs: a request the ERP canceled while the adjustment is still open must have its adjustment canceled by a user; a paid request on a canceled adjustment is a refund to recover. The requests behind each combination are listed underneath.",
        order_note="one row per A/P request; the request-to-adjustment link is one-to-one (measured Odessa 2026-09-23: 16 of 16); the adjustment's service agreement can be missing (2 of 16), so account and customer are outer",
        constants={"X": "PYMNT_SEL_STAT_FLG canceled (base-product A/P request lifecycle)",
                   "P": "PYMNT_SEL_STAT_FLG paid",
                   "60": "ADJ_STATUS_FLG canceled (base-product adjustment lifecycle; 30 freezable, 50 frozen)",
                   "PYMNT_SEL_STAT_FLG": "lookup field name", "ADJ_STATUS_FLG": "lookup field name"},
        sql=f"""
SELECT TRIM(r.pymnt_sel_stat_flg) AS REQ_STATUS, COALESCE(rl.descr, TRIM(r.pymnt_sel_stat_flg)) AS REQ_STATUS_DESCR,
       TRIM(a.adj_status_flg) AS ADJ_STATUS, COALESCE(al.descr, TRIM(a.adj_status_flg)) AS ADJ_STATUS_DESCR,
       CASE WHEN TRIM(r.pymnt_sel_stat_flg) = 'X' AND TRIM(a.adj_status_flg) IN ('30', '50') THEN 'Cancel the adjustment: its A/P request was canceled'
            WHEN TRIM(r.pymnt_sel_stat_flg) = 'P' AND TRIM(a.adj_status_flg) = '60' THEN 'Paid, but the adjustment was canceled: recover'
            ELSE ' ' END AS ACTION,
       COUNT(*) AS REQUESTS, COALESCE(SUM(a.adj_amt), 0) AS ADJ_AMT, COALESCE(SUM(r.paid_amt), 0) AS PAID_AMT
FROM CISADM.CI_ADJ_APREQ r
JOIN CISADM.CI_ADJ a ON a.adj_id = r.adj_id
LEFT JOIN CISADM.CI_LOOKUP_VAL_L rl ON TRIM(rl.field_name) = 'PYMNT_SEL_STAT_FLG' AND TRIM(rl.field_value) = TRIM(r.pymnt_sel_stat_flg) AND rl.language_cd = 'ENG'
LEFT JOIN CISADM.CI_LOOKUP_VAL_L al ON TRIM(al.field_name) = 'ADJ_STATUS_FLG' AND TRIM(al.field_value) = TRIM(a.adj_status_flg) AND al.language_cd = 'ENG'
WHERE {WINDOW.format(col='a.cre_dt')}
GROUP BY TRIM(r.pymnt_sel_stat_flg), COALESCE(rl.descr, TRIM(r.pymnt_sel_stat_flg)), TRIM(a.adj_status_flg), COALESCE(al.descr, TRIM(a.adj_status_flg))
ORDER BY CASE WHEN TRIM(r.pymnt_sel_stat_flg) = 'X' AND TRIM(a.adj_status_flg) IN ('30', '50') THEN 0
              WHEN TRIM(r.pymnt_sel_stat_flg) = 'P' AND TRIM(a.adj_status_flg) = '60' THEN 1 ELSE 2 END,
         TRIM(r.pymnt_sel_stat_flg), TRIM(a.adj_status_flg)""",
        columns=[Col("REQ_STATUS", "Req", width=40), Col("REQ_STATUS_DESCR", "A/P Request Status", width=150),
                 Col("ADJ_STATUS", "Adj", width=40), Col("ADJ_STATUS_DESCR", "Adjustment Status", width=120),
                 Col("ACTION", "Action", width=182),
                 Col("REQUESTS", "Requests", "java.lang.Long", 70, "Right", INT, True),
                 Col("ADJ_AMT", "Adjustment Amount", "java.math.BigDecimal", 100, "Right", MONEY, True),
                 Col("PAID_AMT", "Paid Amount", "java.math.BigDecimal", 100, "Right", MONEY, True)],
        sub=Sub(
            name="adj_ap_requests_detail", key_param="REQ_STATUS", key_field="REQ_STATUS",
            extra_keys={"ADJ_STATUS": "ADJ_STATUS"},
            intro='"Requests"',
            sql=f"""
SELECT TRIM(r.ap_req_id) AS AP_REQ_ID, TRIM(r.adj_id) AS ADJ_ID,
       COALESCE(tl.descr, TRIM(a.adj_type_cd)) AS ADJ_TYPE_DESCR, TRIM(sa.acct_id) AS ACCT_ID,
       r.entity_name AS PAYEE, a.adj_amt AS ADJ_AMT, r.paid_amt AS PAID_AMT,
       a.cre_dt AS CRE_DT, r.scheduled_pay_dt AS SCHEDULED_PAY_DT
FROM CISADM.CI_ADJ_APREQ r
JOIN CISADM.CI_ADJ a ON a.adj_id = r.adj_id
LEFT JOIN CISADM.CI_ADJ_TYPE_L tl ON tl.adj_type_cd = a.adj_type_cd AND tl.language_cd = 'ENG'
LEFT JOIN CISADM.CI_SA sa ON sa.sa_id = a.sa_id
WHERE {WINDOW.format(col='a.cre_dt')}
  AND TRIM(r.pymnt_sel_stat_flg) = TRIM($P{{REQ_STATUS}}) AND TRIM(a.adj_status_flg) = TRIM($P{{ADJ_STATUS}})
  /*FILTERS*/
ORDER BY a.cre_dt, r.ap_req_id""",
            header=True,
            # amounts end at x=702 and x=802, under the main grid's Adjustment Amount and Paid Amount
            columns=[Col("AP_REQ_ID", "A/P Request", width=90), Col("ADJ_ID", "Adjustment", width=90),
                     Col("ADJ_TYPE_DESCR", "Adjustment Type", width=100), Col("ACCT_ID", "Account", width=80),
                     Col("PAYEE", "Payee", width=120),
                     Col("CRE_DT", "Created", "java.sql.Timestamp", 50, "Center", "yyyy-MM-dd"),
                     Col("SCHEDULED_PAY_DT", "Scheduled", "java.sql.Timestamp", 48, "Center", "yyyy-MM-dd"),
                     Col("ADJ_AMT", "Adjustment Amount", "java.math.BigDecimal", 100, "Right", MONEY, True),
                     Col("PAID_AMT", "Paid Amount", "java.math.BigDecimal", 100, "Right", MONEY, True)]),
        filters=[
            Filter("REQ_STATUS_F", "A/P request status",
                   "($P{REQ_STATUS_F} IS NULL OR TRIM(r.pymnt_sel_stat_flg) = TRIM($P{REQ_STATUS_F}))",
                   "($P{REQ_STATUS_F} IS NULL OR TRIM(r.pymnt_sel_stat_flg) = TRIM($P{REQ_STATUS_F}))",
                   lov_sql="SELECT TRIM(l.field_value) AS CODE, TRIM(l.field_value) || ' - ' || l.descr AS DESCR FROM CISADM.CI_LOOKUP_VAL_L l WHERE TRIM(l.field_name) = 'PYMNT_SEL_STAT_FLG' AND l.language_cd = 'ENG' AND EXISTS (SELECT 1 FROM CISADM.CI_ADJ_APREQ r JOIN CISADM.CI_ADJ a ON a.adj_id = r.adj_id WHERE TRIM(r.pymnt_sel_stat_flg) = TRIM(l.field_value) AND a.cre_dt >= CURRENT_DATE - INTERVAL '3' YEAR) ORDER BY 1"),
            Filter("ADJ_STATUS_F", "Adjustment status",
                   "($P{ADJ_STATUS_F} IS NULL OR TRIM(a.adj_status_flg) = TRIM($P{ADJ_STATUS_F}))",
                   "($P{ADJ_STATUS_F} IS NULL OR TRIM(a.adj_status_flg) = TRIM($P{ADJ_STATUS_F}))",
                   lov_sql="SELECT TRIM(l.field_value) AS CODE, TRIM(l.field_value) || ' - ' || l.descr AS DESCR FROM CISADM.CI_LOOKUP_VAL_L l WHERE TRIM(l.field_name) = 'ADJ_STATUS_FLG' AND l.language_cd = 'ENG' AND EXISTS (SELECT 1 FROM CISADM.CI_ADJ a JOIN CISADM.CI_ADJ_APREQ r ON r.adj_id = a.adj_id WHERE TRIM(a.adj_status_flg) = TRIM(l.field_value) AND a.cre_dt >= CURRENT_DATE - INTERVAL '3' YEAR) ORDER BY 1"),
            Filter("ACTION_ONLY_F", "Action needed only (type anything for yes)",
                   "($P{ACTION_ONLY_F} IS NULL OR (TRIM(r.pymnt_sel_stat_flg) = 'X' AND TRIM(a.adj_status_flg) IN ('30', '50')) OR (TRIM(r.pymnt_sel_stat_flg) = 'P' AND TRIM(a.adj_status_flg) = '60'))",
                   "($P{ACTION_ONLY_F} IS NULL OR (TRIM(r.pymnt_sel_stat_flg) = 'X' AND TRIM(a.adj_status_flg) IN ('30', '50')) OR (TRIM(r.pymnt_sel_stat_flg) = 'P' AND TRIM(a.adj_status_flg) = '60'))"),
            Filter("ACCT_ID_F", "Account ID",
                   "($P{ACCT_ID_F} IS NULL OR EXISTS (SELECT 1 FROM CISADM.CI_SA fsa WHERE fsa.sa_id = a.sa_id AND TRIM(fsa.acct_id) = TRIM($P{ACCT_ID_F})))",
                   "($P{ACCT_ID_F} IS NULL OR TRIM(sa.acct_id) = TRIM($P{ACCT_ID_F}))"),
        ]),
    Spec(
        name="aged_debt_as_of", label="Aged Debt As Of Date", as_of=True,
        window_label="Position as of",
        description="The arrears position on a chosen day, by service agreement type: SAs with a balance, current balance and the 0-30 / 31-60 / 61-90 / 91-120 / 120+ buckets, with the largest balances (account, customer) under each type. The same arithmetic as CMS_SA_SNAPSHOT, for any date.",
        order_note="frozen arrears FTs as they stood on that day (Age By: ARS = arrears date like the snapshot, DUE = bill due date like the CIS zone; As Known Today = Y counts later cancellations back into history)",
        params={"TOP_N": ("java.lang.Integer", "10"), "AGE_BY": ("java.lang.String", '"ARS"'), "AS_KNOWN_TODAY": ("java.lang.String", '"N"')},
        constants={"N": "the report's own As Known Today switch and the NOT_IN_ARS_SW lifecycle switch, not a client code",
                   "DUE": "the report's own Age By switch value, not a lifecycle code or client code"},
        sql=AGED.format(restrict="") + """SELECT TRIM(sa.cis_division) AS SA_CIS_DIVISION, TRIM(sa.sa_type_cd) AS SA_TYPE_CD, COALESCE(stl.descr, TRIM(sa.sa_type_cd)) AS SA_TYPE_DESCR,
       COUNT(*) AS SA_COUNT, SUM(p.cur_bal) AS CUR_BAL,
       SUM(p.ars_amt1) AS ARS_AMT1, SUM(p.ars_amt2) AS ARS_AMT2, SUM(p.ars_amt3) AS ARS_AMT3, SUM(p.ars_amt4) AS ARS_AMT4, SUM(p.ars_amt5) AS ARS_AMT5
FROM sa_pos p
JOIN CISADM.CI_SA sa ON sa.sa_id = p.sa_id
LEFT JOIN CISADM.CI_SA_TYPE_L stl ON stl.sa_type_cd = sa.sa_type_cd AND stl.cis_division = sa.cis_division AND stl.language_cd = 'ENG'
WHERE p.cur_bal <> 0
GROUP BY TRIM(sa.cis_division), TRIM(sa.sa_type_cd), COALESCE(stl.descr, TRIM(sa.sa_type_cd))
ORDER BY SUM(p.cur_bal) DESC""",
        columns=[Col("SA_CIS_DIVISION", "Div", width=40), Col("SA_TYPE_CD", "SA Type", width=56), Col("SA_TYPE_DESCR", "Service Agreement Type", width=136),
                 Col("SA_COUNT", "SAs", "java.lang.Long", 60, "Right", INT, True), Col("CUR_BAL", "Balance", "java.math.BigDecimal", 90, "Right", MONEY, True),
                 Col("ARS_AMT1", "0-30", "java.math.BigDecimal", 84, "Right", MONEY, True), Col("ARS_AMT2", "31-60", "java.math.BigDecimal", 84, "Right", MONEY, True),
                 Col("ARS_AMT3", "61-90", "java.math.BigDecimal", 84, "Right", MONEY, True), Col("ARS_AMT4", "91-120", "java.math.BigDecimal", 84, "Right", MONEY, True),
                 Col("ARS_AMT5", "120+", "java.math.BigDecimal", 84, "Right", MONEY, True)],
        sub=Sub(
            name="aged_debt_as_of_top", key_param="SA_TYPE_CD", key_field="SA_TYPE_CD", extra_keys={"SA_CIS_DIVISION": "SA_CIS_DIVISION"},
            intro='"Largest balances of SA type " + $P{SA_TYPE_CD}',
            sql="SELECT TRIM(sa.acct_id) AS ACCT_ID, pn.entity_name AS CUSTOMER_NAME, TRIM(x.SA_ID) AS SA_ID, x.CUR_BAL, x.ARS_AMT1, x.ARS_AMT2, x.ARS_AMT3, x.ARS_AMT4, x.ARS_AMT5\nFROM (\n" + AGED.format(restrict="") + """SELECT /*+ RESULT_CACHE */ TRIM(sa.cis_division) AS SA_CIS_DIVISION, TRIM(sa.sa_type_cd) AS SA_TYPE_CD, p.sa_id AS SA_ID, p.cur_bal AS CUR_BAL,
       p.ars_amt1 AS ARS_AMT1, p.ars_amt2 AS ARS_AMT2, p.ars_amt3 AS ARS_AMT3, p.ars_amt4 AS ARS_AMT4, p.ars_amt5 AS ARS_AMT5,
       ROW_NUMBER() OVER (PARTITION BY TRIM(sa.cis_division), TRIM(sa.sa_type_cd) ORDER BY p.cur_bal DESC, p.sa_id) AS RN
FROM sa_pos p
JOIN CISADM.CI_SA sa ON sa.sa_id = p.sa_id
WHERE p.cur_bal <> 0
) x
JOIN CISADM.CI_SA sa ON sa.sa_id = x.SA_ID
LEFT JOIN CISADM.CI_ACCT_PER ap ON ap.acct_id = sa.acct_id AND TRIM(ap.main_cust_sw) = 'Y'
LEFT JOIN CISADM.CI_PER_NAME pn ON pn.per_id = ap.per_id AND TRIM(pn.name_type_flg) = 'PRIM'
WHERE x.SA_CIS_DIVISION = TRIM($P{SA_CIS_DIVISION}) AND x.SA_TYPE_CD = TRIM($P{SA_TYPE_CD}) AND x.RN <= $P{TOP_N}
ORDER BY x.RN""",
            columns=[Col("ACCT_ID", "Account", width=72), Col("CUSTOMER_NAME", "Customer", width=136), Col("SA_ID", "SA", width=60),
                     Col("CUR_BAL", "Balance", "java.math.BigDecimal", 90, "Right", MONEY, True),
                     Col("ARS_AMT1", "0-30", "java.math.BigDecimal", 84, "Right", MONEY, True), Col("ARS_AMT2", "31-60", "java.math.BigDecimal", 84, "Right", MONEY, True),
                     Col("ARS_AMT3", "61-90", "java.math.BigDecimal", 84, "Right", MONEY, True), Col("ARS_AMT4", "91-120", "java.math.BigDecimal", 84, "Right", MONEY, True),
                     Col("ARS_AMT5", "120+", "java.math.BigDecimal", 84, "Right", MONEY, True)]),
        filters=[
            Filter("CUST_CL_F", "Customer class",
                   "($P{CUST_CL_F} IS NULL OR EXISTS (SELECT 1 FROM CISADM.CI_SA fsa JOIN CISADM.CI_ACCT fa ON fa.acct_id = fsa.acct_id WHERE fsa.sa_id = ft.sa_id AND TRIM(fa.cust_cl_cd) = TRIM($P{CUST_CL_F})))", "($P{CUST_CL_F} IS NULL OR EXISTS (SELECT 1 FROM CISADM.CI_SA fsa JOIN CISADM.CI_ACCT fa ON fa.acct_id = fsa.acct_id WHERE fsa.sa_id = ft.sa_id AND TRIM(fa.cust_cl_cd) = TRIM($P{CUST_CL_F})))",
                   lov_sql="SELECT TRIM(cust_cl_cd) AS CODE, TRIM(cust_cl_cd) || ' - ' || descr AS DESCR FROM CISADM.CI_CUST_CL_L l WHERE l.language_cd = 'ENG' AND EXISTS (SELECT 1 FROM CISADM.CI_ACCT a JOIN CISADM.CI_SA sa ON sa.acct_id = a.acct_id WHERE a.cust_cl_cd = l.cust_cl_cd AND (sa.end_dt IS NULL OR sa.end_dt >= CURRENT_DATE - INTERVAL '3' YEAR)) ORDER BY 1"),
            Filter("CIS_DIVISION_F", "CIS division",
                   "($P{CIS_DIVISION_F} IS NULL OR EXISTS (SELECT 1 FROM CISADM.CI_SA fsa WHERE fsa.sa_id = ft.sa_id AND TRIM(fsa.cis_division) = TRIM($P{CIS_DIVISION_F})))", "($P{CIS_DIVISION_F} IS NULL OR EXISTS (SELECT 1 FROM CISADM.CI_SA fsa WHERE fsa.sa_id = ft.sa_id AND TRIM(fsa.cis_division) = TRIM($P{CIS_DIVISION_F})))",
                   lov_sql="SELECT TRIM(cis_division) AS CODE, TRIM(cis_division) || ' - ' || descr AS DESCR FROM CISADM.CI_CIS_DIVISION_L l WHERE l.language_cd = 'ENG' AND EXISTS (SELECT 1 FROM CISADM.CI_SA sa WHERE sa.cis_division = l.cis_division AND (sa.end_dt IS NULL OR sa.end_dt >= CURRENT_DATE - INTERVAL '3' YEAR)) ORDER BY 1"),
            Filter("ACCT_ID_F", "Account ID",
                   "($P{ACCT_ID_F} IS NULL OR EXISTS (SELECT 1 FROM CISADM.CI_SA fsa WHERE fsa.sa_id = ft.sa_id AND TRIM(fsa.acct_id) = TRIM($P{ACCT_ID_F})))", "($P{ACCT_ID_F} IS NULL OR EXISTS (SELECT 1 FROM CISADM.CI_SA fsa WHERE fsa.sa_id = ft.sa_id AND TRIM(fsa.acct_id) = TRIM($P{ACCT_ID_F})))"),
        ]),

    # College Station, 2026-10-01: "the top 10 users of water, the top 20 of electric, for the year".
    # BILLED usage, not meter reads: what the customer was billed for, after VEE and estimation,
    # with rebills replacing cancels (frozen segments of completed bills), on every client whether
    # read by AMI or by hand. One unit at a time -- usage adds only within a unit -- chosen by the
    # reader or, left blank, the service's most-billed unit that is not a peak (demand) unit.
    # Measured on College Station TEST, 2025: every CI_BSEG_SQ row carries a padded blank SQI (so
    # TRIM, never IS NULL alone); KW (559,454 rows) out-counts KWH (559,331), so the peak flag is
    # what keeps a demand total out; Ellensburg leaves KW unflagged but bills it on 2% of segments.
    # Top 10 water accounts tied to the client's BSEG_SQ_USAGE_RPT_CURR exactly (usage and segments).
    # Residential sewer at College Station is priced in gallons under the code commercial sewer
    # prices in thousands (MGW): rank sewer within one SA type there, or rank water.
    Spec(
        name="top_usage_customers", label="Top Usage Customers",
        window_label="Service period end date", year=True,
        description="The N accounts that used the most of a service in a window, by billed usage: frozen segments of completed bills, one unit of measure at a time, with each account's month-by-month usage and billed amount underneath.",
        order_note="billed usage on frozen segments of completed bills",
        params={"TOP_N": ("java.lang.Integer", "10")},
        sql="""
WITH seg AS (
  SELECT b.bseg_id, b.end_dt, s.sa_id, s.acct_id, s.char_prem_id
  FROM CISADM.CI_BSEG b
  JOIN CISADM.CI_BILL bl ON bl.bill_id = b.bill_id
  JOIN CISADM.CI_SA s ON s.sa_id = b.sa_id
  JOIN CISADM.CI_SA_TYPE t ON t.sa_type_cd = s.sa_type_cd AND t.cis_division = s.cis_division
  WHERE TRIM(b.bseg_stat_flg) = '50' AND TRIM(bl.bill_stat_flg) = 'C'
    AND b.end_dt >= $P{FROM_DT} AND b.end_dt < $P{TO_DT} + INTERVAL '1' DAY
    /*FILTERS*/
),
qty AS (
  SELECT g.acct_id, g.sa_id, g.bseg_id, TRIM(q.uom_cd) AS uom_cd, q.bill_sq
  FROM seg g
  JOIN CISADM.CI_BSEG_SQ q ON q.bseg_id = g.bseg_id
  LEFT JOIN CISADM.CI_UOM u ON u.uom_cd = q.uom_cd
  WHERE TRIM(q.sqi_cd) IS NULL AND TRIM(q.uom_cd) IS NOT NULL
    AND COALESCE(TRIM(u.msr_peak_qty_sw), 'N') <> 'Y'
),
units AS (
  SELECT uom_cd, ROW_NUMBER() OVER (ORDER BY COUNT(*) DESC, uom_cd) AS rn FROM qty GROUP BY uom_cd
),
chosen AS (
  SELECT uom_cd FROM units
  WHERE CASE WHEN $X{IN, '#', UOM_CODES_F} THEN CASE WHEN rn = 1 THEN 1 ELSE 0 END
             WHEN $X{IN, uom_cd, UOM_CODES_F} THEN 1 ELSE 0 END = 1
),
by_acct AS (
  SELECT q.acct_id, SUM(q.bill_sq) AS usage_qty, COUNT(DISTINCT q.bseg_id) AS bills
  FROM qty q JOIN chosen c ON c.uom_cd = q.uom_cd
  GROUP BY q.acct_id
),
ranked AS (
  SELECT acct_id, usage_qty, bills,
         usage_qty * 100 / NULLIF(SUM(usage_qty) OVER (), 0) AS share_pct,
         ROW_NUMBER() OVER (ORDER BY usage_qty DESC, acct_id) AS rank_no
  FROM by_acct
),
top_acct AS (SELECT acct_id, usage_qty, bills, share_pct, rank_no FROM ranked WHERE rank_no <= $P{TOP_N}),
top_sa AS (
  SELECT q.acct_id, q.sa_id, ROW_NUMBER() OVER (PARTITION BY q.acct_id ORDER BY SUM(q.bill_sq) DESC, q.sa_id) AS rn
  FROM qty q JOIN chosen c ON c.uom_cd = q.uom_cd JOIN top_acct ta ON ta.acct_id = q.acct_id
  GROUP BY q.acct_id, q.sa_id
),
prem AS (
  SELECT g.acct_id, COUNT(DISTINCT g.char_prem_id) AS premises
  FROM seg g JOIN top_acct ta ON ta.acct_id = g.acct_id GROUP BY g.acct_id
),
billed AS (
  SELECT g.acct_id, SUM(c.calc_amt) AS billed_amt
  FROM seg g JOIN top_acct ta ON ta.acct_id = g.acct_id
  JOIN CISADM.CI_BSEG_CALC c ON c.bseg_id = g.bseg_id
  GROUP BY g.acct_id
),
unit_list AS (SELECT LISTAGG(uom_cd, ', ') WITHIN GROUP (ORDER BY uom_cd) AS uoms FROM chosen)
SELECT ta.rank_no AS RANK_NO, TRIM(ta.acct_id) AS ACCT_ID, pn.entity_name AS CUSTOMER_NAME,
       TRIM(p.address1) || CASE WHEN TRIM(p.city) IS NOT NULL THEN ', ' || TRIM(p.city) END
         || CASE WHEN pr.premises > 1 THEN ' (+' || (pr.premises - 1) || ' more)' END AS SERVICE_ADDRESS,
       COALESCE(cl.descr, TRIM(a.cust_cl_cd)) AS CUSTOMER_CLASS,
       ta.bills AS BILLS, ta.usage_qty AS USAGE_QTY, ul.uoms AS UOM, ta.share_pct AS SHARE_PCT,
       COALESCE(bd.billed_amt, 0) AS BILLED_AMT
FROM top_acct ta
CROSS JOIN unit_list ul
JOIN CISADM.CI_ACCT a ON a.acct_id = ta.acct_id
LEFT JOIN CISADM.CI_CUST_CL_L cl ON cl.cust_cl_cd = a.cust_cl_cd AND cl.language_cd = 'ENG'
LEFT JOIN CISADM.CI_ACCT_PER ap ON ap.acct_id = ta.acct_id AND TRIM(ap.main_cust_sw) = 'Y'
LEFT JOIN CISADM.CI_PER_NAME pn ON pn.per_id = ap.per_id AND TRIM(pn.name_type_flg) = 'PRIM'
LEFT JOIN top_sa ts ON ts.acct_id = ta.acct_id AND ts.rn = 1
LEFT JOIN CISADM.CI_SA sa ON sa.sa_id = ts.sa_id
LEFT JOIN CISADM.CI_PREM p ON p.prem_id = sa.char_prem_id
LEFT JOIN prem pr ON pr.acct_id = ta.acct_id
LEFT JOIN billed bd ON bd.acct_id = ta.acct_id
ORDER BY ta.rank_no""",
        columns=[Col("RANK_NO", "Rank", "java.lang.Long", 30, "Center", INT), Col("ACCT_ID", "Account", width=80),
                 Col("CUSTOMER_NAME", "Main Customer", width=150), Col("SERVICE_ADDRESS", "Service Address", width=150),
                 Col("CUSTOMER_CLASS", "Class", width=60), Col("BILLS", "Bills", "java.lang.Long", 50, "Right", INT, True),
                 Col("USAGE_QTY", "Billed Usage", "java.math.BigDecimal", 90, "Right", "#,##0.##", True), Col("UOM", "Unit", width=50),
                 Col("SHARE_PCT", "Share %", "java.math.BigDecimal", 50, "Right", "0.00", True),
                 Col("BILLED_AMT", "Billed Amount", "java.math.BigDecimal", 92, "Right", MONEY, True)],
        sub=Sub(
            name="top_usage_customers_month", key_param="ACCT_ID", key_field="ACCT_ID",
            extra_keys={"UNITS": "UOM"},
            intro='"By month for account " + $P{ACCT_ID}',
            sql="""
SELECT TO_CHAR(x.end_dt, 'YYYY-MM') AS USAGE_MONTH, COUNT(x.usage_qty) AS BILLS,
       SUM(x.usage_qty) AS USAGE_QTY, COALESCE(SUM(x.billed_amt), 0) AS BILLED_AMT
FROM (
  SELECT b.bseg_id, b.end_dt,
         (SELECT SUM(q.bill_sq) FROM CISADM.CI_BSEG_SQ q
          WHERE q.bseg_id = b.bseg_id AND TRIM(q.sqi_cd) IS NULL
            AND INSTR(', ' || $P{UNITS} || ',', ', ' || TRIM(q.uom_cd) || ',') > 0
            AND $X{IN, TRIM(q.uom_cd), UOM_CODES_F}) AS usage_qty,
         (SELECT SUM(c.calc_amt) FROM CISADM.CI_BSEG_CALC c WHERE c.bseg_id = b.bseg_id) AS billed_amt
  FROM CISADM.CI_SA s
  JOIN CISADM.CI_SA_TYPE t ON t.sa_type_cd = s.sa_type_cd AND t.cis_division = s.cis_division
  JOIN CISADM.CI_BSEG b ON b.sa_id = s.sa_id
  JOIN CISADM.CI_BILL bl ON bl.bill_id = b.bill_id
  WHERE s.acct_id = $P{ACCT_ID}
    AND TRIM(b.bseg_stat_flg) = '50' AND TRIM(bl.bill_stat_flg) = 'C'
    AND b.end_dt >= $P{FROM_DT} AND b.end_dt < $P{TO_DT} + INTERVAL '1' DAY
    /*FILTERS*/
) x
GROUP BY TO_CHAR(x.end_dt, 'YYYY-MM')
ORDER BY 1""",
            columns=[Col(None, "", width=86), Col("USAGE_MONTH", "Month", width=150), Col(None, "", width=150), Col(None, "", width=60),
                     Col("BILLS", "Bills", "java.lang.Long", 50, "Right", INT, True),
                     Col("USAGE_QTY", "Billed Usage", "java.math.BigDecimal", 90, "Right", "#,##0.##", True),
                     Col(None, "", width=50), Col(None, "", width=50),
                     Col("BILLED_AMT", "Billed Amount", "java.math.BigDecimal", 92, "Right", MONEY, True)]),
        filters=[
            Filter("SVC_TYPE_CD_F", "Service type",
                   "TRIM(t.svc_type_cd) = TRIM($P{SVC_TYPE_CD_F})", "TRIM(t.svc_type_cd) = TRIM($P{SVC_TYPE_CD_F})", required=True,
                   lov_sql="SELECT TRIM(l.svc_type_cd) AS CODE, TRIM(l.svc_type_cd) || ' - ' || l.descr AS DESCR FROM CISADM.CI_SVC_TYPE_L l WHERE l.language_cd = 'ENG' AND EXISTS (SELECT 1 FROM CISADM.CI_UOM u WHERE u.svc_type_cd = l.svc_type_cd) AND EXISTS (SELECT 1 FROM CISADM.CI_SA_TYPE t JOIN CISADM.CI_SA sa ON sa.sa_type_cd = t.sa_type_cd AND sa.cis_division = t.cis_division WHERE t.svc_type_cd = l.svc_type_cd AND (sa.end_dt IS NULL OR sa.end_dt >= CURRENT_DATE - INTERVAL '3' YEAR)) ORDER BY 1"),
            # applied in the query's own chosen-unit step, so it adds no predicate here
            Filter("UOM_CODES_F", "Units of measure", "", "", multi=True,
                   lov_sql="SELECT TRIM(u.uom_cd) AS CODE, TRIM(u.uom_cd) || ' - ' || l.descr AS DESCR FROM CISADM.CI_UOM u JOIN CISADM.CI_UOM_L l ON l.uom_cd = u.uom_cd AND l.language_cd = 'ENG' WHERE TRIM(u.svc_type_cd) = TRIM($P{SVC_TYPE_CD_F}) AND COALESCE(TRIM(u.msr_peak_qty_sw), 'N') <> 'Y' ORDER BY 1"),
            Filter("SA_TYPE_CD_F", "SA types",
                   "$X{IN, TRIM(s.sa_type_cd), SA_TYPE_CD_F}", "$X{IN, TRIM(s.sa_type_cd), SA_TYPE_CD_F}", multi=True,
                   lov_sql="SELECT DISTINCT TRIM(t.sa_type_cd) AS CODE, TRIM(t.sa_type_cd) || ' - ' || l.descr AS DESCR FROM CISADM.CI_SA_TYPE t JOIN CISADM.CI_SA_TYPE_L l ON l.cis_division = t.cis_division AND l.sa_type_cd = t.sa_type_cd AND l.language_cd = 'ENG' WHERE TRIM(t.svc_type_cd) = TRIM($P{SVC_TYPE_CD_F}) AND EXISTS (SELECT 1 FROM CISADM.CI_SA sa WHERE sa.sa_type_cd = t.sa_type_cd AND sa.cis_division = t.cis_division AND (sa.end_dt IS NULL OR sa.end_dt >= CURRENT_DATE - INTERVAL '3' YEAR)) ORDER BY 1"),
            Filter("CUST_CL_F", "Customer class",
                   "($P{CUST_CL_F} IS NULL OR EXISTS (SELECT 1 FROM CISADM.CI_ACCT fa WHERE fa.acct_id = s.acct_id AND TRIM(fa.cust_cl_cd) = TRIM($P{CUST_CL_F})))",
                   "($P{CUST_CL_F} IS NULL OR EXISTS (SELECT 1 FROM CISADM.CI_ACCT fa WHERE fa.acct_id = s.acct_id AND TRIM(fa.cust_cl_cd) = TRIM($P{CUST_CL_F})))",
                   lov_sql="SELECT TRIM(cust_cl_cd) AS CODE, TRIM(cust_cl_cd) || ' - ' || descr AS DESCR FROM CISADM.CI_CUST_CL_L l WHERE l.language_cd = 'ENG' AND EXISTS (SELECT 1 FROM CISADM.CI_ACCT a JOIN CISADM.CI_SA sa ON sa.acct_id = a.acct_id WHERE a.cust_cl_cd = l.cust_cl_cd AND (sa.end_dt IS NULL OR sa.end_dt >= CURRENT_DATE - INTERVAL '3' YEAR)) ORDER BY 1"),
            Filter("CIS_DIVISION_F", "CIS division",
                   "($P{CIS_DIVISION_F} IS NULL OR TRIM(s.cis_division) = TRIM($P{CIS_DIVISION_F}))",
                   "($P{CIS_DIVISION_F} IS NULL OR TRIM(s.cis_division) = TRIM($P{CIS_DIVISION_F}))",
                   lov_sql="SELECT TRIM(cis_division) AS CODE, TRIM(cis_division) || ' - ' || descr AS DESCR FROM CISADM.CI_CIS_DIVISION_L l WHERE l.language_cd = 'ENG' AND EXISTS (SELECT 1 FROM CISADM.CI_SA sa WHERE sa.cis_division = l.cis_division AND (sa.end_dt IS NULL OR sa.end_dt >= CURRENT_DATE - INTERVAL '3' YEAR)) ORDER BY 1"),
        ]),
]


def write_all() -> list[Path]:
    SUBS.mkdir(parents=True, exist_ok=True)
    CONTROLS.mkdir(parents=True, exist_ok=True)
    out = []
    for s in SPECS:
        assert sum(c.width for c in s.columns) == COL_W, (s.name, sum(c.width for c in s.columns))
        assert sum(c.width for c in s.sub.columns) == COL_W - 24, (s.sub.name, sum(c.width for c in s.sub.columns))
        m, sub = REPORTS / f"{s.name}.jrxml", SUBS / f"{s.sub.name}.jrxml"
        m.write_text(main_jrxml(s), encoding="utf-8"); sub.write_text(sub_jrxml(s), encoding="utf-8")
        doc, rest = controls(s)
        (CONTROLS / f"{s.name}_input_controls.json").write_text(json.dumps(doc, indent=2) + "\n")
        (CONTROLS / f"{s.name}_input_controls_rest.json").write_text(json.dumps(rest, indent=2) + "\n")
        out += [m, sub]
    return out


if __name__ == "__main__":
    for p in write_all():
        print("wrote", p.relative_to(REPO))
