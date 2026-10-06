"""After a domain set is imported, the validator proves three things per domain: the server's fields equal
the generated definition, the domain returns the canvas's own row count, and every field executes."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "jaspersoft"))
import jrs_validate_domain_set as v  # noqa: E402

XML = """<schema xmlns="http://www.jaspersoft.com/2007/SL/XMLSchema" version="1.3">
  <dataIslands><itemGroup id="JOINTREE_1" label="Bill" resourceId="JOINTREE_1"></itemGroup></dataIslands>
  <itemGroups>
    <itemGroup id="GBill" label="Bill" resourceId="JOINTREE_1"><items>
      <item id="G_BILL_ID" label="Bill ID" resourceId="JOINTREE_1.BILL_ID"/>
      <item id="G_BILL_DATE" label="Bill Date" resourceId="JOINTREE_1.BILL_DATE"/>
    </items></itemGroup>
    <itemGroup id="GAmounts" label="Amounts &amp; Counts" resourceId="JOINTREE_1"><items>
      <item id="M_SA_COUNT" label="SA Count (Bill)" resourceId="JOINTREE_1.SA_COUNT_BILL"/>
    </items></itemGroup>
  </itemGroups>
</schema>"""


def test_generated_items_are_folder_and_label_per_item_id():
    assert v.generated_items(XML) == {"G_BILL_ID": ("Bill", "Bill ID"), "G_BILL_DATE": ("Bill", "Bill Date"),
                                      "M_SA_COUNT": ("Amounts & Counts", "SA Count (Bill)")}


def test_the_view_is_named_from_the_file_not_the_island():
    # an extended domain's island is a join tree, not the view
    assert v.view_for("originba_bill_domain.xml") == "RPT_BILL_BI"


def test_differences_are_reported_by_kind():
    want = {"A": ("F", "a"), "B": ("F", "b"), "C": ("F", "c")}
    got = {"A": ("F", "a"), "B": ("G", "b"), "D": ("F", "d")}
    assert v.differences(want, got) == {"missing": ["C"], "extra": ["D"], "relabelled": ["B"]}


def test_the_count_is_taken_on_the_grain_key_because_countall_skips_blanks():
    # matched on the item id, not the label: labels are spelled out ("FT" -> "Financial Transaction")
    got = {"G_PARENT_FT_ID": ("F", "Parent Financial Transaction ID"), "G_FT_ID": ("F", "Financial Transaction ID"),
           "G_AMOUNT": ("F", "Amount")}
    assert v.grain_item(got, "FT_ID") == "G_FT_ID"


def test_the_count_reads_from_the_dataset_rows():
    body = json.loads(json.dumps({"truncated": False, "totalCounts": 1, "dataset": {
        "fields": [{"reference": "n", "type": "long", "kind": "aggregation"}], "counts": 1, "rows": [["436"]]}}))
    assert v.count_from(body) == 436


def test_fields_execute_in_chunks_of_forty():
    chunks = list(v.chunks([f"g.f{i}" for i in range(95)]))
    assert [len(c) for c in chunks] == [40, 40, 15]


def test_never_writes():
    src = (ROOT / "scripts" / "jaspersoft" / "jrs_validate_domain_set.py").read_text()
    assert '"PUT"' not in src and '"DELETE"' not in src and "/rest_v2/import" not in src


def test_a_dropped_link_is_named_not_parsed():
    # _http returns code None and the exception text when the VPN or the server is gone
    assert v.answer(None, b"URLError(TimeoutError('timed out'))") == (None, "link down: URLError(TimeoutError('timed out'))")


def test_an_empty_or_failed_response_is_a_problem_not_a_crash():
    assert v.answer(200, b"") == (None, "HTTP 200: empty response")
    assert v.answer(500, b'{"message": "boom"}')[1] == "HTTP 500: boom"
    assert v.answer(200, b'{"a": 1}') == ({"a": 1}, None)


def test_a_failing_chunk_is_narrowed_to_the_fields_that_fail():
    def narrowed(bad, n):
        calls = []

        def run(fields):
            calls.append(fields)
            return not bad & set(fields)
        return v.failing_fields([f"g.f{i}" for i in range(n)], run), len(calls)
    assert narrowed({"g.f3", "g.f7"}, 10)[0] == ["g.f3", "g.f7"]
    found, calls = narrowed({"g.f29"}, 40)   # the real case: one bad field in a chunk of forty
    assert found == ["g.f29"] and calls < 15   # bisected, not one call per field


EXT_XML = """<schema xmlns="http://www.jaspersoft.com/2007/SL/XMLSchema" version="1.3">
  <resources>
    <jdbcQuery id="CHR_PREM_IN_OUT" datasourceId="DS"><fieldList><field id="KEY_ID" type="java.lang.String"/>
      <field id="CHAR_VALUE" type="java.lang.String"/></fieldList>
      <query>SELECT X.KEY_ID AS KEY_ID, X.CHAR_VALUE AS CHAR_VALUE FROM (SELECT 1 FROM DUAL WHERE A &lt;= B) X</query></jdbcQuery>
    <jdbcTable id="RPT_PREMISE_SP_BI" datasourceId="DS" datasourceTableName="RPT_PREMISE_SP_BI" schemaAlias="ORIGINBA_REPORTING"/>
    <joinedDataSetRef><joinString>join</joinString></joinedDataSetRef>
    <joinInfo alias="RPT_PREMISE_SP_BI" referenceId="RPT_PREMISE_SP_BI">
      <join expr="RPT_PREMISE_SP_BI.PREMISE_ID == CHR_PREM_IN_OUT.KEY_ID" left="RPT_PREMISE_SP_BI" right="CHR_PREM_IN_OUT" type="leftOuter" weight="1"/>
    </joinInfo>
  </resources>
  <itemGroups><itemGroup id="GChar" label="Characteristic" resourceId="JoinTree_1"><items>
    <item id="PS_CHR_PREM_IN_OUT" label="Inside/Outside City Limits" resourceId="JoinTree_1.CHR_PREM_IN_OUT.CHAR_VALUE"/>
    <item id="PS_PREMISE_ID" label="Premise ID" resourceId="JoinTree_1.RPT_PREMISE_SP_BI.PREMISE_ID"/>
  </items></itemGroup></itemGroups>
</schema>"""


def test_each_client_characteristic_is_paired_with_its_join_and_sql():
    (c,) = v.characteristic_checks(EXT_XML)
    assert c["item"] == "PS_CHR_PREM_IN_OUT" and c["view"] == "RPT_PREMISE_SP_BI" and c["column"] == "PREMISE_ID"
    assert c["sql"].startswith("SELECT X.KEY_ID") and "A <= B" in c["sql"]   # the XML escape is undone


def test_the_expected_count_is_canvas_rows_whose_key_finds_a_value():
    sql = v.expected_characteristic_sql({"sql": "SELECT 1 AS KEY_ID, 'x' AS CHAR_VALUE FROM DUAL",
                                         "view": "RPT_PREMISE_SP_BI", "column": "PREMISE_ID"})
    assert "count(x.CHAR_VALUE)" in sql and "x.KEY_ID = v.PREMISE_ID" in sql and "left join" in sql.lower()
    assert "ORIGINBA_REPORTING.RPT_PREMISE_SP_BI v" in sql


def test_a_characteristic_is_counted_beside_the_grain_key_so_the_join_runs():
    # counted alone, Jaspersoft drops the join and counts the derived table (12,164 premises, not 33,052
    # service points, Origin_DEV 2026-10-06); any canvas field in the query keeps the join
    q = v.characteristic_query("Char.PS_CHR_PREM_IN_OUT", "SP.PS_SERVICE_POINT_ID")
    refs = [a["fieldRef"] for a in q["select"]["aggregations"]]
    assert refs == ["Char.PS_CHR_PREM_IN_OUT", "SP.PS_SERVICE_POINT_ID"]
    assert all(a["aggregateFunction"] == "CountAll" for a in q["select"]["aggregations"])
