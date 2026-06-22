from __future__ import annotations

import json
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from app_main.app import create_app
from app_main.store.database import Store
from app_main.webhooks.client import deliver_webhook
from app_main.webhooks.dispatcher import WebhookDispatcher
from app_main.webhooks.payload import build_test_payload, build_update_payload


def _make_client(tmp_path: Path) -> TestClient:
    cfg = {
        "email_domain": "corp.test",
        "ip_whitelist": ["testclient"],
        "projects": [],
    }
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(yaml.dump(cfg), encoding="utf-8")
    return TestClient(create_app(cfg_path))


def test_build_update_payload_shape() -> None:
    payload = build_update_payload(
        "evt_1",
        "demo::a/b",
        "demo",
        "a/b",
        "old" * 10 + "oldhash12",
        "old subject",
        "new" * 10 + "newhash12",
        1719000000,
        "new subject",
        "alice",
        [],
    )
    assert payload["type"] == "repository.commit.updated"
    assert payload["repository"]["id"] == "demo::a/b"
    assert payload["current"]["commit"]["subject"] == "new subject"


def test_store_webhook_roundtrip() -> None:
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
        webhook_id = store.create_webhook(
            "alice",
            "demo::a/b",
            "https://example.com/hook",
            "CI",
            "whsec_test",
            True,
        )
        rows = store.list_webhooks("alice")
        assert len(rows) == 1
        assert rows[0]["id"] == webhook_id
        assert store.list_enabled_webhooks_for_repo("demo::a/b")[0]["url"].endswith("/hook")
        store.mark_webhook_delivered(webhook_id, "abc")
        assert store.is_webhook_delivered(webhook_id, "abc")
        store.delete_webhook("alice", webhook_id)
        assert store.list_webhooks("alice") == []
        store.close()


def test_webhook_api_crud_and_test(tmp_path: Path) -> None:
    received: dict = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
            received["body"] = json.loads(body.decode("utf-8"))
            received["event"] = self.headers.get("X-Gitmail-Event")
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"ok":true}')

        def log_message(self, format: str, *args) -> None:
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    hook_url = f"http://127.0.0.1:{port}/hook"

    client = _make_client(tmp_path)
    store = client.app.state.ctx.store  # type: ignore[attr-defined]
    store.upsert_repo_meta(
        "demo::a/b",
        "demo",
        "a/b",
        "/tmp/a/b",
        "http://review.example.com",
        "platform/a",
        "ok",
    )

    created = client.post(
        "/api/webhooks",
        json={
            "repo_key": "demo::a/b",
            "url": hook_url,
            "label": "CI",
        },
    )
    assert created.status_code == 200
    data = created.json()
    assert data["secret"].startswith("whsec_")
    webhook_id = data["id"]

    listed = client.get("/api/webhooks")
    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 1

    tested = client.post(f"/api/webhooks/{webhook_id}/test")
    assert tested.status_code == 200
    assert tested.json()["ok"] is True
    assert received["event"] == "webhook.test"
    assert received["body"]["type"] == "webhook.test"

    deleted = client.delete(f"/api/webhooks/{webhook_id}")
    assert deleted.status_code == 200
    server.shutdown()


def test_deliver_webhook_reports_http_error() -> None:
    result = deliver_webhook(
        "http://127.0.0.1:1/unreachable",
        "whsec_x",
        "webhook.test",
        build_test_payload("wh_1", "demo::a/b", "demo", "a/b"),
        timeout_seconds=1.0,
    )
    assert result.ok is False
    assert result.error


def test_dispatcher_skips_duplicate_delivery() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = Store(Path(tmp) / "t.db")
        dispatcher = WebhookDispatcher(store)
        store.upsert_repo_meta(
            "demo::a/b",
            "demo",
            "a/b",
            "/tmp/a/b",
            None,
            "platform/a",
            "ok",
        )
        store.create_webhook(
            "alice",
            "demo::a/b",
            "http://127.0.0.1:1/hook",
            "",
            "whsec_x",
            True,
        )
        hook_id = store.list_enabled_webhooks_for_repo("demo::a/b")[0]["id"]
        store.mark_webhook_delivered(hook_id, "c" * 40)
        dispatcher.on_repo_updated(
            "demo::a/b",
            "demo",
            "a/b",
            "b" * 40,
            "old",
            "c" * 40,
            1,
            "new",
            "alice",
            [],
            gerrit_base=None,
            gerrit_project="platform/a",
            gerrit_change_number=None,
        )
        store.close()
