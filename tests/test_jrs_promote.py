"""jrs_promote: an org-to-org promotion package built offline from ROOT export shapes. The scope
lands under the destination folder with every path rewritten, the datasource is the target's own,
nothing of the source org or its database survives, and each check catches what it claims to."""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/jaspersoft"))
import jrs_promote as p  # noqa: E402

SRC, TGT = p.org_root("Origin_DEV"), p.org_root("Odessa")
FIN = "/SmartCity/Report/Standard_Offering/Finance"
DOMAIN, REPORT, VIEW = f"{FIN}/Adjustments/Adjustment_AP_Request___Domain", f"{FIN}/adj_ap_requests_control", f"{FIN}/Adjustments/Adjustment___Cancelation_Reason"


def index(keyalias: str, enc: str, entries: str) -> str:
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<export>'
            f'<property name="keyalias" value="{keyalias}"/><module id="repositoryResources">{entries}</module>'
            '<module id="favorites"/><property name="pathProcessorId" value="zip"/><property name="rootTenantId" value="organizations"/>'
            f'<property name="jsVersion" value="10.0.0 PRO"/><property name="encrypted" value="{enc}"/></export>')


def source_export() -> dict[str, bytes]:
    files = {
        "index.xml": index("k-src", "ENC-SRC", f"<resource>{SRC}{DOMAIN}</resource><resource>{SRC}{REPORT}</resource><resource>{SRC}{VIEW}</resource>"),
        f"resources{SRC}/DataSource/Origin_DEV_DS.xml": f"<jdbcDataSource><folder>{SRC}/DataSource</folder><name>Origin_DEV_DS</name><connectionUrl>jdbc:oracle:thin:@src-db-host:1521/ptestdb_ellensburg</connectionUrl><connectionPassword>SRCPW</connectionPassword></jdbcDataSource>",
        f"resources{SRC}{DOMAIN}.xml": (f"<semanticLayerDataSource><folder>{SRC}{FIN}/Adjustments</folder><name>Adjustment_AP_Request___Domain</name><version>3</version>"
                                        f"<schema><localResource><folder>{SRC}{DOMAIN}_files</folder><name>schema</name></localResource></schema>"
                                        f"<dataSource><alias>Origin_DEV_DS</alias><dataSourceReference><uri>{SRC}/DataSource/Origin_DEV_DS</uri></dataSourceReference></dataSource></semanticLayerDataSource>"),
        f"resources{SRC}{DOMAIN}_files/schema.data": '<schema><resources><jdbcTable id="CI_ADJ" datasourceId="Origin_DEV_DS" tableName="CISADM.CI_ADJ"></jdbcTable></resources>'
                                                     '<itemGroups><itemGroup id="SET_REQ"><item id="AP_REQ_ID" resourceId="JoinTree_1.CI_ADJ_APREQ.AP_REQ_ID"></item></itemGroup></itemGroups>'
                                                     '<dataSources><jdbcDataSource id="Origin_DEV_DS"><schemaMap><entry key="CISADM" value="CISADM"></entry></schemaMap></jdbcDataSource></dataSources></schema>',
        f"resources{SRC}{REPORT}.xml": (f"<reportUnit><folder>{SRC}{FIN}</folder><name>adj_ap_requests_control</name>"
                                        f"<dataSource><dataSourceReference><uri>{SRC}/DataSource/Origin_DEV_DS</uri></dataSourceReference></dataSource>"
                                        f"<mainReport><localResource><folder>{SRC}{REPORT}_files</folder><name>main_jrxml</name></localResource></mainReport></reportUnit>"),
        f"resources{SRC}{REPORT}_files/main_jrxml.data": "<jasperReport><queryString>select 1 from cisadm.ci_adj_apreq</queryString></jasperReport>",
        f"resources{SRC}{VIEW}.xml": (f"<adhocDataView><folder>{SRC}{FIN}/Adjustments</folder><name>Adjustment___Cancelation_Reason</name>"
                                      f"<dataSource><dataSourceReference><uri>{SRC}{FIN}/General_Ledger/FT_and_GL_Snapshot___Domain</uri></dataSourceReference></dataSource></adhocDataView>"),
        f"resources{SRC}{VIEW}_files/stateXML.data": '<state><measure fieldName="FT_CORE.FT_ID" name="FT_CORE.FT_ID"></measure><queryField name="ADJ.ADJ_CAN_RSN_CD"></queryField> ADJ.STRAY_TOKEN</state>',
        f"resources{SRC}{FIN}/General_Ledger/FT_and_GL_Snapshot___Domain.xml": f"<semanticLayerDataSource><folder>{SRC}{FIN}/General_Ledger</folder><name>FT_and_GL_Snapshot___Domain</name></semanticLayerDataSource>",
        f"resources{SRC}{FIN}/General_Ledger/FT_and_GL_Snapshot___Domain_files/schema.data": '<schema><itemGroups><itemGroup id="FT_CORE"><item id="FT_ID"></item></itemGroup><itemGroup id="ADJ"><item id="ADJ_CAN_RSN_CD"></item></itemGroup></itemGroups></schema>',
    }
    return {n: d.encode() for n, d in files.items()}


def target_ds_export() -> dict[str, bytes]:
    return {
        "index.xml": index("k-tgt", "ENC-TGT", f"<resource>{TGT}/DataSource/Origin_DataVergence_DS</resource>").encode(),
        # a root export drags the ancestor chain along; none of it may travel (the org root folder is never re-imported)
        f"resources{TGT}/.folder.xml": f"<folder><parent>{p.ORGS.rstrip('/')}</parent><name>Odessa</name></folder>".encode(),
        f"resources{TGT}/DataSource/.folder.xml": f"<folder><parent>{TGT}</parent><name>DataSource</name></folder>".encode(),
        f"resources{TGT}/DataSource/Origin_DataVergence_DS.xml": (f"<jdbcDataSource><folder>{TGT}/DataSource</folder><name>Origin_DataVergence_DS</name>"
                                                                  "<connectionUrl>jdbc:oracle:thin:@tgt-db-host:1521/pdevdb_odessa</connectionUrl><connectionPassword>TGTPW</connectionPassword></jdbcDataSource>").encode(),
    }


def promotion(uris=(DOMAIN, REPORT), into=f"{FIN}/Adjustments"):
    src = source_export()
    scope = p.scope_names(src, "Origin_DEV", list(uris))
    mv = p.moves("Origin_DEV", "Odessa", list(uris), into, "Origin_DEV_DS", "Origin_DataVergence_DS")
    return src, scope, mv


class Scope:
    def test_scope_is_the_descriptor_and_its_files_only(self):
        src, scope, _ = promotion()
        assert scope == {f"resources{SRC}{DOMAIN}.xml", f"resources{SRC}{DOMAIN}_files/schema.data",
                         f"resources{SRC}{REPORT}.xml", f"resources{SRC}{REPORT}_files/main_jrxml.data"}

    def test_a_folder_scope_takes_everything_under_it(self):
        src = source_export()
        scope = p.scope_names(src, "Origin_DEV", [f"{FIN}/Adjustments"])
        assert f"resources{SRC}{VIEW}.xml" in scope and f"resources{SRC}{DOMAIN}_files/schema.data" in scope
        assert f"resources{SRC}{REPORT}.xml" not in scope

    def test_a_uri_that_is_a_prefix_of_another_does_not_swallow_it(self):
        src = source_export()
        src[f"resources{SRC}{FIN}/adj.xml"] = b"<reportUnit><name>adj</name></reportUnit>"
        assert p.scope_names(src, "Origin_DEV", [f"{FIN}/adj"]) == {f"resources{SRC}{FIN}/adj.xml"}


class Rewrite:
    def test_moves_put_the_resource_under_the_destination_and_swap_org_and_datasource(self):
        _, _, mv = promotion()
        text = p.rewrite(f"<folder>{SRC}{FIN}</folder><uri>{SRC}{REPORT}</uri><folder>{SRC}{REPORT}_files</folder>"
                         f"<uri>{SRC}/DataSource/Origin_DEV_DS</uri><alias>Origin_DEV_DS</alias> datasourceId=\"Origin_DEV_DS\" <uri>{SRC}{FIN}/Other</uri>",
                         mv, "Origin_DEV_DS", "Origin_DataVergence_DS")
        assert text == (f"<folder>{TGT}{FIN}</folder><uri>{TGT}{FIN}/Adjustments/adj_ap_requests_control</uri><folder>{TGT}{FIN}/Adjustments/adj_ap_requests_control_files</folder>"
                        f"<uri>{TGT}/DataSource/Origin_DataVergence_DS</uri><alias>Origin_DataVergence_DS</alias> datasourceId=\"Origin_DataVergence_DS\" <uri>{TGT}{FIN}/Other</uri>")

    def test_the_destination_descriptor_folder_is_the_destination(self):
        src, scope, mv = promotion()
        files = p.rewritten_scope(src, scope, mv, "Origin_DEV_DS", "Origin_DataVergence_DS")
        out = files[f"resources{TGT}{FIN}/Adjustments/adj_ap_requests_control.xml"].decode()
        assert f"<folder>{TGT}{FIN}/Adjustments</folder>" in out and "Origin_DEV" not in out
        assert f"<folder>{TGT}{FIN}/Adjustments/adj_ap_requests_control_files</folder>" in out

    def test_a_promoted_folder_names_its_new_parent(self):
        src = source_export()
        src[f"resources{SRC}{FIN}/Adjustments/.folder.xml"] = f"<folder><parent>{SRC}{FIN}</parent><name>Adjustments</name><resource>Adjustment___Cancelation_Reason</resource></folder>".encode()
        scope = p.scope_names(src, "Origin_DEV", [f"{FIN}/Adjustments"])
        mv = p.moves("Origin_DEV", "Odessa", [f"{FIN}/Adjustments"], "/SmartCity/Archive", "", "")
        files = p.rewritten_scope(src, scope, mv, "", "")
        assert f"<parent>{TGT}/SmartCity/Archive</parent>" in files[f"resources{TGT}/SmartCity/Archive/Adjustments/.folder.xml"].decode()
        assert f"<folder>{TGT}/SmartCity/Archive/Adjustments</folder>" in files[f"resources{TGT}/SmartCity/Archive/Adjustments/Adjustment___Cancelation_Reason.xml"].decode()

    def test_a_prefix_uri_does_not_rewrite_its_longer_sibling(self):
        mv = p.moves("Origin_DEV", "Odessa", [f"{FIN}/adj"], f"{FIN}/Adjustments", "A_DS", "B_DS")
        out = p.rewrite(f"<uri>{SRC}{FIN}/adj</uri><uri>{SRC}{FIN}/adj_ap_requests_control</uri>", mv, "A_DS", "B_DS")
        assert out == f"<uri>{TGT}{FIN}/Adjustments/adj</uri><uri>{TGT}{FIN}/adj_ap_requests_control</uri>"


class Datasources:
    def test_the_source_datasource_is_read_from_the_scope(self):
        src, scope, _ = promotion()
        assert p.datasources_in(src, scope) == {"Origin_DEV_DS"}

    def test_a_view_on_a_domain_names_no_datasource_of_its_own(self):
        src = source_export()
        assert p.datasources_in(src, p.scope_names(src, "Origin_DEV", [VIEW])) == set()

    def test_the_target_datasource_is_read_from_its_export(self):
        assert p.datasources_in(target_ds_export(), set(target_ds_export())) == {"Origin_DataVergence_DS"}


class Package:
    def test_package_is_the_targets_datasource_plus_the_rewritten_scope(self):
        src, scope, mv = promotion()
        pkg = p.build_package(src, scope, target_ds_export(), mv, "Origin_DEV_DS", "Origin_DataVergence_DS", [], [f"{FIN}/Adjustments/Adjustment_AP_Request___Domain", f"{FIN}/Adjustments/adj_ap_requests_control"], "Odessa")
        z = zipfile.ZipFile(io.BytesIO(pkg)); names = z.namelist()
        assert names[-1] == "index.xml"
        assert f"resources{TGT}/DataSource/Origin_DataVergence_DS.xml" in names
        assert f"resources{TGT}{FIN}/Adjustments/adj_ap_requests_control.xml" in names
        assert f"resources{TGT}{FIN}/Adjustments/adj_ap_requests_control_files/main_jrxml.data" in names
        assert f"resources{TGT}{DOMAIN}_files/schema.data" in names
        assert not any("Origin_DEV" in n for n in names)
        assert not any(n.endswith("/.folder.xml") for n in names), "no ancestor folder travels"
        assert z.read(f"resources{TGT}/DataSource/Origin_DataVergence_DS.xml") == target_ds_export()[f"resources{TGT}/DataSource/Origin_DataVergence_DS.xml"]
        schema = z.read(f"resources{TGT}{DOMAIN}_files/schema.data").decode()
        assert 'datasourceId="Origin_DataVergence_DS"' in schema and "Origin_DEV" not in schema
        idx = z.read("index.xml").decode()
        assert idx.index("/DataSource/Origin_DataVergence_DS") < idx.index("adj_ap_requests_control")
        assert 'keyalias" value="k-tgt"' in idx and 'encrypted" value="ENC-TGT"' in idx and 'rootTenantId" value="organizations"' in idx
        assert f"<resource>{TGT}{FIN}/Adjustments/adj_ap_requests_control</resource>" in idx
        assert "<folder>" not in idx
        assert 'jdbcDataSource id="Origin_DataVergence_DS"' in schema

    def test_missing_destination_folders_are_created_and_existing_ones_left_alone(self):
        src, scope, mv = promotion(into=f"{FIN}/Adjustments/New_Sub")
        pkg = p.build_package(src, scope, target_ds_export(), mv, "Origin_DEV_DS", "Origin_DataVergence_DS", [f"{FIN}/Adjustments/New_Sub"], [f"{FIN}/Adjustments/New_Sub/adj_ap_requests_control"], "Odessa")
        z = zipfile.ZipFile(io.BytesIO(pkg)); names = z.namelist()
        assert f"resources{TGT}{FIN}/Adjustments/New_Sub/.folder.xml" in names
        assert f"resources{TGT}{FIN}/Adjustments/.folder.xml" not in names
        folder = z.read(f"resources{TGT}{FIN}/Adjustments/New_Sub/.folder.xml").decode()
        assert f"<parent>{TGT}{FIN}/Adjustments</parent>" in folder and "<label>New Sub</label>" in folder
        assert f"<folder>{TGT}{FIN}/Adjustments/New_Sub</folder>" in z.read("index.xml").decode()

    def test_verify_passes_a_clean_package_and_names_what_survives(self):
        src, scope, mv = promotion()
        pkg = p.build_package(src, scope, target_ds_export(), mv, "Origin_DEV_DS", "Origin_DataVergence_DS", [], [DOMAIN], "Odessa")
        assert p.verify_package(pkg, target_ds_export(), "Origin_DEV", "Origin_DEV_DS", "src-db-host", "Origin_DataVergence_DS") == []
        assert not any("host" in x for x in p.verify_package(pkg, target_ds_export(), "Origin_DEV", "Origin_DEV_DS", "tgt-db-host", "Origin_DataVergence_DS")), "the target's own host is not foreign (Origin_DEV_DS points at Ellensburg's database)"
        pkg2 = p.build_package(src, scope, {**target_ds_export(), f"resources{TGT}/DataSource/Origin_DataVergence_DS.xml": target_ds_export()[f"resources{TGT}/DataSource/Origin_DataVergence_DS.xml"].replace(b"pdevdb_odessa", b"pdevdb_odessa src-db-host")}, mv, "Origin_DEV_DS", "Origin_DataVergence_DS", [], [DOMAIN], "Odessa")
        assert any("src-db-host" in x for x in p.verify_package(pkg2, target_ds_export(), "Origin_DEV", "Origin_DEV_DS", "src-db-host", "Origin_DataVergence_DS")), "a foreign host inside the package is caught"
        assert any("Origin_DataVergence_DS" in x for x in p.verify_package(pkg, target_ds_export(), "Origin_DEV", "Origin_DEV_DS", "src-db-host", "Other_DS"))
        assert any("Odessa" in x for x in p.verify_package(pkg, target_ds_export(), "Odessa", "Origin_DEV_DS", "src-db-host", "Origin_DataVergence_DS"))
        assert any("datasource" in x.lower() for x in p.verify_package(pkg, {"index.xml": b""}, "Origin_DEV", "Origin_DEV_DS", "src-db-host", "Origin_DataVergence_DS"))


class SameOrgAcrossServers:
    def test_the_org_path_guard_does_not_fire_when_source_and_target_are_the_same_org(self):
        src = source_export()
        scope = p.scope_names(src, "Origin_DEV", [DOMAIN])
        mv = p.moves("Origin_DEV", "Origin_DEV", [DOMAIN], None, "Origin_DEV_DS", "Origin_DEV_DS")
        tgt = {"index.xml": target_ds_export()["index.xml"], f"resources{SRC}/DataSource/Origin_DEV_DS.xml": src[f"resources{SRC}/DataSource/Origin_DEV_DS.xml"]}
        pkg = p.build_package(src, scope, tgt, mv, "Origin_DEV_DS", "Origin_DEV_DS", [], [DOMAIN], "Origin_DEV")
        assert p.verify_package(pkg, tgt, "Origin_DEV", "Origin_DEV_DS", "src-db-host", "Origin_DEV_DS", "Origin_DEV") == []
        assert any("survives" in x for x in p.verify_package(pkg, tgt, "Origin_DEV", "Origin_DEV_DS", "src-db-host", "Origin_DEV_DS", "Odessa"))


class NestedGroups:
    def test_items_pair_with_their_direct_group_when_groups_nest(self):
        schema = ('<schema xmlns="http://www.jaspersoft.com/2007/SL/XMLSchema" version="1.3"><itemGroups>'
                  '<itemGroup id="CI_BILL" label="Bill"><itemGroups><itemGroup id="CI_BILL_SA_1" label="Bill SA"><items>'
                  '<item id="CUR_AMT_1" label="Current Amount" resourceId="JoinTree_1.CI_BILL_SA.CUR_AMT"></item></items></itemGroup></itemGroups>'
                  '<items><item id="BILL_DT" label="Bill Date" resourceId="JoinTree_1.CI_BILL.BILL_DT"></item></items></itemGroup></itemGroups></schema>')
        items = p.domain_items({"resources/x/D_files/schema.data": schema.encode()})["resources/x/D"]
        assert items == {"CI_BILL.BILL_DT", "CI_BILL.CI_BILL_SA_1.CUR_AMT_1"}, "the full group path, as the engine names the item"


class Metadata:
    def test_levels_come_from_groups_or_the_root_itself(self):
        grouped = {"rootLevel": {"id": "root", "subLevels": [{"id": "A", "items": [{"id": "X"}]}]}}
        flat = {"rootLevel": {"id": "root", "items": [{"id": "X"}, {"id": "Y"}]}}
        assert [l["id"] for l in p.domain_levels(grouped)] == ["A"]
        assert [l["id"] for l in p.domain_levels(flat)] == ["root"] and len(p.domain_levels(flat)[0]["items"]) == 2
        assert p.probe_fields(grouped) == ["A.X"] and p.probe_fields(flat) == ["X", "Y"], "a group-less domain is queried by bare item id"


class Hosts:
    def test_both_jdbc_url_forms_yield_the_host(self):
        plain = {"resources/x/DataSource/A.xml": b"<jdbcDataSource><connectionUrl>jdbc:oracle:thin:@10.13.4.91:1521/ptestdb_ellensburg</connectionUrl></jdbcDataSource>"}
        slashed = {"resources/x/DataSource/B.xml": b"<jdbcDataSource><connectionUrl>jdbc:oracle:thin:@//10.13.4.91:1521/ptestdb_citycorp.testvcn</connectionUrl></jdbcDataSource>"}
        assert p.db_host(plain) == "10.13.4.91" and p.db_host(slashed) == "10.13.4.91"


class Dependencies:
    def test_references_outside_the_package_are_named_on_the_target_side(self):
        src = source_export()
        scope = p.scope_names(src, "Origin_DEV", [VIEW])
        mv = p.moves("Origin_DEV", "Odessa", [VIEW], f"{FIN}/Adjustments", "", "")
        deps = p.external_references(src, scope, mv, "", "", "Odessa")
        assert deps == {f"{TGT}{FIN}/General_Ledger/FT_and_GL_Snapshot___Domain"}

    def test_the_datasource_and_the_scope_itself_are_not_external(self):
        src, scope, mv = promotion()
        assert p.external_references(src, scope, mv, "Origin_DEV_DS", "Origin_DataVergence_DS", "Odessa") == set()

    def test_view_fields_are_checked_against_the_targets_domain_items(self):
        src = source_export()
        scope = p.scope_names(src, "Origin_DEV", [VIEW])
        assert p.unresolved_fields(src, scope, {"FT_CORE.FT_ID", "ADJ.ADJ_CAN_RSN_CD"}) == set()
        assert p.unresolved_fields(src, scope, {"FT_CORE.FT_ID"}) == {"ADJ.ADJ_CAN_RSN_CD"}


class After:
    def test_after_compare_ignores_what_the_importer_rewrites(self):
        pkg = {f"resources{TGT}{DOMAIN}.xml": b"<semanticLayerDataSource>\n  <version>0</version><label>A</label></semanticLayerDataSource>"}
        after = {f"resources{TGT}{DOMAIN}.xml": b"<semanticLayerDataSource><version>7</version><updateDate>2026-09-24T00:00:00.000Z</updateDate><label>A</label></semanticLayerDataSource>"}
        assert p.after_problems(after, pkg) == []
        after[f"resources{TGT}{DOMAIN}.xml"] = b"<semanticLayerDataSource><label>B</label></semanticLayerDataSource>"
        assert p.after_problems(after, pkg) == [f"differs after import: resources{TGT}{DOMAIN}.xml"]
        assert p.after_problems({}, pkg) == [f"missing after import: resources{TGT}{DOMAIN}.xml"]


for cls in (Scope, Rewrite, Datasources, Package, SameOrgAcrossServers, NestedGroups, Metadata, Hosts, Dependencies, After):
    globals()["Test" + cls.__name__] = type("Test" + cls.__name__, (cls,), {})
