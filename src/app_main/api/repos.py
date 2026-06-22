from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app_main.api.deps import AppState, get_app_state, get_current_user
from app_main.identity.user_resolver import ResolvedUser

router = APIRouter(prefix="/repos", tags=["repos"])


def _filter_rows(rows, project: str, path: str):
    for row in rows:
        if project and project.lower() not in row["project_name"].lower():
            continue
        if path and path.lower() not in row["repo_path"].lower():
            continue
        yield row


def _serialize_snapshot(store, row, user: ResolvedUser | None) -> dict:
    subscribed = False
    if user and user.allowed:
        subscribed = row["repo_key"] in store.list_subscribed_keys(user.username)
    snap = store.row_to_snapshot(row, subscribed=subscribed)
    return {
        "repo_key": snap.repo_key,
        "project_name": snap.project_name,
        "repo_path": snap.repo_path,
        "status": snap.status,
        "last_commit_hash": snap.last_commit_hash,
        "last_commit_time": snap.last_commit_time,
        "last_commit_subject": snap.last_commit_subject,
        "last_commit_author": snap.last_commit_author,
        "gerrit_project_url": snap.gerrit_project_url,
        "gerrit_commit_url": snap.gerrit_commit_url,
        "gerrit_change_number": snap.gerrit_change_number,
        "error_message": snap.error_message,
        "subscribed": snap.subscribed,
        "recent_commits": [
            {
                "hash": c.hash,
                "author": c.author,
                "committed_at": c.committed_at,
                "subject": c.subject,
            }
            for c in snap.recent_commits
        ],
        "ai_summary": snap.ai_summary,
        "ai_summary_status": snap.ai_summary_status,
    }


@router.get("")
def list_repos(
    state: Annotated[AppState, Depends(get_app_state)],
    user: Annotated[ResolvedUser, Depends(get_current_user)],
    project: str = Query(default=""),
    path: str = Query(default=""),
) -> dict:
    if not state.config.allow_anonymous_repo_list and not user.allowed:
        raise HTTPException(status_code=403, detail="需要白名单 IP 才能查看仓库列表")
    rows = list(_filter_rows(state.store.list_repo_rows(), project, path))
    items = [_serialize_snapshot(state.store, row, user) for row in rows]
    return {"items": items}


@router.get("/subscribed")
def list_subscribed_repos(
    state: Annotated[AppState, Depends(get_app_state)],
    user: Annotated[ResolvedUser, Depends(get_current_user)],
    project: str = Query(default=""),
    path: str = Query(default=""),
) -> dict:
    if not user.allowed:
        raise HTTPException(status_code=403, detail="当前 IP 不在白名单内")
    keys = state.store.list_subscribed_keys(user.username)
    rows = [
        row
        for row in state.store.list_repo_rows()
        if row["repo_key"] in keys
    ]
    rows = list(_filter_rows(rows, project, path))
    items = [_serialize_snapshot(state.store, row, user) for row in rows]
    return {"items": items}
