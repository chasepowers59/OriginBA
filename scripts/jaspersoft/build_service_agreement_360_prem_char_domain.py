#!/usr/bin/env python3
"""Patch Standard Offering Service Agreement 360 domain with live CISADM premise characteristics.

Two passes: this file adds CI_PREM_CHAR on the CI_SA -> CI_PREM path (the 2.1 group); then
patch_domain_characteristics.py turns both characteristic tables (SA and premise) into
derived tables that carry their own type/value descriptions, a resolved value and an
IS_CURRENT_SW flag -- see that file's docstring for why.

Every table takes the SOURCE SCHEMA's datasource id. The first build hardcoded Origin_DEV_DS
into the added tables while the Newark export's wrapper referenced /DataSource/Newark1_DS;
a domain cannot join across datasource ids, and the schema id must be the wrapper's.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
OUT_ROOT = REPO / "domains/manual_imports/service_agreement_360_prem_char"
DEFAULT_SOURCE_SCHEMA = OUT_ROOT / "schema.reference.xml"
DEFAULT_SOURCE_ZIP = (
    REPO
    / "deploy/jaspersoft_client_promotion/prepared_imports/Newark1_Standard_Offering_import.zip"
)
DOMAIN_NAME = "Service_Agreement___Domain"
FOLDER = "/SmartCity/Report/Standard_Offering/Customer_Operations/Service_Agreements"
MARKER = "CI_PREM_CHAR_CHAR_TYPE_CD"
DS_PLACEHOLDER = "__DS__"

PREM_CHAR_TABLE = """    <jdbcTable id="CI_PREM_CHAR" datasourceId="__DS__" datasourceTableName="CI_PREM_CHAR" schemaAlias="CISADM">
      <fieldList>
        <field id="PREM_ID" type="java.lang.String"></field>
        <field id="CHAR_TYPE_CD" type="java.lang.String"></field>
        <field id="CHAR_VAL" type="java.lang.String"></field>
        <field id="EFFDT" type="java.sql.Timestamp"></field>
        <field id="VERSION" type="java.math.BigDecimal"></field>
        <field id="ADHOC_CHAR_VAL" type="java.lang.String"></field>
        <field id="CHAR_VAL_FK1" type="java.lang.String"></field>
        <field id="CHAR_VAL_FK2" type="java.lang.String"></field>
        <field id="CHAR_VAL_FK3" type="java.lang.String"></field>
        <field id="CHAR_VAL_FK4" type="java.lang.String"></field>
        <field id="CHAR_VAL_FK5" type="java.lang.String"></field>
        <field id="SRCH_CHAR_VAL" type="java.lang.String"></field>
      </fieldList>
    </jdbcTable>
"""

CHAR_TYPE_L_2_TABLE = """    <jdbcTable id="CI_CHAR_TYPE_L_2" datasourceId="__DS__" datasourceTableName="CI_CHAR_TYPE_L" schemaAlias="CISADM">
      <fieldList>
        <field id="CHAR_TYPE_CD" type="java.lang.String"></field>
        <field id="LANGUAGE_CD" type="java.lang.String"></field>
        <field id="DESCR" type="java.lang.String"></field>
        <field id="OWNER_FLG" type="java.lang.String"></field>
        <field id="VERSION" type="java.math.BigDecimal"></field>
      </fieldList>
    </jdbcTable>
"""

CHAR_VAL_L_2_TABLE = """    <jdbcTable id="CI_CHAR_VAL_L_2" datasourceId="__DS__" datasourceTableName="CI_CHAR_VAL_L" schemaAlias="CISADM">
      <fieldList>
        <field id="CHAR_TYPE_CD" type="java.lang.String"></field>
        <field id="CHAR_VAL" type="java.lang.String"></field>
        <field id="LANGUAGE_CD" type="java.lang.String"></field>
        <field id="DESCR" type="java.lang.String"></field>
        <field id="OWNER_FLG" type="java.lang.String"></field>
        <field id="VERSION" type="java.math.BigDecimal"></field>
      </fieldList>
    </jdbcTable>
"""

JOINS = """
        <join expr="CI_PREM.PREM_ID == CI_PREM_CHAR.PREM_ID" left="CI_PREM" right="CI_PREM_CHAR" type="leftOuter" weight="1"></join>
        <join expr="CI_PREM_CHAR.CHAR_TYPE_CD == CI_CHAR_TYPE_L_2.CHAR_TYPE_CD and CI_CHAR_TYPE_L_2.LANGUAGE_CD == 'ENG'" left="CI_PREM_CHAR" right="CI_CHAR_TYPE_L_2" type="leftOuter" weight="1"></join>
        <join expr="CI_PREM_CHAR.CHAR_TYPE_CD == CI_CHAR_VAL_L_2.CHAR_TYPE_CD and CI_PREM_CHAR.CHAR_VAL == CI_CHAR_VAL_L_2.CHAR_VAL and CI_CHAR_VAL_L_2.LANGUAGE_CD == 'ENG'" left="CI_PREM_CHAR" right="CI_CHAR_VAL_L_2" type="leftOuter" weight="1"></join>"""

TABLE_REFS = """
        <tableRef alwaysIncludeTable="false" tableAlias="CI_PREM_CHAR" tableId="CI_PREM_CHAR"></tableRef>
        <tableRef alwaysIncludeTable="false" tableAlias="CI_CHAR_TYPE_L_2" tableId="CI_CHAR_TYPE_L_2"></tableRef>
        <tableRef alwaysIncludeTable="false" tableAlias="CI_CHAR_VAL_L_2" tableId="CI_CHAR_VAL_L_2"></tableRef>"""

JOIN_TREE_FIELDS = """
        <field id="CI_PREM_CHAR.PREM_ID" type="java.lang.String"></field>
        <field id="CI_PREM_CHAR.CHAR_TYPE_CD" type="java.lang.String"></field>
        <field id="CI_PREM_CHAR.EFFDT" type="java.sql.Timestamp"></field>
        <field id="CI_PREM_CHAR.CHAR_VAL" type="java.lang.String"></field>
        <field id="CI_PREM_CHAR.ADHOC_CHAR_VAL" type="java.lang.String"></field>
        <field id="CI_PREM_CHAR.CHAR_VAL_FK1" type="java.lang.String"></field>
        <field id="CI_PREM_CHAR.CHAR_VAL_FK2" type="java.lang.String"></field>
        <field id="CI_PREM_CHAR.CHAR_VAL_FK3" type="java.lang.String"></field>
        <field id="CI_PREM_CHAR.CHAR_VAL_FK4" type="java.lang.String"></field>
        <field id="CI_PREM_CHAR.CHAR_VAL_FK5" type="java.lang.String"></field>
        <field id="CI_PREM_CHAR.SRCH_CHAR_VAL" type="java.lang.String"></field>
        <field id="CI_PREM_CHAR.VERSION" type="java.math.BigDecimal"></field>
        <field id="CI_CHAR_TYPE_L_2.CHAR_TYPE_CD" type="java.lang.String"></field>
        <field id="CI_CHAR_TYPE_L_2.LANGUAGE_CD" type="java.lang.String"></field>
        <field id="CI_CHAR_TYPE_L_2.DESCR" type="java.lang.String"></field>
        <field id="CI_CHAR_TYPE_L_2.OWNER_FLG" type="java.lang.String"></field>
        <field id="CI_CHAR_TYPE_L_2.VERSION" type="java.math.BigDecimal"></field>
        <field id="CI_CHAR_VAL_L_2.CHAR_TYPE_CD" type="java.lang.String"></field>
        <field id="CI_CHAR_VAL_L_2.CHAR_VAL" type="java.lang.String"></field>
        <field id="CI_CHAR_VAL_L_2.LANGUAGE_CD" type="java.lang.String"></field>
        <field id="CI_CHAR_VAL_L_2.DESCR" type="java.lang.String"></field>
        <field id="CI_CHAR_VAL_L_2.OWNER_FLG" type="java.lang.String"></field>
        <field id="CI_CHAR_VAL_L_2.VERSION" type="java.math.BigDecimal"></field>"""

FORMULA_FIELD = """
        <field id="PREM_CHAR_DIST" dataSetExpression="CountDistinct(Concatenate(CI_PREM_CHAR.PREM_ID, '_', CI_PREM_CHAR.CHAR_TYPE_CD, '_', CI_PREM_CHAR.EFFDT), 'Current')" type="java.lang.Long"></field>"""

FORMULA_ITEM = """
        <item id="PREM_CHAR_DIST" label="Distinct Premise Characteristic" resourceId="JoinTree_1.PREM_CHAR_DIST"></item>"""

ITEM_GROUP = """
    <itemGroup id="CI_PREM_CHAR" label="2.1) Premise Characteristics" resourceId="JoinTree_1">
      <items>
        <item id="CI_PREM_CHAR_PREM_ID" label="Premise ID" resourceId="JoinTree_1.CI_PREM_CHAR.PREM_ID"></item>
        <item id="CI_PREM_CHAR_CHAR_TYPE_CD" label="Characteristic Type Code" resourceId="JoinTree_1.CI_PREM_CHAR.CHAR_TYPE_CD"></item>
        <item id="CI_CHAR_TYPE_L_2_DESCR" label="Characteristic Type Description" resourceId="JoinTree_1.CI_CHAR_TYPE_L_2.DESCR"></item>
        <item id="CI_PREM_CHAR_EFFDT" label="Characteristic Effective Date" resourceId="JoinTree_1.CI_PREM_CHAR.EFFDT"></item>
        <item id="CI_PREM_CHAR_CHAR_VAL" label="Characteristic Value Code" resourceId="JoinTree_1.CI_PREM_CHAR.CHAR_VAL"></item>
        <item id="CI_CHAR_VAL_L_2_DESCR" label="Characteristic Value Description" resourceId="JoinTree_1.CI_CHAR_VAL_L_2.DESCR"></item>
        <item id="CI_PREM_CHAR_ADHOC_CHAR_VAL" label="Ad Hoc Characteristic Value" resourceId="JoinTree_1.CI_PREM_CHAR.ADHOC_CHAR_VAL"></item>
        <item id="CI_PREM_CHAR_SRCH_CHAR_VAL" label="Search Characteristic Value" resourceId="JoinTree_1.CI_PREM_CHAR.SRCH_CHAR_VAL"></item>
        <item id="CI_PREM_CHAR_CHAR_VAL_FK1" label="Characteristic Value FK1" resourceId="JoinTree_1.CI_PREM_CHAR.CHAR_VAL_FK1"></item>
        <item id="CI_PREM_CHAR_CHAR_VAL_FK2" label="Characteristic Value FK2" resourceId="JoinTree_1.CI_PREM_CHAR.CHAR_VAL_FK2"></item>
        <item id="CI_PREM_CHAR_CHAR_VAL_FK3" label="Characteristic Value FK3" resourceId="JoinTree_1.CI_PREM_CHAR.CHAR_VAL_FK3"></item>
        <item id="CI_PREM_CHAR_CHAR_VAL_FK4" label="Characteristic Value FK4" resourceId="JoinTree_1.CI_PREM_CHAR.CHAR_VAL_FK4"></item>
        <item id="CI_PREM_CHAR_CHAR_VAL_FK5" label="Characteristic Value FK5" resourceId="JoinTree_1.CI_PREM_CHAR.CHAR_VAL_FK5"></item>
        <item id="CI_PREM_CHAR_VERSION" label="Characteristic Version" resourceId="JoinTree_1.CI_PREM_CHAR.VERSION"></item>
      </items>
    </itemGroup>"""


def validate_schema(path: Path) -> None:
    validator = REPO / "scripts/jaspersoft/validate_domain_schema.py"
    result = subprocess.run(
        [sys.executable, str(validator), str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"schema validation failed:\n{result.stdout}\n{result.stderr}")


def _datasource_id(schema: str) -> str:
    ids = sorted(set(re.findall(r'<jdbcDataSource id="([^"]+)"', schema)))
    if len(ids) != 1:
        raise SystemExit(f"expected exactly one datasource id in the source schema, found {ids}")
    return ids[0]


def patch_schema(schema: str) -> str:
    if MARKER in schema:
        return schema
    ds = _datasource_id(schema)

    anchor_join = (
        '<join expr="CI_SA.CHAR_PREM_ID == CI_PREM.PREM_ID" left="CI_SA" right="CI_PREM" '
        'type="leftOuter" weight="1"></join>'
    )
    if anchor_join not in schema:
        raise SystemExit("expected CI_SA -> CI_PREM join anchor not found")
    schema = schema.replace(anchor_join, anchor_join + JOINS)

    anchor_ref = (
        '<tableRef alwaysIncludeTable="false" tableAlias="CI_PREM" tableId="CI_PREM"></tableRef>'
    )
    if anchor_ref not in schema:
        raise SystemExit("expected CI_PREM tableRef anchor not found")
    schema = schema.replace(anchor_ref, anchor_ref + TABLE_REFS)

    anchor_jt_fields = (
        '<field id="CI_PREM.PREM_DATA_AREA" type="java.lang.String"></field>'
    )
    if anchor_jt_fields not in schema:
        raise SystemExit("expected CI_PREM.PREM_DATA_AREA join-tree field anchor not found")
    schema = schema.replace(anchor_jt_fields, anchor_jt_fields + JOIN_TREE_FIELDS)

    anchor_formula = (
        '<field id="SA_CHAR_DIST" dataSetExpression="CountDistinct(Concatenate(CI_SA_CHAR.SA_ID, '
        "'_', CI_SA_CHAR.CHAR_TYPE_CD, '_', CI_SA_CHAR.EFFDT), 'Current')\" type=\"java.lang.Long\"></field>"
    )
    if anchor_formula not in schema:
        raise SystemExit("expected SA_CHAR_DIST formula field anchor not found")
    schema = schema.replace(anchor_formula, anchor_formula + FORMULA_FIELD)

    anchor_item = (
        '<item id="SA_CHAR_DIST" label="Distinct Service Agreement Characteristic" '
        'resourceId="JoinTree_1.SA_CHAR_DIST"></item>'
    )
    if anchor_item not in schema:
        raise SystemExit("expected SA_CHAR_DIST formula item anchor not found")
    schema = schema.replace(anchor_item, anchor_item + FORMULA_ITEM)

    sa_char_close = (
        '        <item id="CI_SA_CHAR_VERSION" label="Characteristic Version" '
        'resourceId="JoinTree_1.CI_SA_CHAR.VERSION"></item>\n'
        "      </items>\n"
        "    </itemGroup>\n"
        "  </itemGroups>"
    )
    if sa_char_close not in schema:
        raise SystemExit("expected end of 2.0 Service Agreement Characteristics itemGroup anchor not found")
    schema = schema.replace(
        sa_char_close,
        '        <item id="CI_SA_CHAR_VERSION" label="Characteristic Version" '
        'resourceId="JoinTree_1.CI_SA_CHAR.VERSION"></item>\n'
        "      </items>\n"
        "    </itemGroup>"
        + ITEM_GROUP
        + "\n  </itemGroups>",
    )

    join_tree_anchor = f'    <jdbcTable id="JoinTree_1" datasourceId="{ds}"'
    if join_tree_anchor not in schema:
        raise SystemExit("expected JoinTree_1 jdbcTable anchor not found")
    tables = (PREM_CHAR_TABLE + CHAR_TYPE_L_2_TABLE + CHAR_VAL_L_2_TABLE).replace(DS_PLACEHOLDER, ds)
    schema = schema.replace(join_tree_anchor, tables + join_tree_anchor)

    from patch_domain_characteristics import patch as derive_characteristics
    return derive_characteristics(schema)


def extract_from_zip(source_zip: Path) -> tuple[str, str]:
    with zipfile.ZipFile(source_zip) as zf:
        schema_path = next(
            n for n in zf.namelist() if n.endswith(f"{DOMAIN_NAME}_files/schema.data")
        )
        xml_path = next(n for n in zf.namelist() if n.endswith(f"{DOMAIN_NAME}.xml"))
        return zf.read(schema_path).decode("utf-8"), zf.read(xml_path).decode("utf-8")


def write_import_bundle(schema: str, domain_xml: str, out_root: Path) -> Path:
    staging = out_root / "_import_staging"
    if staging.exists():
        shutil.rmtree(staging)
    files_dir = staging / "resources/SmartCity/Report/Standard_Offering/Customer_Operations/Service_Agreements"
    files_dir.mkdir(parents=True, exist_ok=True)
    (files_dir / f"{DOMAIN_NAME}_files").mkdir(parents=True, exist_ok=True)
    (files_dir / f"{DOMAIN_NAME}_files/schema.data").write_text(schema, encoding="utf-8")
    (files_dir / f"{DOMAIN_NAME}.xml").write_text(domain_xml, encoding="utf-8")
    folder_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<folder exportedWithPermissions="false">
    <folder>{FOLDER}</folder>
    <name>Service_Agreements</name>
    <version>1</version>
    <label>Service_Agreements</label>
</folder>
"""
    (files_dir / ".folder.xml").write_text(folder_xml, encoding="utf-8")
    index_xml = """<?xml version="1.0" encoding="UTF-8"?>
<export exportedWithPermissions="false">
    <moduleId>repositoryResource</moduleId>
    <label>Repository Resource</label>
</export>
"""
    (staging / "index.xml").write_text(index_xml, encoding="utf-8")

    out_zip = out_root / f"{DOMAIN_NAME}_prem_char_{_datasource_id(schema)}_import.zip"
    if out_zip.exists():
        out_zip.unlink()
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(staging.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(staging).as_posix())

    schema_out = out_root / f"{DOMAIN_NAME}_files/schema.data"
    schema_out.parent.mkdir(parents=True, exist_ok=True)
    schema_out.write_text(schema, encoding="utf-8")
    (out_root / f"{DOMAIN_NAME}.xml").write_text(domain_xml, encoding="utf-8")
    return out_zip


def load_source_schema(source_schema: Path, source_zip: Path | None) -> tuple[str, str]:
    """A zip supplies BOTH the schema and the wrapper: pairing a reference schema from one
    tenant with a wrapper from another produced a bundle whose tables sat on Origin_DEV_DS
    while the wrapper pointed at /DataSource/Newark1_DS."""
    if source_zip and source_zip.is_file():
        return extract_from_zip(source_zip)
    if source_schema.is_file():
        return source_schema.read_text(encoding="utf-8"), ""
    raise SystemExit(f"source schema not found: {source_schema}")


def check_wrapper_matches(schema: str, domain_xml: str) -> None:
    ds = _datasource_id(schema)
    m = re.search(r"<uri>/DataSource/([^<]+)</uri>", domain_xml)
    if not m or m.group(1) != ds:
        raise SystemExit(f"wrapper references {m.group(1) if m else 'no datasource'} but the schema is on {ds}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-schema", type=Path, default=DEFAULT_SOURCE_SCHEMA)
    parser.add_argument("--source-zip", type=Path, default=None)
    parser.add_argument("--out-root", type=Path, default=OUT_ROOT)
    parser.add_argument(
        "--downloads-xml",
        type=Path,
        default=Path.home() / "Downloads" / "Service_Agreement___Domain_schema_fixed.xml",
    )
    args = parser.parse_args()

    schema_raw, domain_xml = load_source_schema(args.source_schema, args.source_zip)
    schema = patch_schema(schema_raw)

    args.out_root.mkdir(parents=True, exist_ok=True)
    schema_out = args.out_root / f"{DOMAIN_NAME}_files/schema.data"
    schema_out.parent.mkdir(parents=True, exist_ok=True)
    schema_out.write_text(schema, encoding="utf-8")
    args.downloads_xml.parent.mkdir(parents=True, exist_ok=True)
    args.downloads_xml.write_text(schema, encoding="utf-8")

    out_zip: Path | None = None
    if domain_xml:
        check_wrapper_matches(schema, domain_xml)
        out_zip = write_import_bundle(schema, domain_xml, args.out_root)
    validate_schema(schema_out)
    print(f"Schema: {schema_out}")
    print(f"Downloads: {args.downloads_xml}")
    if out_zip:
        print(f"Import zip: {out_zip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
