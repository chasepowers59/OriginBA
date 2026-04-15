# Jaspersoft Repository Import Debugging Runbook

## Purpose

Document the working repair pattern for Jaspersoft Server repository imports so we do not repeat the same debugging cycle when an exported Ad Hoc/report package fails after import.

Use this runbook when any of these happen:
- import says a repository resource cannot be found
- the report imports but fails with `Field not found`
- the report imports but fails with `Data source ... not found`
- an exported Ad Hoc wrapper report depends on a shared template under `/public/templates/`

## Case That Established This Pattern

Source artifact:
- `Deposit Control Report.zip`

Target object:
- `Deposit_Control___Detailed_View_Report`

Domain:
- `Tender___Payments_Snapshot___Domain`

## What Actually Happened

### 1. ZIP structure mattered first

Initial symptom:
- `Resource /organizations/.../Deposit_Control___Detailed_View_Report cannot be found`

Root cause:
- The rebuilt ZIP did not preserve the server's repository export structure closely enough.

Required structure:
- `index.xml` at ZIP root
- `resources/`
- `favorites/` when present in the export
- full `resources/...` directory tree
- `.folder.xml` files
- companion `_files` folders
- explicit directory entries

## 2. The exported wrapper report was not self-contained

Observed in:
- exported `Deposit_Control___Detailed_View_Report.xml`

Critical detail:
- `<mainReport><uri>/public/templates/actual_size.820.jrxml</uri></mainReport>`

Meaning:
- The report unit compiled against a shared public template.
- The exported wrapper itself was not enough to guarantee correct behavior after import.

## 3. The shared template was the source of the compile failure

Observed in:
- exported `resources/public/templates/actual_size.820.jrxml.data`

Hardcoded field references found there:
- `NewSet1.DESCR_3`
- `NewSet2.CUR_AMT`

Observed symptom after import:
- `Report design not valid`
- `Field not found : NewSet1.DESCR_3`
- `Field not found : NewSet2.CUR_AMT`

Interpretation:
- The imported report unit was compiling a shared template unrelated to the deposit-control saved view.

## 4. The durable fix was a self-contained report unit

Instead of preserving the Ad Hoc wrapper unchanged, the working fix was:
- keep the same repository path and object name
- replace the shared-template `mainReport` reference with a local `main_jrxml` file resource
- point the report unit directly to the payments Domain
- keep the package self-contained inside the report-unit `_files` folder

This removed dependency on `/public/templates/actual_size.820.jrxml`.

## 5. Export files have different source-of-truth roles

Use these as source of truth:
- `schema.data`
  - Domain field IDs
  - field types
  - datasource alias wiring
- `topicJRXML.data`
  - exact saved-view field IDs
  - Ad Hoc state and server-side field naming patterns
- `stateXML.data`
  - saved filters
  - grouping
  - measure functions

Do not use these as source of truth:
- `topicJRXML.data` as the maintained hand-authored JRXML style
- shared `/public/templates/...` as automatically safe dependencies

## 6. URI style inside packaged JRXML matters

The next failure after template repair was:
- `Data source /SmartCity/Report/Workstreams/Development/Snapshots/Cashiering/Tender___Payments_Snapshot___Domain not found`

Root cause:
- The rebuilt JRXML used org-relative Domain URIs.
- The server-packaged report-unit pattern for this environment expected the full repository URI.

Working pattern:
- `ireport.domainUri=/organizations/organization_1/organizations/Origin_DEV/...`
- `com.jaspersoft.jrs.data.source=/organizations/organization_1/organizations/Origin_DEV/...`

Do not assume Studio-safe org-relative URIs are also correct for imported packaged report units.

## 7. Practical decision rule

When an exported report package depends on `/public/templates/...` and fails after import:
1. inspect the shared template
2. search it for hardcoded fields or unrelated datasets
3. if it is brittle, stop preserving the wrapper unchanged
4. rebuild the report unit as a self-contained local-`main_jrxml` package

## 8. Validation checklist before import

- XML-parse the report unit XML
- XML-parse the JRXML
- search package contents for:
  - old shared-template references
  - old broken field names
  - stale saved-view resource URIs
- confirm ZIP contains:
  - `index.xml`
  - full `resources/...` tree
  - `.folder.xml`
  - expected `_files` folders
- confirm JRXML Domain properties use the correct URI form for the target server pattern

## 9. Working repository pattern going forward

For maintainable OriginBA delivery:
- use the export as source of truth for repository object hierarchy
- use `schema.data` and `topicJRXML.data` to confirm field IDs and saved view state
- prefer self-contained report units over brittle shared-template wrapper reports when importing replacements
- keep the report logic in a maintained JRXML in `reports/`
- keep parameter contract documentation in `server/input_controls/`

## Related files

- [jaspersoft_repository_export_structure.md](/C:/Users/cvpow/OneDrive/Desktop/OriginBA/docs/jaspersoft_repository_export_structure.md)
- [payments_deposit_control_summary.jrxml](/C:/Users/cvpow/OneDrive/Desktop/OriginBA/reports/payments_deposit_control_summary.jrxml)
