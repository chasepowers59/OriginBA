"""The repository tool's writes: the exact call each command makes, and the guards that keep a
write off the wrong org or off prod by accident. Offline -- the HTTP layer is replaced."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "scripts/jaspersoft/jrs_repository.py"


def run(*args, env_extra=None):
    env = {**os.environ, "JRS_TEST_URL": "https://jrs.example/jasperserver-pro", "JRS_TEST_USER": "me@x|Origin_DEV", "JRS_TEST_PASSWORD": "x",
           "JRS_PROD_URL": "https://prod.example/jasperserver-pro", "JRS_PROD_USER": "me@x|CityCorp", "JRS_PROD_PASSWORD": "x"}
    env.update(env_extra or {})
    for k in list(env):
        if k in ("JRS_URL", "JRS_USER", "JRS_PASSWORD"):
            env.pop(k)
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True, env=env)


def test_copy_is_a_post_with_content_location_into_the_destination_folder():
    r = run("--dry-run", "--confirm", "Origin_DEV", "copy", "/SmartCity/Report/A/r1", "/SmartCity/Report/B")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "POST /rest_v2/resources/SmartCity/Report/B?createFolders=true&overwrite=false" in r.stdout
    assert "'Content-Location': '/SmartCity/Report/A/r1'" in r.stdout


def test_move_is_a_put_and_delete_is_a_delete():
    assert "PUT /rest_v2/resources/SmartCity/Report/B?" in run("--dry-run", "--confirm", "Origin_DEV", "move", "/SmartCity/Report/A/r1", "/SmartCity/Report/B").stdout
    assert "DELETE /rest_v2/resources/SmartCity/Report/A/r1" in run("--dry-run", "--confirm", "Origin_DEV", "delete", "/SmartCity/Report/A/r1").stdout


def test_a_write_without_naming_the_org_back_is_refused():
    r = run("--dry-run", "delete", "/SmartCity/Report/A/r1")
    assert r.returncode != 0 and "pass --confirm Origin_DEV" in r.stderr


def test_naming_the_wrong_org_is_refused():
    r = run("--dry-run", "--confirm", "Ellensburg", "delete", "/SmartCity/Report/A/r1")
    assert r.returncode != 0 and "scoped to Origin_DEV" in r.stderr


def test_org_flag_rescopes_the_login_and_the_confirm_must_match_it():
    r = run("--dry-run", "--org", "Ellensburg", "--confirm", "Origin_DEV", "delete", "/SmartCity/Report/A/r1")
    assert r.returncode != 0 and "scoped to Ellensburg" in r.stderr
    assert run("--dry-run", "--org", "Ellensburg", "--confirm", "Ellensburg", "delete", "/SmartCity/Report/A/r1").returncode == 0


def test_a_root_scoped_write_must_be_confirmed_as_root():
    r = run("--dry-run", "--confirm", "Origin_DEV", "delete", "/x", env_extra={"JRS_TEST_USER": "superuser"})
    assert r.returncode != 0 and "ROOT" in r.stderr and "outside every client tenant" in r.stderr


def test_prod_writes_need_i_mean_prod_and_say_to_snapshot_first():
    r = run("--env", "prod", "--dry-run", "--confirm", "CityCorp", "delete", "/SmartCity/Report/A/r1")
    assert r.returncode != 0 and "--i-mean-prod" in r.stderr and "snapshot --env prod --orgs CityCorp" in r.stderr
    assert run("--env", "prod", "--dry-run", "--confirm", "CityCorp", "--i-mean-prod", "delete", "/SmartCity/Report/A/r1").returncode == 0


def test_permissions_put_replaces_with_the_named_grants():
    r = run("--dry-run", "--confirm", "Origin_DEV", "perms-set", "/SmartCity/Report/X", "role/ROLE_BILLING:18", "user/jsmith:30")
    assert "PUT /rest_v2/permissions/SmartCity/Report/X" in r.stdout and "body=" in r.stdout


def test_reads_need_no_confirmation():
    for args in (["perms", "/x"], ["jobs"], ["users"], ["roles"]):
        r = run("--dry-run", *args)
        assert "refused" not in r.stderr, args   # the read itself fails offline; the guard must not fire
