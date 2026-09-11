# Jaspersoft Style Implementation (Origin 2025)

Source:
- Corporate style guide (2025)
- SharePoint: `Homepage > Documents > Marketing > Style Guide`

## Required Standards for All New Reports

1. Font system
- Primary font: `Aptos`
- H1: 20pt bold
- H2: 16pt bold
- H3: 14pt regular
- Body: 11pt
- Table body: 10pt

2. Approved color palette (hex)
- Orange `#BE4D21`
- Gold `#E9870D`
- Marmalade `#FFB450`
- White `#F5F0EB`
- Teal `#64D0DE`
- Blue `#3BAFE2`
- Sapphire `#006FAC`
- Indigo `#1348AB`
- Black `#000000`

3. Table styling
- Header: Aptos 12pt bold, white text, Sapphire background.
- Body: Aptos 10pt, black text, light background (`#F5F0EB`).
- Header alignment centered, body left aligned.

4. Chart styling
- Use palette-consistent series colors.
- Recommended severity chart order:
  - Critical: `#BE4D21`
  - High Geo: `#E9870D`
  - High Aging: `#FFB450`
  - Normal: `#64D0DE`

5. Confidential footer (mandatory)
- `@2025, Origin Utility, Inc / Proprietary & Confidential / Expressly for CLIENT NAME`
- For internal docs: use `INTERNAL USE ONLY`.

6. Logo placement
- Place logo in upper-right unless logo itself is subject.
- Preserve aspect ratio; no color variation.

## Style Implementation Method

- Styles are embedded directly inside each JRXML report.
- Do not reference external `.jrtx` files for production reports in this repository.
- Keep `style` blocks in-report so designs are self-contained and portable.

## Reports Updated to Match This Standard

- `reports/field_ops_action_queue.jrxml`
- `reports/map_meters_coverage.jrxml`
- `reports/templates/base_kpi_template.jrxml`
- `reports/templates/base_letter_template.jrxml`
- `reports/templates/base_customer_bill_template.jrxml`

## Enforcement Checklist (Before Publish)

1. `Aptos` is used for report text.
2. Only approved palette colors are used.
3. Table header/body styles follow standard.
4. Chart colors follow severity mapping.
5. Confidential footer is present.
6. Logo placement/size follows policy.
