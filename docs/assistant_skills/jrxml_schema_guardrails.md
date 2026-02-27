# JRXML Schema Guardrails (Studio/Server 9.x)

## Required Element Order (high-level)
1. `property`, `style`, `parameter`, `queryString`, `field`, `sortField`, `variable`, `filterExpression`, `group`, then bands.
2. `pageFooter` must come before `summary`.
3. `filterExpression` must come before `group`.

## Chart Rules
1. Do not use unsupported `seriesColor` in core chart blocks.
2. Do not place unsupported attributes like `backgroundColor` on `<plot>`.
3. Keep chart child order strict (`plot`, axis formats, etc.).

## Domain Rules
1. `<queryFields>` must not be empty.
2. Domain IDs must match exported schema IDs exactly.
3. If Studio says `query.no.data`, re-open Dataset and Query and re-add fields explicitly.

## Expression Rules
1. Use null-safe expressions.
2. Prefer `new java.text.DecimalFormat("#0.0").format(...)` over fragile inline `String.format(...)` escaping.
3. Keep booleans explicit (`Boolean.TRUE/FALSE` defaults).
