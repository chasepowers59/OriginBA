#!/usr/bin/env python3
"""
Build an importable native Jaspersoft dashboard package for snapshot-backed
financial operations monitoring.

The package assumes Standard_Offering has already been imported and the
snapshot-backed Finance/Financial_Transaction Ad Hoc views already exist.
"""

from __future__ import annotations

import argparse
import json
import shutil
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


ORG_ROOT = "/organizations/organization_1/organizations/Origin_DEV"
REPORT_ROOT = f"{ORG_ROOT}/SmartCity/Report"
FT_FOLDER_URI = f"{REPORT_ROOT}/Standard_Offering/Finance/Financial_Transaction"
FT_FOLDER_MEMBER = (
    "resources/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/"
    "Standard_Offering/Finance/Financial_Transaction/.folder.xml"
)

DASHBOARD_NAME = "Financial_Operations___Dashboard"
DASHBOARD_LABEL = "Financial Operations - Dashboard"
DASHBOARD_DESCRIPTION = (
    "Snapshot-backed finance operations dashboard for billed revenue, posting "
    "status, transaction mix, and bill-cycle monitoring."
)

VIEWS = [
    {
        "name": "Financial_Transaction___Billed_Revenue_Trend",
        "component_id": "Revenue_Trend",
        "title": "Billed Revenue Trend",
        "show_export": True,
        "layout": {"x": 0, "y": 5, "width": 20, "height": 10},
    },
    {
        "name": "Financial_Transaction___Distribution_Status",
        "component_id": "GL_Distribution_Status",
        "title": "GL Distribution Status",
        "show_export": True,
        "layout": {"x": 20, "y": 5, "width": 20, "height": 10},
    },
    {
        "name": "Financial_Transaction___Total_Transactions_by_Type",
        "component_id": "Transactions_by_Type",
        "title": "Transactions by Type",
        "show_export": True,
        "layout": {"x": 0, "y": 15, "width": 13, "height": 10},
    },
    {
        "name": "Billed_Revenue_by_Customer_Class",
        "component_id": "Revenue_by_Customer_Class",
        "title": "Revenue by Customer Class",
        "show_export": True,
        "layout": {"x": 13, "y": 15, "width": 13, "height": 10},
    },
    {
        "name": "Financial_Transaction___Bill_Cycle_FT_Health",
        "component_id": "Bill_Cycle_Transactions",
        "title": "Bill Cycle Transaction Health",
        "show_export": True,
        "layout": {"x": 26, "y": 15, "width": 14, "height": 10},
    },
    {
        "name": "Financial_Transactions___Service_Type_FT_Summary",
        "component_id": "Service_Type_Summary",
        "title": "Service Type FT Summary",
        "show_export": True,
        "layout": {"x": 0, "y": 25, "width": 40, "height": 11},
    },
]

FILTERS = [
    {
        "name": "ACCOUNTING_DT_1",
        "label": "Accounting Date is on or after",
        "position": 1,
        "owner_view": "Financial_Transaction___Billed_Revenue_Trend",
        "owner_label": "Accounting Date is between",
        "consumers": [view["component_id"] for view in VIEWS],
    },
    {
        "name": "ACCOUNTING_DT_2",
        "label": "Accounting Date is on or before",
        "position": 2,
        "owner_view": "Financial_Transaction___Billed_Revenue_Trend",
        "owner_label": "and",
        "consumers": ["Revenue_Trend", "Revenue_by_Customer_Class"],
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the snapshot financial operations dashboard package.")
    parser.add_argument(
        "--standard-offering-zip",
        default="/Users/chase/OriginBA-3/deploy/jaspersoft_standard_offering/Standard_Offering_import.zip",
        help="Path to the curated Standard_Offering import ZIP.",
    )
    parser.add_argument(
        "--outdir",
        default="/Users/chase/OriginBA-3/deploy/native_dashboard_pack_v1",
        help="Output directory for the dashboard package.",
    )
    return parser.parse_args()


def decode_bytes(data: bytes) -> str:
    for encoding in ("utf-8", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Unable to decode file content.")


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def dashboard_member_path(name: str) -> str:
    return (
        "resources/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/"
        f"Standard_Offering/Finance/Financial_Transaction/{name}"
    )


def view_uri(name: str) -> str:
    return f"{FT_FOLDER_URI}/{name}"


def parse_view_metadata(archive: zipfile.ZipFile) -> dict[str, dict[str, object]]:
    metadata: dict[str, dict[str, object]] = {}
    for view in VIEWS:
        name = view["name"]
        member = dashboard_member_path(f"{name}.xml")
        root = ET.fromstring(archive.read(member))
        params: list[dict[str, str]] = []
        for control in root.findall("inputControl"):
            local = control.find("localResource")
            if local is None:
                continue
            params.append(
                {
                    "id": local.findtext("name") or "",
                    "label": local.findtext("label") or "",
                    "uri": view_uri(name),
                }
            )
        metadata[name] = {
            "label": root.findtext("label") or name,
            "description": root.findtext("description") or "",
            "params": params,
        }
    return metadata


def updated_folder_xml(original: str) -> str:
    root = ET.fromstring(original)
    existing = [node.text for node in root.findall("resource") if node.text]
    if DASHBOARD_NAME not in existing:
        resource_node = ET.Element("resource")
        resource_node.text = DASHBOARD_NAME
        root.append(resource_node)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")


def build_dashboard_xml() -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<dashboardModelResource exportedWithPermissions="true">',
        f"    <folder>{FT_FOLDER_URI}</folder>",
        f"    <name>{DASHBOARD_NAME}</name>",
        "    <version>0</version>",
        f"    <label>{DASHBOARD_LABEL}</label>",
        f"    <description>{DASHBOARD_DESCRIPTION}</description>",
        "    <creationDate>2026-04-24T20:00:00.000Z</creationDate>",
        "    <updateDate>2026-04-24T20:00:00.000Z</updateDate>",
        "    <defaultFoundation>default</defaultFoundation>",
        "    <foundation>",
        "        <id>default</id>",
        "        <layout>layout</layout>",
        "        <wiring>wiring</wiring>",
        "        <components>components</components>",
        "    </foundation>",
        "    <resourceDescriptor><type>wiring</type><id>wiring</id></resourceDescriptor>",
        "    <resourceDescriptor><type>layout</type><id>layout</id></resourceDescriptor>",
        "    <resourceDescriptor><type>components</type><id>components</id></resourceDescriptor>",
    ]
    for view in VIEWS:
        lines.append(
            f"    <resourceDescriptor><type>adhocDataView</type><id>{view_uri(view['name'])}</id></resourceDescriptor>"
        )
    for control in FILTERS:
        lines.append(
            "    <resourceDescriptor>"
            "<type>inputControl</type>"
            f"<id>{view_uri(control['owner_view'])}_files/{control['name']}</id>"
            "</resourceDescriptor>"
        )
    lines.extend(
        [
            "    <resource>",
            '        <localResource xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'exportedWithPermissions="false" dataFile="wiring.data" xsi:type="fileResource">',
            f"            <folder>{FT_FOLDER_URI}/{DASHBOARD_NAME}_files</folder>",
            "            <name>wiring</name>",
            "            <version>0</version>",
            "            <label>wiring</label>",
            "            <creationDate>2026-04-24T20:00:00.000Z</creationDate>",
            "            <updateDate>2026-04-24T20:00:00.000Z</updateDate>",
            "            <fileType>json</fileType>",
            "        </localResource>",
            "    </resource>",
            "    <resource>",
            '        <localResource xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'exportedWithPermissions="false" dataFile="layout" xsi:type="contentResource">',
            f"            <folder>{FT_FOLDER_URI}/{DASHBOARD_NAME}_files</folder>",
            "            <name>layout</name>",
            "            <version>0</version>",
            "            <label>layout</label>",
            "            <creationDate>2026-04-24T20:00:00.000Z</creationDate>",
            "            <updateDate>2026-04-24T20:00:00.000Z</updateDate>",
            "            <fileType>html</fileType>",
            "        </localResource>",
            "    </resource>",
            "    <resource>",
            '        <localResource xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            'exportedWithPermissions="false" dataFile="components.data" xsi:type="fileResource">',
            f"            <folder>{FT_FOLDER_URI}/{DASHBOARD_NAME}_files</folder>",
            "            <name>components</name>",
            "            <version>0</version>",
            "            <label>components</label>",
            "            <creationDate>2026-04-24T20:00:00.000Z</creationDate>",
            "            <updateDate>2026-04-24T20:00:00.000Z</updateDate>",
            "            <fileType>dashboardComponent</fileType>",
            "        </localResource>",
            "    </resource>",
        ]
    )
    for view in VIEWS:
        lines.extend(["    <resource>", f"        <uri>{view_uri(view['name'])}</uri>", "    </resource>"])
    for control in FILTERS:
        lines.extend(
            [
                "    <resource>",
                '        <localResource xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
                'exportedWithPermissions="false" xsi:type="inputControl">',
                f"            <folder>{FT_FOLDER_URI}/{DASHBOARD_NAME}_files</folder>",
                f"            <name>{control['name']}</name>",
                "            <version>0</version>",
                f"            <label>{control['label']}</label>",
                "            <creationDate>2026-04-24T20:00:00.000Z</creationDate>",
                "            <updateDate>2026-04-24T20:00:00.000Z</updateDate>",
                "            <type>2</type>",
                "            <mandatory>false</mandatory>",
                "            <readOnly>false</readOnly>",
                "            <visible>true</visible>",
                "            <dataType>",
                '                <localResource exportedWithPermissions="false" xsi:type="dataType">',
                f"                    <folder>{FT_FOLDER_URI}/{DASHBOARD_NAME}_files/{control['name']}_files</folder>",
                "                    <name>timestamp</name>",
                "                    <version>0</version>",
                "                    <label>Timestamp</label>",
                "                    <creationDate>2026-04-24T20:00:00.000Z</creationDate>",
                "                    <updateDate>2026-04-24T20:00:00.000Z</updateDate>",
                "                    <type>4</type>",
                "                    <strictMin>false</strictMin>",
                "                    <strictMax>false</strictMax>",
                "                </localResource>",
                "            </dataType>",
                "        </localResource>",
                "    </resource>",
            ]
        )
    lines.append("</dashboardModelResource>")
    lines.append("")
    return "\n".join(lines)


def build_components_data(view_meta: dict[str, dict[str, object]]) -> str:
    components: list[dict[str, object]] = [
        {
            "id": "DashboardProperties",
            "type": "dashboardProperties",
            "name": "DashboardProperties",
            "autoRefresh": False,
            "refreshInterval": 5,
            "refreshIntervalUnit": "minute",
            "showDashletBorders": True,
            "showExportButton": False,
            "dashletMargin": 6,
            "dashletPadding": 8,
            "dashletFilterShowPopup": True,
            "useFixedSize": False,
            "fixedWidth": 1440,
            "fixedHeight": 900,
            "canvasColor": "#f4f1ea",
            "titleBarColor": "rgba(0, 0, 0, 0)",
            "titleTextColor": "#1f2a37",
        },
        {
            "type": "text",
            "label": "Title",
            "exposeOutputsToFilterManager": False,
            "dashletHyperlinkTarget": "",
            "id": "Dashboard_Title",
            "name": "Dashboard Title",
            "alignment": "left",
            "verticalAlignment": "top",
            "bold": True,
            "text": "Financial Operations Dashboard",
            "italic": False,
            "underline": False,
            "font": "Aptos",
            "size": 18,
            "color": "#102a43",
            "backgroundColor": "rgba(0, 0, 0, 0)",
            "scaleToFit": "container",
            "showDashletBorders": False,
            "borderColor": "#d6d3d1",
            "toolbar": None,
        },
        {
            "type": "text",
            "label": "Subtitle",
            "exposeOutputsToFilterManager": False,
            "dashletHyperlinkTarget": "",
            "id": "Dashboard_Subtitle",
            "name": "Dashboard Subtitle",
            "alignment": "left",
            "verticalAlignment": "top",
            "bold": False,
            "text": (
                "Use this snapshot-backed dashboard to review recent billed revenue, "
                "posting status, transaction mix, bill-cycle activity, and service-type "
                "financial volume without leaving the Finance workstream."
            ),
            "italic": False,
            "underline": False,
            "font": "Aptos",
            "size": 10,
            "color": "#334e68",
            "backgroundColor": "rgba(0, 0, 0, 0)",
            "scaleToFit": "container",
            "showDashletBorders": False,
            "borderColor": "#d6d3d1",
            "toolbar": None,
        },
    ]

    for view in VIEWS:
        meta = view_meta[view["name"]]
        components.append(
            {
                "type": "adhocDataView",
                "label": meta["label"],
                "resource": view_uri(view["name"]),
                "exposeOutputsToFilterManager": False,
                "dashletHyperlinkTarget": "",
                "id": view["component_id"],
                "name": view["title"],
                "scaleToFit": "width",
                "autoRefresh": True,
                "refreshInterval": 5,
                "refreshIntervalUnit": "minute",
                "showTitleBar": True,
                "showExportButton": view["show_export"],
                "showRefreshButton": True,
                "showMaximizeButton": True,
                "showBackButton": True,
                "enableAdhocDrilldown": True,
                "dataSourceUri": view_uri(view["name"]),
                "showVizSelectorIcon": False,
                "parameters": meta["params"],
                "showVizSelector": True,
            }
        )

    components.append(
        {
            "type": "filterGroup",
            "name": "Filter Group",
            "id": "Filter_Group",
            "filtersPerRow": 2,
            "buttonsPosition": "bottom",
            "applyButton": True,
            "resetButton": True,
            "floating": False,
            "toolbar": None,
        }
    )

    for control in FILTERS:
        components.append(
            {
                "type": "inputControl",
                "label": control["label"],
                "resourceId": control["name"],
                "resource": f"{view_uri(control['owner_view'])}_files/{control['name']}",
                "id": control["name"],
                "name": control["label"],
                "selected": False,
                "hovered": False,
                "interactive": True,
                "ownerResourceId": view_uri(control["owner_view"]),
                "ownerResourceParameterName": control["name"],
                "masterDependencies": [],
                "fullCollectionRequired": False,
                "parentId": "Filter_Group",
                "position": control["position"],
            }
        )

    return json.dumps(components, separators=(",", ":"))


def build_wiring_data() -> str:
    wiring: list[dict[str, object]] = [
        {
            "name": "@init",
            "producer": "DashboardProperties:@init",
            "component": "DashboardProperties",
            "consumers": [{"consumer": f"{view['component_id']}:@refresh"} for view in VIEWS],
        },
        {
            "name": "@applyParams",
            "producer": "DashboardProperties:@applyParams",
            "component": "DashboardProperties",
            "consumers": [{"consumer": f"{view['component_id']}:@applyParams"} for view in VIEWS],
        },
        {
            "name": "@refresh",
            "producer": "Filter_Group:@refresh",
            "component": "Filter_Group",
            "consumers": [{"consumer": f"{view['component_id']}:@applyParams"} for view in VIEWS],
        },
    ]

    for control in FILTERS:
        wiring.append(
            {
                "name": control["name"],
                "producer": f"{control['name']}:{control['name']}",
                "component": control["name"],
                "consumers": [{"consumer": f"{consumer}:{control['name']}"} for consumer in control["consumers"]],
            }
        )

    return json.dumps(wiring, separators=(",", ":"))


def build_layout() -> str:
    blocks = [
        ("Dashboard_Title", 0, 0, 24, 2),
        ("Dashboard_Subtitle", 0, 2, 24, 3),
        ("Filter_Group", 24, 0, 16, 5),
    ]
    for view in VIEWS:
        layout = view["layout"]
        blocks.append((view["component_id"], layout["x"], layout["y"], layout["width"], layout["height"]))
    return "".join(
        [
            f"<div data-componentId='{component_id}' data-x='{x}' data-y='{y}' "
            f"data-width='{width}' data-height='{height}'></div>"
            for component_id, x, y, width, height in blocks
        ]
    )


def build_index_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<export><module id=\"repositoryResources\">"
        f"<folder>{FT_FOLDER_URI}</folder>"
        "</module>"
        '<property name="pathProcessorId" value="zip" />'
        '<property name="rootTenantId" value="organizations" />'
        '<property name="jsVersion" value="8.1.0 PRO" />'
        "</export>\n"
    )


def build_manifest() -> dict[str, object]:
    return {
        "dashboard_name": DASHBOARD_NAME,
        "dashboard_label": DASHBOARD_LABEL,
        "target_folder_uri": FT_FOLDER_URI,
        "package_type": "native_dashboard_add_on",
        "business_use_case": (
            "Daily and month-to-date financial operations review using snapshot-backed "
            "billed revenue, posting status, transaction mix, bill-cycle activity, and "
            "service-type FT summary visuals."
        ),
        "shared_filters": [control["name"] for control in FILTERS],
        "dashlets": [
            {"title": view["title"], "resource_uri": view_uri(view["name"])}
            for view in VIEWS
        ],
        "prerequisite": "Standard_Offering_import.zip must already be imported into Origin_DEV.",
    }


def main() -> int:
    args = parse_args()
    source_zip = Path(args.standard_offering_zip).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()
    workspace = outdir / "_financial_operations_dashboard_build"

    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(source_zip) as archive:
        folder_xml_text = decode_bytes(archive.read(FT_FOLDER_MEMBER))
        view_meta = parse_view_metadata(archive)

    folder_target = workspace / FT_FOLDER_MEMBER
    ensure_parent(folder_target)
    folder_target.write_text(updated_folder_xml(folder_xml_text), encoding="utf-8")

    dashboard_xml_target = workspace / dashboard_member_path(f"{DASHBOARD_NAME}.xml")
    ensure_parent(dashboard_xml_target)
    dashboard_xml_target.write_text(build_dashboard_xml(), encoding="utf-8")

    dashboard_files_dir = workspace / dashboard_member_path(f"{DASHBOARD_NAME}_files")
    dashboard_files_dir.mkdir(parents=True, exist_ok=True)
    (dashboard_files_dir / "components.data").write_text(build_components_data(view_meta), encoding="utf-8")
    (dashboard_files_dir / "wiring.data").write_text(build_wiring_data(), encoding="utf-8")
    (dashboard_files_dir / "layout").write_text(build_layout(), encoding="utf-8")
    (workspace / "index.xml").write_text(build_index_xml(), encoding="utf-8")

    zip_path = outdir / "Financial_Operations_Dashboard_import.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(workspace.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(workspace).as_posix())

    manifest = build_manifest()
    (outdir / "Financial_Operations_Dashboard_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    print(zip_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
