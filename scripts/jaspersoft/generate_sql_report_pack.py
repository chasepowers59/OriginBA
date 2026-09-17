#!/usr/bin/env python3
"""Generate the SmartCity finance report pack: SQL JRXML main reports with a subreport each,
runnable at ANY client because the SQL names only base-product tables, lifecycle constants
and label tables -- never a client-configured code.

    python3 scripts/jaspersoft/generate_sql_report_pack.py          # writes reports/ + server/input_controls/

Why generated: eight JRXML files share one style block, one page geometry, one parameter set
and one band layout; hand-editing them drifts. Each report is a SPEC below (query, columns,
subreport); the emitter owns the JRXML 6 model (JRS 8.1 / 9.0 -- see the report-builder
skill for the 6-vs-7 rule). Proofs: tests/test_sql_report_pack.py (structure, validator, the
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
import uuid
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

STYLES = """    <style name="Base" isDefault="true" fontName="Aptos" fontSize="9"/>
    <style name="TitleSapphire" style="Base" fontSize="18" isBold="true" forecolor="#006FAC"/>
    <style name="H3" style="Base" fontSize="10" forecolor="#0F4761"/>
    <style name="HeaderSapphire" style="Base" fontSize="9" isBold="true" forecolor="#FFFFFF" backcolor="#006FAC" mode="Opaque"/>
    <style name="DetailText" style="Base" fontSize="9" forecolor="#000000" backcolor="#F5F0EB" mode="Opaque"/>
    <style name="SubHeader" style="Base" fontSize="8" isBold="true" forecolor="#1348AB"/>
    <style name="SubText" style="Base" fontSize="8" forecolor="#000000"/>
    <style name="TotalText" style="Base" fontSize="9" isBold="true" forecolor="#000000" backcolor="#F5F0EB" mode="Opaque"/>
    <style name="FooterConfidential" style="Base" fontSize="7" forecolor="#000000"/>
"""
FOOTER = '"@2026, Origin Utility, Inc / Proprietary & Confidential / Expressly for " + $P{CLIENT_NAME}'


@dataclass
class Col:
    name: str
    label: str
    cls: str = "java.lang.String"
    width: int = 80
    align: str = "Left"
    pattern: str | None = None
    total: bool = False       # Sum variable + summary cell


@dataclass
class Sub:
    name: str
    key_param: str            # parameter the main passes (the row's key)
    key_field: str            # main-report field holding the key
    sql: str
    columns: list[Col]
    intro: str                # text above the subreport table, may use $P{...}


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

    def all_params(self) -> dict:
        return {**self.params, **{f.param: (f.cls, "null") for f in self.filters}}

    def main_sql(self) -> str:
        return _with_filters(self.sql, [f.main_pred for f in self.filters])

    def sub_sql(self) -> str:
        return _with_filters(self.sub.sql, [f.sub_pred for f in self.filters])


def _with_filters(sql: str, preds: list[str]) -> str:
    """Append the optional predicates to the query's (first) WHERE clause -- before GROUP BY /
    ORDER BY. Queries here have one WHERE at their driving level; the TOP-N subquery is the
    exception and is handled by placing the marker comment where the filters belong."""
    if not preds:
        return sql
    extra = "".join(f"\n  AND {p}" for p in preds)
    if "/*FILTERS*/" in sql:
        return sql.replace("/*FILTERS*/", extra.lstrip("\n"))
    for kw in ("\nGROUP BY", "\nORDER BY"):
        i = sql.find(kw)
        if i >= 0:
            return sql[:i] + extra + sql[i:]
    return sql + extra


def _uid(seed: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "originba/" + seed))


def _xml_esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _params(extra: dict[str, tuple[str, str]]) -> str:
    base = {
        "FROM_DT": ("java.sql.Date", 'java.sql.Date.valueOf(java.time.LocalDate.now().withDayOfMonth(1).minusMonths(1).toString())'),
        "TO_DT": ("java.sql.Date", 'java.sql.Date.valueOf(java.time.LocalDate.now().withDayOfMonth(1).minusDays(1).toString())'),
        "CLIENT_NAME": ("java.lang.String", '"SmartCity Client"'),
    }
    base.update(extra)
    out = []
    for n, (cls, default) in base.items():
        out.append(f'    <parameter name="{n}" class="{cls}">\n        <defaultValueExpression><![CDATA[{default}]]></defaultValueExpression>\n    </parameter>')
    return "\n".join(out)


def _fields(cols: list[Col]) -> str:
    return "\n".join(f'    <field name="{c.name}" class="{c.cls}"/>' for c in cols)


def _variables(cols: list[Col]) -> str:
    return "\n".join(
        f'    <variable name="SUM_{c.name}" class="{c.cls}" calculation="Sum">\n'
        f'        <variableExpression><![CDATA[$F{{{c.name}}}]]></variableExpression>\n    </variable>'
        for c in cols if c.total)


def _text(x: int, y: int, w: int, h: int, expr: str, style: str, align: str, seed: str,
          pattern: str | None = None, mode: str | None = None, blank_null: bool = True) -> str:
    pat = f' pattern="{pattern}"' if pattern else ""
    bn = ' isBlankWhenNull="true"' if blank_null else ""
    m = f' mode="{mode}"' if mode else ""
    return (f'            <textField{pat}{bn} textAdjust="StretchHeight">\n'
            f'                <reportElement style="{style}" x="{x}" y="{y}" width="{w}" height="{h}"{m} uuid="{_uid(seed)}"/>\n'
            f'                <textElement textAlignment="{align}" verticalAlignment="Middle"><paragraph leftIndent="2" rightIndent="2"/></textElement>\n'
            f'                <textFieldExpression><![CDATA[{expr}]]></textFieldExpression>\n            </textField>')


def _static(x: int, y: int, w: int, h: int, text: str, style: str, align: str, seed: str) -> str:
    return (f'            <staticText>\n'
            f'                <reportElement style="{style}" x="{x}" y="{y}" width="{w}" height="{h}" uuid="{_uid(seed)}"/>\n'
            f'                <textElement textAlignment="{align}" verticalAlignment="Middle"><paragraph leftIndent="2" rightIndent="2"/></textElement>\n'
            f'                <text><![CDATA[{_xml_esc(text)}]]></text>\n            </staticText>')


def _header_row(cols: list[Col], style: str, seed: str, h: int = HDR_H) -> str:
    x, out = 0, []
    for c in cols:
        out.append(_static(x, 0, c.width, h, c.label, style, "Center" if style == "HeaderSapphire" else c.align, f"{seed}/h/{c.name}"))
        x += c.width
    return "\n".join(out)


def _detail_row(cols: list[Col], style: str, seed: str, h: int = ROW_H) -> str:
    x, out = 0, []
    for c in cols:
        out.append(_text(x, 0, c.width, h, f"$F{{{c.name}}}", style, c.align, f"{seed}/d/{c.name}", c.pattern))
        x += c.width
    return "\n".join(out)


def _total_row(cols: list[Col], style: str, seed: str, label: str, h: int = ROW_H) -> str:
    x, out = 0, []
    first = True
    for c in cols:
        if c.total:
            out.append(_text(x, 0, c.width, h, f"$V{{SUM_{c.name}}}", style, c.align, f"{seed}/t/{c.name}", c.pattern))
        elif first:
            out.append(_static(x, 0, c.width, h, label, style, "Left", f"{seed}/t/label"))
            first = False
        else:
            out.append(_static(x, 0, c.width, h, "", style, "Left", f"{seed}/t/{c.name}"))
        x += c.width
    return "\n".join(out)


def _head(name: str, page_w: int, page_h: int, margin: int, col_w: int, orientation: str = "Landscape") -> str:
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<jasperReport xmlns="http://jasperreports.sourceforge.net/jasperreports"\n'
            f'    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
            f'    xsi:schemaLocation="http://jasperreports.sourceforge.net/jasperreports http://jasperreports.sourceforge.net/xsd/jasperreport.xsd"\n'
            f'    name="{name}" pageWidth="{page_w}" pageHeight="{page_h}" orientation="{orientation}"\n'
            f'    columnWidth="{col_w}" leftMargin="{margin}" rightMargin="{margin}" topMargin="{margin}" bottomMargin="{margin}"\n'
            f'    whenNoDataType="AllSectionsNoDetail" uuid="{_uid(name)}">\n'
            f'    <property name="net.sf.jasperreports.query.timeout" value="600"/>\n'
            f'    <property name="net.sf.jasperreports.export.xls.remove.empty.space.between.rows" value="true"/>\n')


def main_jrxml(s: Spec) -> str:
    sub_params = "\n".join(
        f'                <subreportParameter name="{p}">\n'
        f'                    <subreportParameterExpression><![CDATA[$P{{{p}}}]]></subreportParameterExpression>\n'
        f'                </subreportParameter>' for p in ("FROM_DT", "TO_DT", *s.all_params()))
    sub_key = (f'                <subreportParameter name="{s.sub.key_param}">\n'
               f'                    <subreportParameterExpression><![CDATA[$F{{{s.sub.key_field}}}]]></subreportParameterExpression>\n'
               f'                </subreportParameter>')
    window = ('$P{CLIENT_NAME} + "  |  " + new java.text.SimpleDateFormat("yyyy-MM-dd").format($P{FROM_DT}) '
              '+ " to " + new java.text.SimpleDateFormat("yyyy-MM-dd").format($P{TO_DT})'
              + (f' + "  |  {s.order_note}"' if s.order_note else "")
              + "".join(f' + ($P{{{f.param}}} == null ? "" : "  |  {f.label}: " + $P{{{f.param}}})' for f in s.filters))
    return (_head(s.name, PAGE_W, PAGE_H, MARGIN, COL_W) + STYLES + _params(s.all_params()) + "\n"
            f'    <queryString language="SQL"><![CDATA[\n{s.main_sql().strip()}\n]]></queryString>\n'
            + _fields(s.columns) + "\n" + _variables(s.columns) + "\n"
            f'    <title>\n        <band height="52">\n'
            + _text(0, 0, COL_W, 26, f'"{s.label}"', "TitleSapphire", "Left", s.name + "/title") + "\n"
            + _text(0, 28, COL_W, 16, window, "H3", "Left", s.name + "/window") + "\n"
            + _text(0, 44, COL_W, 8, '""', "Base", "Left", s.name + "/gap") + "\n"
            f'        </band>\n    </title>\n'
            f'    <columnHeader>\n        <band height="{HDR_H}">\n' + _header_row(s.columns, "HeaderSapphire", s.name) + "\n"
            f'        </band>\n    </columnHeader>\n'
            f'    <detail>\n        <band height="{ROW_H + 4}" splitType="Prevent">\n' + _detail_row(s.columns, "DetailText", s.name) + "\n"
            f'        </band>\n        <band height="20" splitType="Stretch">\n'
            f'            <subreport isUsingCache="false">\n'
            f'                <reportElement positionType="Float" stretchType="RelativeToBandHeight" isRemoveLineWhenBlank="true" x="24" y="0" width="{COL_W - 24}" height="20" uuid="{_uid(s.name + "/sub")}"/>\n'
            + sub_params + "\n" + sub_key + "\n"
            f'                <connectionExpression><![CDATA[$P{{REPORT_CONNECTION}}]]></connectionExpression>\n'
            f'                <subreportExpression><![CDATA["repo:{s.sub.name}"]]></subreportExpression>\n'
            f'            </subreport>\n        </band>\n    </detail>\n'
            f'    <pageFooter>\n        <band height="14">\n'
            + _text(0, 0, 600, 14, FOOTER, "FooterConfidential", "Left", s.name + "/foot") + "\n"
            + _text(600, 0, 202, 14, '"Page " + $V{PAGE_NUMBER} + " of " + $V{PAGE_NUMBER}', "FooterConfidential", "Right", s.name + "/page").replace(
                '<textField isBlankWhenNull="true" textAdjust="StretchHeight">', '<textField isBlankWhenNull="true" textAdjust="StretchHeight" evaluationTime="Report">', 1) + "\n"
            f'        </band>\n    </pageFooter>\n'
            f'    <summary>\n        <band height="{ROW_H + 6}">\n' + _total_row(s.columns, "TotalText", s.name, "Total") + "\n"
            f'        </band>\n    </summary>\n</jasperReport>\n')


def sub_jrxml(s: Spec) -> str:
    sub, w = s.sub, COL_W - 24
    return (_head(sub.name, w, PAGE_H, 0, w) + STYLES
            + _params({sub.key_param: ("java.lang.String", '""'), **s.all_params()}).replace('<parameter name="CLIENT_NAME"', '<parameter name="CLIENT_NAME" isForPrompting="false"') + "\n"
            f'    <queryString language="SQL"><![CDATA[\n{s.sub_sql().strip()}\n]]></queryString>\n'
            + _fields(sub.columns) + "\n" + _variables(sub.columns) + "\n"
            f'    <title>\n        <band height="14">\n' + _text(0, 0, w, 14, sub.intro, "SubHeader", "Left", sub.name + "/intro") + "\n"
            f'        </band>\n    </title>\n'
            f'    <columnHeader>\n        <band height="14">\n' + _header_row(sub.columns, "SubHeader", sub.name, 14) + "\n"
            f'        </band>\n    </columnHeader>\n'
            f'    <detail>\n        <band height="13">\n' + _detail_row(sub.columns, "SubText", sub.name, 13) + "\n"
            f'        </band>\n    </detail>\n'
            f'    <summary>\n        <band height="16">\n' + _total_row(sub.columns, "SubHeader", sub.name, "Subtotal", 13) + "\n"
            f'        </band>\n    </summary>\n</jasperReport>\n')


def controls(s: Spec) -> tuple[dict, list]:
    ics = [
        {"id": "FROM_DT", "label": "From date (inclusive)", "type": "singleValueDate", "mandatory": True, "visible": True},
        {"id": "TO_DT", "label": "To date (inclusive)", "type": "singleValueDate", "mandatory": True, "visible": True},
        {"id": "CLIENT_NAME", "label": "Client name (footer)", "type": "singleValueText", "mandatory": False, "visible": True, "defaultValue": "SmartCity Client"},
    ]
    for n, (cls, default) in s.params.items():
        ics.append({"id": n, "label": n.replace("_", " ").title(), "type": "singleValueNumber" if "Integer" in cls else "singleValueText",
                    "mandatory": False, "visible": True, "defaultValue": default.strip('"')})
    for f in s.filters:
        ics.append({"id": f.param, "label": f"{f.label} (blank = all)", "type": f.control, "mandatory": False, "visible": True})
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
FOLDERS = {
    "billing_by_cycle_period": "/SmartCity/Report/Standard_Offering/Billing_and_Rates",
    "payments_by_tender_type_period": "/SmartCity/Report/Standard_Offering/Cashiering",
    "adjustments_by_type_period": "/SmartCity/Report/Standard_Offering/Finance",
    "gl_by_distribution_code_period": "/SmartCity/Report/Standard_Offering/Finance",
}

# ------------------------------------------------------------------ the specs
WINDOW = "{col} >= $P{{FROM_DT}} AND {col} < $P{{TO_DT}} + INTERVAL '1' DAY"

SPECS: list[Spec] = [
    Spec(
        name="billing_by_cycle_period", label="Billing by Cycle",
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
SELECT TRIM(t.svc_type_cd) AS SVC_TYPE_CD, COALESCE(sl.descr, TRIM(t.svc_type_cd)) AS SVC_TYPE_DESCR,
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
  AND COALESCE(NULLIF(TRIM(b.bill_cyc_cd), ''), '(none)') = $P{{BILL_CYC_CD}}
GROUP BY TRIM(t.svc_type_cd), COALESCE(sl.descr, TRIM(t.svc_type_cd))
ORDER BY BILLED_AMT DESC""",
            columns=[Col("SVC_TYPE_CD", "Type", width=60), Col("SVC_TYPE_DESCR", "Service Type", width=328),
                     Col("SERVICE_AGREEMENTS", "SAs", "java.lang.Long", 90, "Right", INT, True), Col("SEGMENTS", "Segments", "java.lang.Long", 90, "Right", INT, True),
                     Col("ESTIMATED_SEGMENTS", "Estimated", "java.lang.Long", 90, "Right", INT, True),
                     Col("BILLED_AMT", "Billed Amount", "java.math.BigDecimal", 120, "Right", MONEY, True)]),
        filters=[
            Filter("BILL_CYC_CD_F", "Bill cycle",
                   "($P{BILL_CYC_CD_F} IS NULL OR TRIM(b.bill_cyc_cd) = TRIM($P{BILL_CYC_CD_F}))",
                   "($P{BILL_CYC_CD_F} IS NULL OR TRIM(b.bill_cyc_cd) = TRIM($P{BILL_CYC_CD_F}))"),
            Filter("SVC_TYPE_CD_F", "Service type",
                   "($P{SVC_TYPE_CD_F} IS NULL OR EXISTS (SELECT 1 FROM CISADM.CI_SA fsa JOIN CISADM.CI_SA_TYPE ft ON ft.sa_type_cd = fsa.sa_type_cd AND ft.cis_division = fsa.cis_division WHERE fsa.sa_id = s.sa_id AND TRIM(ft.svc_type_cd) = TRIM($P{SVC_TYPE_CD_F})))",
                   "($P{SVC_TYPE_CD_F} IS NULL OR TRIM(t.svc_type_cd) = TRIM($P{SVC_TYPE_CD_F}))"),
            Filter("CIS_DIVISION_F", "CIS division",
                   "($P{CIS_DIVISION_F} IS NULL OR EXISTS (SELECT 1 FROM CISADM.CI_ACCT fa WHERE fa.acct_id = b.acct_id AND TRIM(fa.cis_division) = TRIM($P{CIS_DIVISION_F})))",
                   "($P{CIS_DIVISION_F} IS NULL OR TRIM(sa.cis_division) = TRIM($P{CIS_DIVISION_F}))"),
            Filter("ACCT_ID_F", "Account ID",
                   "($P{ACCT_ID_F} IS NULL OR TRIM(b.acct_id) = TRIM($P{ACCT_ID_F}))",
                   "($P{ACCT_ID_F} IS NULL OR TRIM(b.acct_id) = TRIM($P{ACCT_ID_F}))"),
        ]),

    Spec(
        name="payments_by_tender_type_period", label="Payments by Tender Type",
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
            columns=[Col("PAY_MONTH", "Month", width=292), Col("TENDERS", "Tenders", "java.lang.Long", 80, "Right", INT, True),
                     Col("TENDER_AMT", "Amount", "java.math.BigDecimal", 120, "Right", MONEY, True), Col("CANCELLED", "Cancelled", "java.lang.Long", 80, "Right", INT, True),
                     Col("PAYOR_ACCOUNTS", "Payors", "java.lang.Long", 206, "Right", INT, True)]),
        filters=[
            Filter("TENDER_TYPE_CD_F", "Tender type",
                   "($P{TENDER_TYPE_CD_F} IS NULL OR TRIM(t.tender_type_cd) = TRIM($P{TENDER_TYPE_CD_F}))",
                   "($P{TENDER_TYPE_CD_F} IS NULL OR TRIM(t.tender_type_cd) = TRIM($P{TENDER_TYPE_CD_F}))"),
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
SELECT ADJ_ID, CRE_DT, SA_ID, ACCT_ID, CUSTOMER_NAME, ADJ_AMT FROM (
  SELECT TRIM(a.adj_id) AS ADJ_ID, a.cre_dt AS CRE_DT, TRIM(a.sa_id) AS SA_ID, TRIM(sa.acct_id) AS ACCT_ID,
         pn.entity_name AS CUSTOMER_NAME, a.adj_amt AS ADJ_AMT
  FROM CISADM.CI_ADJ a
  JOIN CISADM.CI_SA sa ON sa.sa_id = a.sa_id
  LEFT JOIN CISADM.CI_ACCT_PER ap ON ap.acct_id = sa.acct_id AND TRIM(ap.main_cust_sw) = 'Y'
  LEFT JOIN CISADM.CI_PER_NAME pn ON pn.per_id = ap.per_id AND TRIM(pn.name_type_flg) = 'PRIM'
  WHERE TRIM(a.adj_status_flg) = '50' AND {WINDOW.format(col='a.cre_dt')}
    AND TRIM(a.adj_type_cd) = TRIM($P{{ADJ_TYPE_CD}})
    /*FILTERS*/
  ORDER BY ABS(a.adj_amt) DESC, a.adj_id
) x
FETCH FIRST $P{{TOP_N}} ROWS ONLY""",
            columns=[Col("ADJ_ID", "Adjustment", width=90), Col("CRE_DT", "Created", "java.sql.Timestamp", 80, "Left", "yyyy-MM-dd"),
                     Col("SA_ID", "SA", width=90), Col("ACCT_ID", "Account", width=90), Col("CUSTOMER_NAME", "Main Customer", width=308),
                     Col("ADJ_AMT", "Amount", "java.math.BigDecimal", 120, "Right", MONEY, True)]),
        filters=[
            Filter("ADJ_TYPE_CD_F", "Adjustment type",
                   "($P{ADJ_TYPE_CD_F} IS NULL OR TRIM(a.adj_type_cd) = TRIM($P{ADJ_TYPE_CD_F}))",
                   "($P{ADJ_TYPE_CD_F} IS NULL OR TRIM(a.adj_type_cd) = TRIM($P{ADJ_TYPE_CD_F}))"),
            Filter("ACCT_ID_F", "Account ID",
                   "($P{ACCT_ID_F} IS NULL OR EXISTS (SELECT 1 FROM CISADM.CI_SA fsa WHERE fsa.sa_id = a.sa_id AND TRIM(fsa.acct_id) = TRIM($P{ACCT_ID_F})))",
                   "($P{ACCT_ID_F} IS NULL OR TRIM(sa.acct_id) = TRIM($P{ACCT_ID_F}))"),
            Filter("SA_ID_F", "Service agreement ID",
                   "($P{SA_ID_F} IS NULL OR TRIM(a.sa_id) = TRIM($P{SA_ID_F}))",
                   "($P{SA_ID_F} IS NULL OR TRIM(a.sa_id) = TRIM($P{SA_ID_F}))"),
            Filter("MIN_ABS_AMT_F", "Minimum absolute amount",
                   "($P{MIN_ABS_AMT_F} IS NULL OR ABS(a.adj_amt) >= $P{MIN_ABS_AMT_F})",
                   "($P{MIN_ABS_AMT_F} IS NULL OR ABS(a.adj_amt) >= $P{MIN_ABS_AMT_F})", "java.math.BigDecimal", "singleValueNumber"),
        ]),

    Spec(
        name="gl_by_distribution_code_period", label="GL Activity by Distribution Code",
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
            intro='"By accounting month for distribution code " + $P{DST_ID}',
            sql=f"""
SELECT TO_CHAR(f.accounting_dt, 'YYYY-MM') AS ACCT_MONTH, COUNT(*) AS GL_LINES,
       COALESCE(SUM(CASE WHEN g.amount > 0 THEN g.amount ELSE 0 END), 0) AS DEBIT_AMT,
       COALESCE(SUM(CASE WHEN g.amount < 0 THEN -g.amount ELSE 0 END), 0) AS CREDIT_AMT,
       COALESCE(SUM(g.amount), 0) AS NET_AMT
FROM CISADM.CI_FT_GL g
JOIN CISADM.CI_FT f ON f.ft_id = g.ft_id
WHERE TRIM(f.freeze_sw) = 'Y' AND {WINDOW.format(col='f.accounting_dt')} AND TRIM(g.dst_id) = TRIM($P{{DST_ID}})
GROUP BY TO_CHAR(f.accounting_dt, 'YYYY-MM')
ORDER BY ACCT_MONTH""",
            columns=[Col("ACCT_MONTH", "Month", width=328), Col("GL_LINES", "Lines", "java.lang.Long", 70, "Right", INT, True),
                     Col("DEBIT_AMT", "Debits", "java.math.BigDecimal", 120, "Right", MONEY, True), Col("CREDIT_AMT", "Credits", "java.math.BigDecimal", 120, "Right", MONEY, True),
                     Col("NET_AMT", "Net", "java.math.BigDecimal", 140, "Right", MONEY, True)]),
        filters=[
            Filter("DST_ID_F", "Distribution code",
                   "($P{DST_ID_F} IS NULL OR TRIM(g.dst_id) = TRIM($P{DST_ID_F}))",
                   "($P{DST_ID_F} IS NULL OR TRIM(g.dst_id) = TRIM($P{DST_ID_F}))"),
            Filter("GL_ACCT_F", "GL account (exact)",
                   "($P{GL_ACCT_F} IS NULL OR TRIM(g.gl_acct) = TRIM($P{GL_ACCT_F}))",
                   "($P{GL_ACCT_F} IS NULL OR TRIM(g.gl_acct) = TRIM($P{GL_ACCT_F}))"),
            Filter("GL_DIVISION_F", "GL division",
                   "($P{GL_DIVISION_F} IS NULL OR TRIM(f.gl_division) = TRIM($P{GL_DIVISION_F}))",
                   "($P{GL_DIVISION_F} IS NULL OR TRIM(f.gl_division) = TRIM($P{GL_DIVISION_F}))"),
            Filter("CIS_DIVISION_F", "CIS division",
                   "($P{CIS_DIVISION_F} IS NULL OR TRIM(f.cis_division) = TRIM($P{CIS_DIVISION_F}))",
                   "($P{CIS_DIVISION_F} IS NULL OR TRIM(f.cis_division) = TRIM($P{CIS_DIVISION_F}))"),
            Filter("FT_TYPE_FLG_F", "FT type (BS, BX, AD, AX, PS, PX)",
                   "($P{FT_TYPE_FLG_F} IS NULL OR TRIM(f.ft_type_flg) = TRIM($P{FT_TYPE_FLG_F}))",
                   "($P{FT_TYPE_FLG_F} IS NULL OR TRIM(f.ft_type_flg) = TRIM($P{FT_TYPE_FLG_F}))"),
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
