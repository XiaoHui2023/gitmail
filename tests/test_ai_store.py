from __future__ import annotations

import tempfile
from pathlib import Path

from app_main.store.database import Store


def test_store_ai_summary_roundtrip() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        store = Store(Path(tmp) / "t.db")
        store.upsert_repo_meta(
            "demo::a/b",
            "demo",
            "a/b",
            "/tmp/a/b",
            None,
            "platform/a",
            "ok",
        )
        store.update_repo_success(
            "demo::a/b",
            "hash2",
            100,
            "subject",
            "author",
            [],
        )
        row = store.get_repo_row("demo::a/b")
        assert row["ai_summary_status"] == "pending"

        assert store.update_ai_summary("demo::a/b", "hash2", "AI 说明", "ready")
        row = store.get_repo_row("demo::a/b")
        assert row["ai_summary"] == "AI 说明"
        assert row["ai_summary_status"] == "ready"

        assert not store.update_ai_summary("demo::a/b", "stale", "x", "ready")
        store.close()
