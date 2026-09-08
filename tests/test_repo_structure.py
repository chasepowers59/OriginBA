"""Repository structure checks for the 2026-09-08 reorganization (plan D1..D10).

Each check names the phase that makes it applicable; until that phase lands the check
is skipped with the reason, so the suite stays honest rather than green by omission.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT / "archive" / "2026-09-08_reorg"

ACTIVE_8 = {
    "FT_RPT_CURR", "BSEG_BILLED_USAGE_RPT_CURR", "BSEG_SQ_USAGE_RPT_CURR", "D1_MSRMT_RPT_CURR",
    "FT_GL_DISTRIBUTION_RPT_CURR", "D1_USAGE_RPT_CURR", "D1_USAGE_SCALAR_DTL_RPT_CURR",
}
# Named by active-8 tooling as a legacy comparison point or a synonym, not deployed by it.
RPT_CURR_ALLOWED_MENTIONS = set()
# Files whose purpose is to FIND and STOP the retired jobs in client databases.
RPT_CURR_ALLOWED_FILES = {"sql/performance/snapshots/qa/scheduler_jobs_sweep.sql",
                          "sql/performance/snapshots/qa/scheduler_jobs_disable_retired.sql"}

INDEX_DOCS = ["README.md", "AGENTS.md", "docs/roadmap/repository_structure_standard.md",
              "domains/README.md", "jaspersoft/README.md"]
# Rewritten in Phase 5 of the reorg; their dangling paths are known and listed there.
REWRITTEN_IN_PHASE_5 = {"README.md", "AGENTS.md"}

_PATH_TOKEN = re.compile(r"`([^`\s]+)`")
_PLACEHOLDER = re.compile(r"[<>{}*?$~]|^https?://|^--|^-[a-z]|^\.$|^/")


def backticked_paths(text: str) -> list[str]:
    out = []
    for tok in _PATH_TOKEN.findall(text):
        tok = tok.rstrip(":,;.)")
        if "/" not in tok and not re.search(r"\.(md|yml|yaml|py|sh|sql|json|ps1|xml|csv|toml)$", tok):
            continue
        if _PLACEHOLDER.search(tok):
            continue
        out.append(tok)
    return out


_BASENAMES: set[str] | None = None


def tracked_basenames() -> set[str]:
    global _BASENAMES
    if _BASENAMES is None:
        out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        _BASENAMES = {Path(line).name for line in out.splitlines()}
    return _BASENAMES


def path_exists(token: str, doc: Path) -> bool:
    """A path is read relative to the doc's own directory first, then the repo root; a
    bare file name is a mention and counts if any tracked file carries it."""
    if "/" not in token:
        return token in tracked_basenames()
    return (doc.parent / token).exists() or (ROOT / token).exists()


def expand_braces(tokens: list[str]) -> list[str]:
    """`deploy/{A,B}DS.zip` -> deploy/ADS.zip, deploy/BDS.zip (one level, as INDEX.md writes them)."""
    out = []
    for t in tokens:
        m = re.search(r"\{([^{}]+)\}", t)
        out.extend(t[:m.start()] + alt + t[m.end():] for alt in m.group(1).split(",")) if m else out.append(t)
    return [t.rstrip("/") for t in out]


def git_ignored(path: str) -> bool:
    return subprocess.run(["git", "check-ignore", "-q", path], cwd=ROOT).returncode == 0


def tracked_files(*subdirs: str) -> list[Path]:
    args = ["git", "ls-files", *subdirs]
    out = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [ROOT / line for line in out.splitlines() if line]


# --- D1: every path an index doc names exists -------------------------------------
@pytest.mark.parametrize("doc", INDEX_DOCS)
def test_d1_index_docs_name_only_existing_paths(doc):
    p = ROOT / doc
    if not p.exists():
        pytest.skip(f"{doc} does not exist yet (created in a later phase)")
    missing = sorted({t for t in backticked_paths(p.read_text(encoding="utf-8")) if not path_exists(t, p)})
    if missing and doc in REWRITTEN_IN_PHASE_5:
        pytest.xfail(f"{doc} is rewritten in Phase 5; {len(missing)} dangling paths: " + ", ".join(missing[:6]))
    assert missing == [], f"{doc} names paths that do not exist:\n  " + "\n  ".join(missing)


# --- D2: live code never reaches into the archive -----------------------------------
def test_d2_live_code_does_not_reference_the_archive():
    if not ARCHIVE.exists():
        pytest.skip("archive tree not created yet (Phase 1)")
    hits = []
    for f in tracked_files("api", "apps/analytics-portal/src", "scripts", "tests", "deploy", ".github", "ci"):
        if f.suffix not in {".py", ".ts", ".tsx", ".sh", ".ps1", ".yml", ".yaml"} or f.name == "test_repo_structure.py":
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "archive/2026-09-08_reorg" in text:
            hits.append(str(f.relative_to(ROOT)))
    assert hits == [], "live code references the archive:\n  " + "\n  ".join(hits)


# --- D4: the client registry and the portal agree ----------------------------------------
def _registry_entries() -> list[dict]:
    import json
    export = ROOT / "config" / "clients.export.json"
    if not export.exists():
        pytest.skip("config/clients.export.json not exported yet (Phase 4)")
    return json.loads(export.read_text(encoding="utf-8"))["entries"]


def test_d4_every_portal_org_is_a_registry_entry():
    import json
    entries = {e["portal_org_id"]: e for e in _registry_entries() if e.get("portal_org_id")}
    orgs = json.loads((ROOT / "config" / "portal_organizations.json").read_text(encoding="utf-8"))
    orgs = orgs["organizations"] if isinstance(orgs, dict) else orgs
    problems = []
    for org in orgs:
        e = entries.get(org["id"])
        if not e:
            problems.append(f"{org['id']}: no registry entry claims it"); continue
        if org.get("warehouse_url_env") != e.get("portal_warehouse_url_env"):
            problems.append(f"{org['id']}: warehouse_url_env {org.get('warehouse_url_env')} vs registry {e.get('portal_warehouse_url_env')}")
        if org.get("env_prefix") and org["env_prefix"] != e.get("portal_oracle_prefix"):
            problems.append(f"{org['id']}: env_prefix {org['env_prefix']} vs registry {e.get('portal_oracle_prefix')}")
    assert problems == [], "\n  ".join(problems)


def test_d4_every_client_alias_the_sql_runner_accepts_is_registered():
    import importlib.util
    spec = importlib.util.spec_from_file_location("rcos", ROOT / "scripts" / "local" / "run_client_oracle_sql.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    known = set()
    for e in _registry_entries():
        known.add(e["id"]); known.update(e.get("aliases", []))
    unknown = sorted(set(mod.CLIENTS) - known)
    assert unknown == [], f"aliases with no registry entry: {unknown}"
    for legacy in ("fonddulac", "collegestation", "newark_prod", "int_train", "odessa_dev", "origin_demo"):
        assert legacy in mod.CLIENTS, f"{legacy} used to work and must still resolve"


def test_d4_promotion_csv_matches_the_registry():
    import csv
    rows = list(csv.reader((ROOT / "deploy" / "jaspersoft_client_promotion" / "client_org_mapping.csv").open(encoding="utf-8")))
    expected = {(e["jaspersoft"]["tenant_org"], e["jaspersoft"]["ds_name"]) for e in _registry_entries()
                if e.get("jaspersoft") and e["jaspersoft"].get("tenant_org") and e.get("kind") == "client" and e.get("client_id") == e["id"]}
    assert {tuple(r) for r in rows if r} == expected


# --- D5: only the active-8 snapshot tables outside the archive ----------------------
_JOB_OR_PROC = re.compile(r"^(?:JOB_BASELINE_|JOB_REFRESH_|JOB_ONCE_FULL_|REFRESH_)|(?:_ONCE|_JOB|_JB)$")


def snapshot_table(name: str) -> str:
    """JOB_REFRESH_FT_RPT_CURR, REFRESH_FT_RPT_CURR and JOB_BASELINE_FT_RPT_CURR_ONCE all name FT_RPT_CURR."""
    while True:
        stripped = _JOB_OR_PROC.sub("", name)
        if stripped == name:
            return name
        name = stripped


def test_d5_no_retired_snapshot_table_outside_the_archive():
    if not (ARCHIVE / "sql" / "performance" / "snapshots").exists():
        pytest.skip("snapshot estate not archived yet (Phase 2)")
    pat = re.compile(r"\b[A-Z0-9_]+_RPT_CURR(?:_ONCE|_JOB|_JB)?\b")
    found: dict[str, set[str]] = {}
    # Code, DDL and domain XML only: prose may name a snapshot that was proposed and never built.
    for f in tracked_files("sql", "domains", "scripts", "deploy/jaspersoft_standard_offering"):
        if f.suffix.lower() not in {".sql", ".xml", ".py", ".sh", ".ps1", ".json", ".csv"}:
            continue
        if str(f.relative_to(ROOT)) in RPT_CURR_ALLOWED_FILES:
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for name in {snapshot_table(n) for n in pat.findall(text)} - ACTIVE_8 - RPT_CURR_ALLOWED_MENTIONS:
            found.setdefault(name, set()).add(str(f.relative_to(ROOT)))
    assert found == {}, "retired snapshot tables still named outside archive/:\n" + "\n".join(
        f"  {k}: {sorted(v)[:3]}{' ...' if len(v) > 3 else ''}" for k, v in sorted(found.items()))


# --- D6: the data-safety ignores hold ------------------------------------------------
@pytest.mark.parametrize("path", [
    ".env", ".env.local", "apps/analytics-portal/.env.local", "apps/analytics-portal/.env.local.bak-x",
    "output/.portal_data_source.vault", "output/.portal_vault_key", "data/analytics_portal/portal_auth.db",
])
def test_d6_secret_paths_are_ignored(path):
    assert git_ignored(path), f"{path} is not gitignored"


# --- D7: a pointer stands at every archived path --------------------------------------
def test_d7_every_archived_item_has_a_pointer_at_its_old_path():
    index = ARCHIVE / "INDEX.md"
    if not index.exists():
        pytest.skip("archive INDEX.md not created yet (Phase 1)")
    missing = []
    for line in index.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or not cells[0].startswith("`") or cells[0] in ("`what`", "`original path`"):
            continue
        for old in (Path(t) for t in expand_braces(re.findall(r"`([^`]+)`", cells[0]))):
            parent = ROOT / old.parent
            pointers = [parent / "ARCHIVED.md", ROOT / old / "README.md", parent / "README.md", parent / "MOVED.md"]
            texts = "".join(p.read_text(encoding="utf-8", errors="ignore") for p in pointers if p.exists())
            if old.name not in texts:
                missing.append(str(old))
    assert missing == [], "archived paths with no pointer naming them:\n  " + "\n  ".join(missing)


# --- D10: MICR never reaches a delivery artifact ---------------------------------------
def test_d10_micr_reaches_no_delivery_artifact():
    hits = []
    for f in tracked_files("jaspersoft", "domains/exports/manual_imports", "output/catalog_dbt.json"):
        if f.suffix.lower() in {".zip", ".jasper", ".xlsx"}:
            continue
        if "MICR_ID" in f.read_text(encoding="utf-8", errors="ignore"):
            hits.append(str(f.relative_to(ROOT)))
    assert hits == [], "MICR_ID in a delivery artifact:\n  " + "\n  ".join(hits)
