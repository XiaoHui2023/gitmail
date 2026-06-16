from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path

from app_main.models.repo import CommitInfo, RepoSnapshot, make_repo_key


class Store:
    """SQLite 状态库：仓库状态、订阅与用户设置。"""

    def __init__(self, db_path: Path) -> None:
        """打开或创建数据库文件。

        Args:
            db_path: SQLite 文件路径。
        """
        self._db_path = db_path
        self._lock = threading.RLock()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS repo_state (
                    repo_key TEXT PRIMARY KEY,
                    project_name TEXT NOT NULL,
                    repo_path TEXT NOT NULL,
                    local_path TEXT NOT NULL,
                    gerrit_base TEXT,
                    gerrit_project TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    last_commit_hash TEXT,
                    last_commit_time INTEGER,
                    last_commit_subject TEXT,
                    last_commit_author TEXT,
                    recent_commits_json TEXT,
                    error_message TEXT,
                    fail_count INTEGER NOT NULL DEFAULT 0,
                    next_retry_at REAL NOT NULL DEFAULT 0,
                    updated_at REAL NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS subscriptions (
                    username TEXT NOT NULL,
                    repo_key TEXT NOT NULL,
                    PRIMARY KEY (username, repo_key)
                );
                CREATE TABLE IF NOT EXISTS user_settings (
                    username TEXT PRIMARY KEY,
                    email_enabled INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS notify_cursor (
                    repo_key TEXT NOT NULL,
                    commit_hash TEXT NOT NULL,
                    notified_at REAL NOT NULL,
                    PRIMARY KEY (repo_key, commit_hash)
                );
                """
            )
            self._conn.commit()

    def upsert_repo_meta(
        self,
        repo_key: str,
        project_name: str,
        repo_path: str,
        local_path: str,
        gerrit_base: str | None,
        gerrit_project: str,
        status: str,
    ) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO repo_state (
                    repo_key, project_name, repo_path, local_path,
                    gerrit_base, gerrit_project, status, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(repo_key) DO UPDATE SET
                    project_name=excluded.project_name,
                    repo_path=excluded.repo_path,
                    local_path=excluded.local_path,
                    gerrit_base=excluded.gerrit_base,
                    gerrit_project=excluded.gerrit_project,
                    updated_at=excluded.updated_at
                """,
                (
                    repo_key,
                    project_name,
                    repo_path,
                    local_path,
                    gerrit_base,
                    gerrit_project,
                    status,
                    time.time(),
                ),
            )
            self._conn.commit()

    def update_repo_success(
        self,
        repo_key: str,
        commit_hash: str,
        commit_time: int,
        subject: str,
        author: str,
        recent_commits: list[CommitInfo],
    ) -> bool:
        """写入成功检查结果；若提交号变化返回 True。"""
        with self._lock:
            row = self._conn.execute(
                "SELECT last_commit_hash FROM repo_state WHERE repo_key = ?",
                (repo_key,),
            ).fetchone()
            changed = row is None or row["last_commit_hash"] != commit_hash
            commits_json = json.dumps(
                [
                    {
                        "hash": c.hash,
                        "author": c.author,
                        "committed_at": c.committed_at,
                        "subject": c.subject,
                    }
                    for c in recent_commits
                ]
            )
            self._conn.execute(
                """
                UPDATE repo_state SET
                    status='ok',
                    last_commit_hash=?,
                    last_commit_time=?,
                    last_commit_subject=?,
                    last_commit_author=?,
                    recent_commits_json=?,
                    error_message=NULL,
                    fail_count=0,
                    next_retry_at=0,
                    updated_at=?
                WHERE repo_key=?
                """,
                (
                    commit_hash,
                    commit_time,
                    subject,
                    author,
                    commits_json,
                    time.time(),
                    repo_key,
                ),
            )
            self._conn.commit()
            return changed

    def update_repo_failure(
        self,
        repo_key: str,
        error_message: str,
        fail_count: int,
        next_retry_at: float,
    ) -> None:
        with self._lock:
            self._conn.execute(
                """
                UPDATE repo_state SET
                    status='error',
                    error_message=?,
                    fail_count=?,
                    next_retry_at=?,
                    updated_at=?
                WHERE repo_key=?
                """,
                (error_message, fail_count, next_retry_at, time.time(), repo_key),
            )
            self._conn.commit()

    def list_repo_rows(self) -> list[sqlite3.Row]:
        with self._lock:
            return list(self._conn.execute("SELECT * FROM repo_state ORDER BY project_name, repo_path"))

    def get_repo_row(self, repo_key: str) -> sqlite3.Row | None:
        with self._lock:
            return self._conn.execute(
                "SELECT * FROM repo_state WHERE repo_key = ?", (repo_key,)
            ).fetchone()

    def remove_missing_repos(self, active_keys: set[str]) -> None:
        with self._lock:
            rows = self._conn.execute("SELECT repo_key FROM repo_state").fetchall()
            for row in rows:
                if row["repo_key"] not in active_keys:
                    key = row["repo_key"]
                    self._conn.execute("DELETE FROM repo_state WHERE repo_key = ?", (key,))
                    self._conn.execute("DELETE FROM subscriptions WHERE repo_key = ?", (key,))
                    self._conn.execute("DELETE FROM notify_cursor WHERE repo_key = ?", (key,))
            self._conn.commit()

    def subscribe(self, username: str, repo_key: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO subscriptions (username, repo_key) VALUES (?, ?)",
                (username, repo_key),
            )
            self._conn.commit()

    def unsubscribe(self, username: str, repo_key: str) -> None:
        with self._lock:
            self._conn.execute(
                "DELETE FROM subscriptions WHERE username = ? AND repo_key = ?",
                (username, repo_key),
            )
            self._conn.commit()

    def list_subscribed_keys(self, username: str) -> set[str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT repo_key FROM subscriptions WHERE username = ?", (username,)
            ).fetchall()
            return {row["repo_key"] for row in rows}

    def list_subscribers(self, repo_key: str) -> list[str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT username FROM subscriptions WHERE repo_key = ?", (repo_key,)
            ).fetchall()
            return [row["username"] for row in rows]

    def get_email_enabled(self, username: str) -> bool:
        with self._lock:
            row = self._conn.execute(
                "SELECT email_enabled FROM user_settings WHERE username = ?", (username,)
            ).fetchone()
            return bool(row and row["email_enabled"])

    def set_email_enabled(self, username: str, enabled: bool) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO user_settings (username, email_enabled) VALUES (?, ?)
                ON CONFLICT(username) DO UPDATE SET email_enabled=excluded.email_enabled
                """,
                (username, int(enabled)),
            )
            self._conn.commit()

    def is_notified(self, repo_key: str, commit_hash: str) -> bool:
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM notify_cursor WHERE repo_key = ? AND commit_hash = ?",
                (repo_key, commit_hash),
            ).fetchone()
            return row is not None

    def mark_notified(self, repo_key: str, commit_hash: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO notify_cursor (repo_key, commit_hash, notified_at) VALUES (?, ?, ?)",
                (repo_key, commit_hash, time.time()),
            )
            self._conn.commit()

    def count_failed_repos(self) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT COUNT(*) AS c FROM repo_state WHERE status = 'error'"
            ).fetchone()
            return int(row["c"]) if row else 0

    def row_to_snapshot(self, row: sqlite3.Row, subscribed: bool = False) -> RepoSnapshot:
        from app_main.manifest.gerrit_urls import build_gerrit_urls

        gerrit_base = row["gerrit_base"]
        gerrit_project = row["gerrit_project"]
        commit_hash = row["last_commit_hash"]
        urls = build_gerrit_urls(gerrit_base, gerrit_project, commit_hash)
        recent: list[CommitInfo] = []
        if row["recent_commits_json"]:
            for item in json.loads(row["recent_commits_json"]):
                recent.append(
                    CommitInfo(
                        hash=item["hash"],
                        author=item["author"],
                        committed_at=item["committed_at"],
                        subject=item["subject"],
                    )
                )
        return RepoSnapshot(
            repo_key=row["repo_key"],
            project_name=row["project_name"],
            repo_path=row["repo_path"],
            status=row["status"],
            last_commit_hash=commit_hash,
            last_commit_time=row["last_commit_time"],
            last_commit_subject=row["last_commit_subject"],
            last_commit_author=row["last_commit_author"],
            gerrit_base=gerrit_base,
            gerrit_project=gerrit_project,
            gerrit_project_url=urls.project_url,
            gerrit_commit_url=urls.commit_url,
            error_message=row["error_message"],
            subscribed=subscribed,
            recent_commits=recent,
        )

    def close(self) -> None:
        with self._lock:
            self._conn.close()
