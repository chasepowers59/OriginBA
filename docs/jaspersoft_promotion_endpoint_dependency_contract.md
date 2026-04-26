# Jaspersoft Promotion Endpoint And Dependency Contract

## Why this exists

Jaspersoft imports are path-sensitive. Promotions fail or silently miswire when any of these relationships break:

1. report/ad hoc endpoint URI
2. report/ad hoc -> domain URI reference
3. domain -> datasource URI reference
4. repository folder/index structure consistency (`index.xml`, `.folder.xml`, `_files`)

This contract documents the non-negotiable rules for repeatable promotions.

## Canonical dependency chain

For every promoted analytics artifact, the chain must resolve end-to-end:

1. `reportUnit` or `adhocDataView` resource exists at target URI
2. that resource references an existing Domain URI
3. that Domain references an existing datasource URI
4. all three live under valid repository paths included in `index.xml`

If any link breaks, import may succeed with unusable reports.

## Endpoint rewrite contract (automation behavior)

Promotion automation is implemented by:

- `scripts/jaspersoft/prepare_client_imports.py`
- `scripts/jaspersoft/run_client_import_pipeline.py`
- `scripts/jaspersoft/verify_prepared_import.py`

Expected behavior per target org:

1. rewrite source org token (for example `Origin_DEV`) to target org across content
2. rewrite source datasource token (for example `Origin_DEV_DS`) to target datasource token
3. rename file and folder paths containing those identifiers
4. preserve repository shape and import manifest
5. validate no leftover source org/source datasource identifiers remain

## Ad Hoc view to Domain rules

For every `adhocDataView`:

1. the data source URI inside the view must point to a valid target Domain URI
2. the target Domain URI should be in the same curated package scope (for Standard Offering promotions)
3. wrapper artifacts must not introduce unintended `/public/templates/...` dependencies unless explicitly accepted

Practical rule: if an Ad Hoc endpoint is promoted, its Domain endpoint must be promoted in the same package.

## Domain to datasource rules

For every promoted Domain XML:

1. `jdbcDataSource` or datasource URI reference must resolve to target datasource
2. do not leave a source datasource reference in client package contents
3. when datasource overlay mode is enabled, datasource resource XML must be present and indexed
4. when overlay mode is disabled, target server must already contain the expected datasource resource

Practical rule: no Domain should point to `Origin_DEV_DS` in a client-target package.

## Repository structure invariants (must remain consistent)

These objects are mandatory for import stability:

1. ZIP root contains `index.xml`
2. repository assets are under `resources/`
3. organization path follows:
   - `resources/organizations/organization_1/organizations/<TARGET_ORG>/...`
4. folder metadata files (`.folder.xml`) remain aligned to actual folders
5. companion payload folders (`*_files/`) are preserved when referenced
6. `favorites/` subtree, if present, must point to target org only

Breaking any invariant can produce partial imports or unresolved references.

## Add-on import wrapper contract (critical)

This section captures the exact failure mode encountered while packaging new Standard Offering add-ons and defines the mandatory wrapper format to avoid repeats.

### Why this is critical

Jaspersoft import failures like:

- `Folder details for folder ".../Standard_Offering/Customer_Operations" were not found in the import information`

are usually wrapper/manifest consistency failures, not report logic failures.

### Canonical wrapper pattern (must match known-good package)

Use `deploy/jaspersoft_standard_offering/Standard_Offering_import.zip` as wrapper template.

Required `index.xml` behavior:

1. keep properties as in known-good package (`keyalias`, `pathProcessorId`, `rootTenantId`, `jsVersion`, `encrypted`)
2. module folder:
   - `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Standard_Offering`
3. module resources for this package family should follow the known-good pattern:
   - include root Standard Offering resource and ensure folder details are resolvable from packaged metadata
4. never mix wrapper strategies between iterations (for example custom multi-resource one run, single-root next run) without full rebuild + revalidation

Required folder metadata behavior:

1. `.folder.xml` files under `Standard_Offering` should follow the same style as the known-good package
2. avoid hand-crafted folder trees when a working exported `.folder.xml` pattern exists
3. if copying folder descriptors from a template package, ensure they are compatible with packaged paths and do not reference unrelated roots

### Non-negotiable anti-patterns (do not ship)

1. mixed repository roots in one ZIP (for example both `Standard_Offering` and `Standard_Offering_Add_Ons`)
2. stale resources left in `_build` that are no longer represented in `index.xml`
3. `.folder.xml` child folder declarations that do not resolve in import context
4. packaging from an incrementally edited `_build` without a clean rebuild sweep

### Full preflight validation (required before push/import)

Before every add-on ZIP build:

1. confirm only one target root exists in `_build/resources`:
   - `.../Report/Standard_Offering`
2. confirm no alternate root subtree exists:
   - `.../Report/Standard_Offering_Add_Ons` (must be absent for Standard_Offering-targeted package)
3. verify `index.xml` module folder matches target root exactly
4. verify every path family referenced by folder metadata exists in packaged resources
5. verify no forbidden/stale path tokens remain:
   - previous root names, old org tokens, old datasource tokens
6. rebuild ZIP from current `_build` only (no append/update-in-place)

### Single-test package contract

Single-test ZIPs used for import diagnostics must:

1. use the same wrapper convention as the known-good package
2. include:
   - target Ad Hoc XML + `_files`
   - required Domain XML + `_files`
   - required `.folder.xml` chain for the target path
   - valid `index.xml` module folder/resource contract
3. exclude unrelated ad hoc/domain payloads unless required for wrapper consistency

### Incident summary (April 2026)

Observed break cause:

1. iterative rebuilds introduced wrapper drift
2. stale alternate root content remained in package
3. folder-detail resolution failed on `Customer_Operations`

Corrective actions applied:

1. removed alternate root subtree from `_build`
2. realigned `index.xml` to known-good wrapper strategy
3. realigned `.folder.xml` style to known-good package conventions
4. rebuilt full and single-test ZIPs from clean state

## Standard Offering specific contract

Current reporting source-of-truth package:

- `deploy/jaspersoft_standard_offering/Standard_Offering_import.zip`

Current verification source:

- `deploy/jaspersoft_standard_offering/standard_offering_verification.json`

Current audit source:

- `deploy/jaspersoft_standard_offering/standard_offering_package_audit.json`

For this package family:

1. curated endpoints must resolve under:
   - `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Standard_Offering/...`
2. report/ad hoc references must point to Domains carried in the curated tree
3. Domain datasource references must resolve to the expected datasource alias
4. package must remain free of banned template dependency unless explicitly intended

## Pre-import checklist

Before importing any promoted ZIP:

1. run rewrite pipeline (or dry run)
2. run package verification (`verify_prepared_import.py`)
3. confirm:
   - target org root exists
   - no leftover source org/source datasource identifiers
   - report/ad hoc endpoints point to target paths
   - Domain URIs referenced by reports/ad hoc exist
   - Domain datasource references resolve for target
   - `index.xml` includes all required resources

## Post-import smoke checks

After import:

1. open one report per workstream from Standard Offering
2. open one Ad Hoc view per workstream and run with simple filter
3. verify prompts/input controls load
4. verify at least one query executes without datasource/domain resolution errors

## Failure signatures and meaning

Common error patterns:

- `Reference resource ... Domain ... not found`
  - report/ad hoc endpoint points at missing Domain URI
- `Reference resource ... DataSource ... not found`
  - Domain points at datasource that was not imported or does not exist on target
- import root/folder metadata errors
  - `index.xml` scope and `.folder.xml` hierarchy are inconsistent

## Change-management policy

Any promotion-impacting change must be treated as a contract change when it affects:

1. repository endpoint URIs
2. Domain resource location or naming
3. datasource alias naming
4. import structure (`index.xml` or folder metadata behavior)

Required companion updates:

1. update this contract doc
2. update `docs/jaspersoft_client_promotion_pipeline.md` if process changed
3. update verification logic/scripts if new invariant is introduced
