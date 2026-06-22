from __future__ import annotations

import time
from datetime import datetime, timezone

from app_main.models.repo import CommitInfo


def _iso_timestamp(ts: float | None = None) -> str:
    when = ts if ts is not None else time.time()
    return datetime.fromtimestamp(when, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _commit_dict(commit_hash: str, author: str, committed_at: int, subject: str) -> dict:
    return {
        "id": commit_hash,
        "author": author,
        "committed_at": committed_at,
        "subject": subject,
    }


def _commits_list(commits: list[CommitInfo]) -> list[dict]:
    return [
        {
            "id": c.hash,
            "author": c.author,
            "committed_at": c.committed_at,
            "subject": c.subject,
        }
        for c in commits
    ]


def build_test_payload(
    webhook_id: str,
    repo_key: str,
    project_name: str,
    repo_path: str,
) -> dict:
    now = time.time()
    return {
        "id": f"test_{webhook_id}",
        "type": "webhook.test",
        "occurred_at": _iso_timestamp(now),
        "repository": {
            "id": repo_key,
            "project": project_name,
            "path": repo_path,
        },
        "current": {
            "commit": _commit_dict(
                "0" * 40,
                "gitmail",
                int(now),
                "gitmail webhook test",
            )
        },
        "extensions": {
            "gitmail": {"test": True, "webhook_id": webhook_id},
        },
    }


def build_update_payload(
    event_id: str,
    repo_key: str,
    project_name: str,
    repo_path: str,
    old_hash: str,
    old_subject: str | None,
    commit_hash: str,
    commit_time: int,
    subject: str,
    author: str,
    recent: list[CommitInfo],
    *,
    gerrit_project_url: str | None = None,
    gerrit_commit_url: str | None = None,
    gerrit_change_number: int | None = None,
) -> dict:
    payload: dict = {
        "id": event_id,
        "type": "repository.commit.updated",
        "occurred_at": _iso_timestamp(),
        "repository": {
            "id": repo_key,
            "project": project_name,
            "path": repo_path,
        },
        "previous": {
            "commit": {
                "id": old_hash,
                "subject": old_subject or "",
            }
        },
        "current": {
            "commit": _commit_dict(commit_hash, author, commit_time, subject),
        },
        "commits": _commits_list(recent),
    }
    links: dict[str, str] = {}
    if gerrit_project_url:
        links["web"] = gerrit_project_url
    if gerrit_commit_url:
        links["commit"] = gerrit_commit_url
    if links:
        payload["links"] = links
    extensions: dict = {}
    if gerrit_change_number is not None:
        extensions["gerrit"] = {"change_number": gerrit_change_number}
    if extensions:
        payload["extensions"] = extensions
    return payload
