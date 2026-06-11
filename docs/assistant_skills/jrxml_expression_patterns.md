# JRXML Expression Patterns (JRS 9.x)

Catalog of safe expression idioms used in this repo. Prefer copying these patterns over inventing new syntax.

## Optional Text Filters (null-safe)

Use when a report parameter is optional and should not filter when blank:

```java
$P{REGION} == null || $P{REGION}.trim().length() == 0 || $F{DIVISION_CD}.equalsIgnoreCase($P{REGION}.trim())
```

Pattern:
```java
$P{PARAM} == null || $P{PARAM}.trim().length() == 0 || <field predicate>
```

## Optional Boolean Filters

```java
!$P{ONLY_OPEN}.booleanValue() || ($F{END_DTTM} == null)
```

Default booleans explicitly:
```java
<defaultValueExpression><![CDATA[Boolean.FALSE]]></defaultValueExpression>
```

## Date Window Filters

Inclusive end date:
```java
!$F{EVENT_DATE}.before($P{START_DATE}) && !$F{EVENT_DATE}.after($P{END_DATE})
```

Handle null parameters:
```java
$P{START_DATE} == null || !$F{EVENT_DATE}.before($P{START_DATE})
```

## Report-Level KPI Variables

```xml
<variable name="TOTAL_ROWS" class="java.lang.Integer" calculation="Count">
  <variableExpression><![CDATA[$F{ID}]]></variableExpression>
  <initialValueExpression><![CDATA[0]]></initialValueExpression>
</variable>
```

Use in summary band:
```xml
<textField evaluationTime="Report">
  <textFieldExpression><![CDATA["Rows: " + $V{TOTAL_ROWS}]]></textFieldExpression>
</textField>
```

## Number Formatting

Prefer `DecimalFormat`:
```java
$F{AMOUNT} == null ? "0.00" : new java.text.DecimalFormat("#,##0.00").format($F{AMOUNT})
```

Integer KPIs:
```java
$F{COUNT} == null ? "0" : new java.text.DecimalFormat("#,##0").format($F{COUNT})
```

## Null-Coalescing Display Values

```java
$F{REGION} == null ? "UNKNOWN" : $F{REGION}
```

## Conditional Styles

```xml
<style name="SeverityCell" style="Base" mode="Opaque">
  <conditionalStyle>
    <conditionExpression><![CDATA[
($F{DAYS_OLD} != null && $F{DAYS_OLD}.intValue() >= $P{STALE_DAYS}.intValue())
    ]]></conditionExpression>
    <style backcolor="#B91C1C" forecolor="#FFFFFF"/>
  </conditionalStyle>
</style>
```

## printWhenExpression

Show row only when exception flag is set:
```java
"Y".equalsIgnoreCase($F{IS_ERROR_SW})
```

Hide detail for aggregate/header rows:
```java
$V{PAGE_NUMBER}.intValue() == 1
```

## Domain Field Binding

JRXML field name can differ from Domain item ID:
```xml
<field name="STATUS_DESCR" class="java.lang.String">
  <property name="net.sf.jasperreports.query.field.id" value="DESCR_1"/>
</field>
```

Query must reference the Domain item ID, not the JRXML field alias:
```xml
<queryField id="DESCR_1"/>
```

## Forbidden Patterns

Do not use:
- `<seriesColor>` in chart blocks
- Unsupported `<plot backgroundColor="...">` attributes on JRS 9.x
- Table-qualified Domain query IDs like `D1_SP.D1_SP_ID`
- Fragile nested `String.format` when `DecimalFormat` works

## Reference Reports

| Pattern | Example report |
|---------|----------------|
| Domain filters + severity styling | `reports/field_activity_operational_intelligence.jrxml` |
| KPI variables + bar chart | `reports/usage_device_dashboard.jrxml` |
| Exception row filtering | `reports/billing_missing_bill_exceptions.jrxml` |
| Executive summary KPIs | `reports/general_ledger_batch_executive_packet.jrxml` |

## Validation

After editing expressions:
```bash
python3 scripts/validate_jrxml_schema.py reports/<report>.jrxml
```
