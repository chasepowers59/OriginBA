# Jaspersoft Artifact Inventory

## Purpose

This tool inventories Jaspersoft artifacts across local repo assets and exported
repository ZIPs so we can:

- distinguish Domains, Ad Hocs, wrapper resources, favorites, and JRXML reports
- extract repository URIs and datasource wiring
- understand what has to move during client promotion
- build future automation for Domain-driven report generation

Script:

- [inventory_jaspersoft_artifacts.py](/Users/chase/OriginBA-3/scripts/jaspersoft/inventory_jaspersoft_artifacts.py)

## What It Scans

By default it scans:

- `domains/`
- `reports/`
- `server/input_controls/`
- `deploy/jaspersoft_client_promotion/`

It reads:

- `.xml`
- `.jrxml`
- `.json`
- `.zip`

For ZIP files, it inspects member XML/JSON payloads and emits both:

- one record for the ZIP itself
- one record per recognized artifact inside the ZIP

## Artifact Types It Recognizes

- `domain_schema`
- `semantic_layer_domain`
- `adhoc_view`
- `favorite`
- `repository_folder`
- `export_index`
- `favorites_index`
- `jrxml_report`
- `input_control_json`
- `repository_export_zip`

Unknown or malformed files are still recorded as:

- `xml_unknown`
- `xml_parse_error`
- `json_unknown`
- `json_parse_error`

## Captured Metadata

Each artifact record can include:

- source type
  - local file
  - ZIP
  - ZIP member
- logical path
- container ZIP path when applicable
- artifact name
- root tag
- repository URIs
- datasource aliases
- datasource resource URIs
- file resource dependencies such as `schema.data`

## Recommended Commands

### Console summary only

```bash
python3 scripts/jaspersoft/inventory_jaspersoft_artifacts.py
```

### Write full JSON inventory

```bash
python3 scripts/jaspersoft/inventory_jaspersoft_artifacts.py \
  --output-json output/jaspersoft_artifact_inventory.json \
  --output-summary-json output/jaspersoft_artifact_inventory_summary.json
```

### Scan specific roots only

```bash
python3 scripts/jaspersoft/inventory_jaspersoft_artifacts.py \
  --roots domains/exports reports server/input_controls \
  --output-json output/jaspersoft_artifact_inventory.json
```

## Why This Matters

This is the first foundational step for higher-value Jaspersoft automation:

1. artifact dependency graphing
2. endpoint rewrite across all reports
3. package promotion validation
4. Ad Hoc understanding and extraction
5. Domain-to-report template generation

Without a reliable inventory layer, those later automations are too brittle.
