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

INDEX_DOCS = ["README.md", "AGENTS.md", "docs/roadmap/repository_structure_standard.md",
              "domains/README.md", "jaspersoft/README.md"]
# Rewritten in Phase 5 of the reorg; their dangling paths are known and listed there.
REWRITTEN_IN_PHASE_5 = {"README.md", "domains/README.md", "AGENTS.md",
                        "docs/roadmap/repository_structure_standard.md"}

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


# --- D5: only the active-8 snapshot tables outside the archive ----------------------
def test_d5_no_retired_snapshot_table_outside_the_archive():
    if not ARCHIVE.exists():
        pytest.skip("archive tree not created yet (Phase 2)")
    pat = re.compile(r"\b[A-Z0-9_]+_RPT_CURR\b")
    found: dict[str, set[str]] = {}
    for f in tracked_files("sql", "domains", "scripts", "deploy/jaspersoft_standard_offering"):
        if f.suffix.lower() not in {".sql", ".xml", ".py", ".sh", ".ps1", ".md", ".json", ".csv"}:
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for name in set(pat.findall(text)) - ACTIVE_8 - RPT_CURR_ALLOWED_MENTIONS:
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
        m = re.match(r"\|\s*`([^`]+)`\s*\|", line)
        if not m or m.group(1) in ("what", "original path"):
            continue
        old = Path(m.group(1))
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
