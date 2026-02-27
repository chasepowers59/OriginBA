# Template Authoring Playbook (Jaspersoft Studio 9.0 + JRS)

## Purpose
Standardize how report templates are created, reused, and promoted across organizations.

## Starter Assets
- `reports/templates/base_letter_template.jrxml`
- `reports/templates/base_kpi_template.jrxml`
- `reports/subreports/common/address_block.jrxml`
- `reports/subreports/common/signature_block.jrxml`

## Naming Standards
- Parameters: `ALL_CAPS` snake case (`CLIENT_ID`, `START_TS`, `END_TS`)
- Input Control names: exact match to parameter names
- Subreport resource IDs: lowercase snake (`line_items_fieldwork`, `address_block`)

## Build Process
1. Copy the closest base template from `reports/templates/`.
2. Keep datasource-agnostic SQL with bind parameters.
3. Avoid hardcoded datasource names in query logic.
4. If reusing common sections, reference repository resources:
   - `repo:subreports/common/address_block`
   - `repo:subreports/common/signature_block`
5. Compile in Studio and preview with a small parameter set.

## Multi-Org Pattern
1. Keep one canonical JRXML in git.
2. Deploy to each org path.
3. Bind report unit to that org datasource.
4. Keep same parameter contract across orgs.

## Parameter Design Rules
- Always provide operational filters:
  - `CLIENT_ID`
  - `START_TS`
  - `END_TS`
- Use nullable filters only when business logic allows.
- For text IDs, use trim-safe comparisons in SQL when needed.

## Subreport Rules
- Prefer repository-relative references (`repo:`) for server runtime.
- Place common subreports under `/subreports/common/`.
- Keep subreport parameters minimal and explicit.

## Validation Checklist (Author)
1. JRXML compiles in Studio.
2. No `cvc-complex-type` XML schema errors.
3. Preview returns expected rows for known test input.
4. Input Controls match parameter names exactly.
5. Report runs in JRS with org datasource binding.

## Recommended Folder Contract
- `reports/templates/`: base layouts only
- `reports/subreports/common/`: reusable components
- `reports/`: concrete report units
- `server/input_controls/`: JSON payloads
- `deploy/`: packaging/deploy scripts
