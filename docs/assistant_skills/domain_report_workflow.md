# Domain Report Workflow (Jaspersoft 9.x)

## 1) Discovery
1. Confirm domain URI and organization path.
2. Extract exact domain field IDs from schema export.
3. Map business intent to available fields.

## 2) Build
1. Create JRXML in `reports/`.
2. Use `language="domain"` and explicit `<queryField id="..."/>`.
3. Add fields with `net.sf.jasperreports.query.field.id`.
4. Add parameters in ALL_CAPS.
5. Add filterExpression with null-safe checks.

## 3) Controls
1. Create/update:
   - `server/input_controls/<report>_input_controls.json`
   - `server/input_controls/<report>_input_controls_rest.json`
2. Ensure IDs exactly match JRXML parameter names.

## 4) Validate
1. XML parse of JRXML.
2. JSON parse of input control files.
3. Studio test with minimal fields/params first.
4. Expand query fields in batches if domain cache/query errors appear.

## 5) Promote
1. Publish to NON-PROD first.
2. Bind repository datasource alias.
3. Run smoke PDF/HTML render.
4. Validate filters, totals, and null-handling behavior.
