#!/usr/bin/env python3
"""Deploy the finance report pack to a JasperReports Server through the REST API, then run it.

No import zip: each report unit is written with PUT /rest_v2/resources/<uri> as a reportUnit
descriptor carrying the main JRXML, the subreport as an embedded jrxml resource (named what
the main's repo:<name> says), the tenant datasource by reference and the input controls
embedded -- so the result is verifiable in the same run: the unit is read back, then executed
as a PDF with a real window and the text is checked. Credentials from JRS_URL / JRS_USER /
JRS_PASSWORD (a superuser writes absolute org paths; an org-scoped user writes /SmartCity/...).

    python3 scripts/jaspersoft/jrs_deploy_report_units.py --org Origin_DEV --datasource Origin_DEV_DS
    python3 scripts/jaspersoft/jrs_deploy_report_units.py --org Origin_DEV --datasource Origin_DEV_DS --run 2025-01-01 2026-08-31
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_sql_report_pack as g  # noqa: E402
from jrs_repository import _call, _cfg, _ssl_context  # noqa: E402

DATATYPE = {"singleValueText": "text", "singleValueNumber": "number", "singleValueDate": "date"}


def org_root(org: str | None) -> str:
    return f"/organizations/organization_1/organizations/{org}" if org else ""


def descriptor(spec: g.Spec, ds_uri: str) -> dict:
    doc, _ = g.controls(spec)
    controls = []
    for ic in doc["inputControls"]:
        controls.append({"inputControl": {
            "label": ic["label"], "mandatory": bool(ic["mandatory"]), "readOnly": False, "visible": True, "type": 2,
            "dataType": {"dataType": {"label": "myDatatype", "type": DATATYPE[ic["type"]], "strictMin": False, "strictMax": False}},
            # the embedded resource takes its NAME (= the report parameter it binds) from this
            "uri": f"{spec.name}_files/{ic['id']}"}})
    return {
        "label": spec.label, "description": spec.description,
        "alwaysPromptControls": True, "controlsLayout": "popupScreen",
        "dataSource": {"dataSourceReference": {"uri": ds_uri}},
        "jrxml": {"jrxmlFile": {"label": "Main jrxml", "type": "jrxml",
                                "content": base64.b64encode((g.REPORTS / f"{spec.name}.jrxml").read_bytes()).decode()}},
        # ClientReportUnitResourceListWrapper: the list sits under "resource"
        "resources": {"resource": [{"name": spec.sub.name, "file": {"fileResource": {
            "label": spec.sub.name, "type": "jrxml",
            "content": base64.b64encode((g.SUBS / f"{spec.sub.name}.jrxml").read_bytes()).decode()}}}]},
        "inputControls": controls,
    }


def deploy(org: str | None, ds: str) -> list[str]:
    root = org_root(org)
    ds_uri = f"{root}/DataSource/{ds}"
    uris = []
    for spec in g.SPECS:
        uri = f"{root}{g.FOLDERS[spec.name]}/{spec.name}"
        body = json.dumps(descriptor(spec, ds_uri)).encode()
        code, text = _call(f"/rest_v2/resources{uri}?overwrite=true&createFolders=true", method="PUT", body=body,
                           ctype="application/repository.reportUnit+json", accept="application/json")
        print(f"PUT {uri}: {code}" + ("" if code in (200, 201) else f"\n     {text[:600]}"))
        if code not in (200, 201):
            continue
        code, text = _call(f"/rest_v2/resources{uri}?expanded=true", accept="application/repository.reportUnit+json")
        d = json.loads(text)
        ctl = [c.get("inputControl", c.get("inputControlReference", {})).get("uri", "?").rsplit("/", 1)[-1] for c in d.get("inputControls", [])]
        rs = d.get("resources", {}); rs = rs.get("resource", rs) if isinstance(rs, dict) else rs
        res = [r.get("name") for r in rs]
        dsd = d.get("dataSource", {}); dsd = next(iter(dsd.values())) if dsd else {}
        print(f"     controls: {ctl}\n     resources: {res}; datasource: {dsd.get('uri', '?').rsplit('/', 1)[-1]}")
        uris.append(uri)
    return uris


def run(uris: list[str], from_dt: str, to_dt: str, out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    bad = 0
    for uri in uris:
        q = urllib.parse.urlencode({"FROM_DT": from_dt, "TO_DT": to_dt, "CLIENT_NAME": "Origin DEV (Ellensburg 25.4)"})
        url, auth = _cfg()
        req = urllib.request.Request(f"{url}/rest_v2/reports{uri}.pdf?{q}")
        req.add_header("Authorization", auth)
        try:
            with urllib.request.urlopen(req, timeout=600, context=_ssl_context()) as r:
                pdf = r.read(); code = r.status
        except urllib.error.HTTPError as e:
            pdf = e.read(); code = e.code
        name = uri.rsplit("/", 1)[-1]
        if code == 200 and pdf[:4] == b"%PDF":
            (out_dir / f"{name}.pdf").write_bytes(pdf)
            print(f"RUN {name}: 200, {len(pdf) // 1024} KB -> {out_dir / (name + '.pdf')}")
        else:
            bad += 1
            print(f"RUN {name}: {code} {pdf[:400].decode('utf-8', 'replace')}")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--org", default=None, help="organization id when the login is a superuser (e.g. Origin_DEV)")
    ap.add_argument("--datasource", default="Origin_DEV_DS")
    ap.add_argument("--run", nargs=2, metavar=("FROM", "TO"), help="execute each unit as a PDF with this window")
    ap.add_argument("--out", type=Path, default=Path("/tmp/finance_pack_pdfs"))
    a = ap.parse_args()
    uris = deploy(a.org, a.datasource)
    if a.run and uris:
        return 1 if run(uris, a.run[0], a.run[1], a.out) else 0
    return 0 if len(uris) == len(g.SPECS) else 1


if __name__ == "__main__":
    sys.exit(main())
