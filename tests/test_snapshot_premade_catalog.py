"""Validate premade report fields exist in Domain XML / catalog fields."""

from __future__ import annotations

import json
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from snapshot_explorer_registry import PORTAL_SNAPSHOTS, SNAPSHOT_REGISTRY  # noqa: E402

DOMAIN_DIR = ROOT / "domains" / "exports" / "manual_imports"
CATALOG_PATH = ROOT / "output" / "snapshot_explorer_catalog.json"
NS = {"sl": "http://www.jaspersoft.com/2007/SL/XMLSchema"}


def domain_field_ids(table_name: str) -> set[str]:
    path = DOMAIN_DIR / f"{table_name}_End_User_Friendly.xml"
    if not path.exists():
        raise FileNotFoundError(path)
    root = ET.parse(path).getroot()
    ids: set[str] = set()
    for field_el in root.findall(".//sl:resources/sl:jdbcTable/sl:fieldList/sl:field", NS):
        field_id = field_el.get("id")
        if field_id:
            ids.add(field_id.upper())
    return ids


class PremadeCatalogValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not CATALOG_PATH.exists():
            raise unittest.SkipTest("Run scripts/build_snapshot_explorer_catalog.py first")
        cls.catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    def test_premade_dimensions_and_measures_in_domain(self) -> None:
        errors: list[str] = []
        for snap_id in PORTAL_SNAPSHOTS:
            meta = SNAPSHOT_REGISTRY.get(snap_id, {})
            premade = meta.get("premade_reports") or []
            if not premade:
                continue
            try:
                allowed = domain_field_ids(snap_id)
            except FileNotFoundError as exc:
                errors.append(str(exc))
                continue
            allowed.add("*")
            for report in premade:
                for dim in report.get("dimensions") or []:
                    if dim.upper() not in allowed:
                        errors.append(
                            f"{snap_id} report {report.get('id')}: invalid dimension {dim}"
                        )
                for measure in report.get("measures") or []:
                    field = str(measure.get("field", "*")).upper()
                    if field not in allowed:
                        errors.append(
                            f"{snap_id} report {report.get('id')}: invalid measure field {field}"
                        )
                for filt in report.get("filters") or []:
                    field = str(filt.get("field", "")).upper()
                    if field and field not in allowed:
                        errors.append(
                            f"{snap_id} report {report.get('id')}: invalid filter field {field}"
                        )
        if errors:
            self.fail("Premade catalog validation failed:\n" + "\n".join(errors))

    def test_scope_filters_in_domain(self) -> None:
        from snapshot_explorer_registry import SCOPE_FILTERS

        errors: list[str] = []
        for snap_id, filters in SCOPE_FILTERS.items():
            allowed = domain_field_ids(snap_id)
            for f in filters:
                field = f["field"].upper()
                if field not in allowed:
                    errors.append(f"{snap_id}: scope filter field {field} not in domain")
        if errors:
            self.fail("\n".join(errors))


if __name__ == "__main__":
    unittest.main()
