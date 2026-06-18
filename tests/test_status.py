from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from app_main.app import create_app
from app_main.identity.whitelist import ip_matches_pattern
from app_main.manifest.parser import discover_project_repos, normalize_gerrit_base
from app_main.paths import resolve_database_path
from app_main.store.database import Store


def test_status_ok() -> None:
    client = TestClient(create_app())
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["name"] == "gitmail"
    assert "monitor" in data


def test_ip_whitelist_wildcard() -> None:
    assert ip_matches_pattern("192.168.1.42", "192.168.1.*")
    assert not ip_matches_pattern("10.0.0.1", "192.168.1.*")


def test_normalize_gerrit_base() -> None:
    assert normalize_gerrit_base("review.example.com").startswith("http://")
    assert "review.example.com" in normalize_gerrit_base("http://review.example.com/gerrit")


def test_discover_manifest_from_fixture(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    repo_dir = workspace / ".repo"
    repo_dir.mkdir(parents=True)
    (repo_dir / "manifest.xml").write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<manifest>
  <remote name="origin" fetch=".." review="review.example.com"/>
  <default remote="origin" revision="main"/>
  <project name="platform/build" path="build/make"/>
</manifest>
""",
        encoding="utf-8",
    )
    git_dir = workspace / "build" / "make" / ".git"
    git_dir.mkdir(parents=True)
    repos, err = discover_project_repos("demo", workspace, None)
    assert err is None
    assert len(repos) == 1
    assert repos[0].repo_path == "build/make"
    assert repos[0].reachable is True


def test_store_subscribe_roundtrip() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = Store(Path(tmp) / "t.db")
        store.upsert_repo_meta(
            "demo::a/b",
            "demo",
            "a/b",
            "/tmp/a/b",
            "http://review.example.com",
            "platform/a",
            "ok",
        )
        store.subscribe("alice", "demo::a/b")
        assert "demo::a/b" in store.list_subscribed_keys("alice")
        store.set_email_enabled("alice", True)
        assert store.get_email_enabled("alice")
        store.close()


def test_resolve_database_path_default() -> None:
    assert resolve_database_path("").name == "gitmail.db"
    assert resolve_database_path("  ").name == "gitmail.db"


def test_resolve_database_path_custom(tmp_path: Path) -> None:
    custom = tmp_path / "state" / "custom.db"
    assert resolve_database_path(str(custom)) == custom.resolve()


def test_api_with_custom_database_path(tmp_path: Path) -> None:
    db_file = tmp_path / "var" / "gitmail-state.db"
    cfg = {
        "email_domain": "corp.test",
        "database_path": str(db_file),
        "ip_whitelist": ["testclient"],
        "projects": [],
    }
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.dump(cfg), encoding="utf-8")
    client = TestClient(create_app(cfg_path))
    assert client.get("/api/status").status_code == 200
    assert db_file.is_file()


def test_api_with_config(tmp_path: Path) -> None:
    cfg = {
        "email_domain": "corp.test",
        "ip_whitelist": ["testclient"],
        "projects": [],
    }
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.dump(cfg), encoding="utf-8")
    client = TestClient(create_app(cfg_path))
    me = client.get("/api/user/me")
    assert me.status_code == 200
    repos = client.get("/api/repos")
    assert repos.status_code == 200
    assert repos.json()["items"] == []


def test_api_username_extract_regexes_from_config(tmp_path: Path) -> None:
    cfg = {
        "email_domain": "corp.test",
        "ip_whitelist": ["testclient"],
        "ip_user_map": {"testclient": "user-Lenovo"},
        "username_extract_regexes": [r"^([^-]+)-"],
        "projects": [],
    }
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.dump(cfg), encoding="utf-8")
    client = TestClient(create_app(cfg_path))
    me = client.get("/api/user/me")
    assert me.status_code == 200
    assert me.json()["username"] == "user"
    assert me.json()["email"] == "user@corp.test"
