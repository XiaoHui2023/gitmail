from __future__ import annotations

import sqlite3
from typing import Annotated
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app_main.api.deps import AppState, get_app_state, require_allowed_user
from app_main.identity.user_resolver import ResolvedUser
from app_main.webhooks.dispatcher import WebhookDispatcher

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class WebhookCreateBody(BaseModel):
    repo_key: str = Field(description="仓库唯一键 project::path")
    url: str = Field(description="回调 URL")
    label: str = Field(default="", description="备注")
    enabled: bool = Field(default=True, description="是否启用")
    secret: str = Field(default="", description="签名密钥；留空则自动生成")

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return _normalize_webhook_url(value)

    @field_validator("repo_key", "label")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class WebhookUpdateBody(BaseModel):
    repo_key: str | None = Field(default=None, description="仓库唯一键")
    url: str | None = Field(default=None, description="回调 URL")
    label: str | None = Field(default=None, description="备注")
    enabled: bool | None = Field(default=None, description="是否启用")
    secret: str | None = Field(default=None, description="轮换签名密钥；留空表示不修改")

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_webhook_url(value)

    @field_validator("repo_key", "label")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


def _normalize_webhook_url(url: str) -> str:
    cleaned = url.strip()
    parsed = urlparse(cleaned)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("URL 须为有效的 http:// 或 https:// 地址")
    return cleaned


def _serialize_webhook(store, row: sqlite3.Row, *, include_secret: bool = False) -> dict:
    repo_row = store.get_repo_row(row["repo_key"])
    project_name = repo_row["project_name"] if repo_row else row["repo_key"].split("::", 1)[0]
    repo_path = repo_row["repo_path"] if repo_row else row["repo_key"].split("::", 1)[-1]
    item = {
        "id": row["id"],
        "repo_key": row["repo_key"],
        "project_name": project_name,
        "repo_path": repo_path,
        "url": row["url"],
        "label": row["label"],
        "enabled": bool(row["enabled"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "last_delivery": _serialize_last_delivery(row),
    }
    if include_secret:
        item["secret"] = row["secret"]
    return item


def _serialize_last_delivery(row: sqlite3.Row) -> dict | None:
    if row["last_delivery_at"] is None:
        return None
    return {
        "at": row["last_delivery_at"],
        "ok": bool(row["last_delivery_ok"]) if row["last_delivery_ok"] is not None else None,
        "status_code": row["last_delivery_status"],
        "error": row["last_delivery_error"],
    }


def _serialize_delivery_result(result) -> dict:
    return {
        "ok": result.ok,
        "status_code": result.status_code,
        "duration_ms": result.duration_ms,
        "response_preview": result.response_preview,
        "error": result.error,
    }


def _get_dispatcher(state: AppState) -> WebhookDispatcher:
    return state.webhooks  # type: ignore[attr-defined]


@router.get("")
def list_webhooks(
    state: Annotated[AppState, Depends(get_app_state)],
    user: Annotated[ResolvedUser, Depends(require_allowed_user)],
) -> dict:
    rows = state.store.list_webhooks(user.username)
    return {"items": [_serialize_webhook(state.store, row) for row in rows]}


@router.post("")
def create_webhook(
    body: WebhookCreateBody,
    state: Annotated[AppState, Depends(get_app_state)],
    user: Annotated[ResolvedUser, Depends(require_allowed_user)],
) -> dict:
    if state.store.get_repo_row(body.repo_key) is None:
        raise HTTPException(status_code=404, detail="仓库不存在")
    secret = body.secret.strip() or WebhookDispatcher.generate_secret()
    try:
        webhook_id = state.store.create_webhook(
            user.username,
            body.repo_key,
            body.url,
            body.label,
            secret,
            body.enabled,
        )
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            raise HTTPException(status_code=409, detail="同一仓库与 URL 的 Webhook 已存在") from exc
        raise
    row = state.store.get_webhook(user.username, webhook_id)
    assert row is not None
    return _serialize_webhook(state.store, row, include_secret=True)


@router.get("/{webhook_id}")
def get_webhook(
    webhook_id: str,
    state: Annotated[AppState, Depends(get_app_state)],
    user: Annotated[ResolvedUser, Depends(require_allowed_user)],
) -> dict:
    row = state.store.get_webhook(user.username, webhook_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Webhook 不存在")
    return _serialize_webhook(state.store, row)


@router.put("/{webhook_id}")
def update_webhook(
    webhook_id: str,
    body: WebhookUpdateBody,
    state: Annotated[AppState, Depends(get_app_state)],
    user: Annotated[ResolvedUser, Depends(require_allowed_user)],
) -> dict:
    row = state.store.get_webhook(user.username, webhook_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Webhook 不存在")
    new_repo_key = body.repo_key if body.repo_key is not None else row["repo_key"]
    if new_repo_key != row["repo_key"] and state.store.get_repo_row(new_repo_key) is None:
        raise HTTPException(status_code=404, detail="仓库不存在")
    secret = body.secret.strip() if body.secret else None
    try:
        state.store.update_webhook(
            user.username,
            webhook_id,
            repo_key=body.repo_key,
            url=body.url,
            label=body.label,
            secret=secret if secret else None,
            enabled=body.enabled,
        )
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            raise HTTPException(status_code=409, detail="同一仓库与 URL 的 Webhook 已存在") from exc
        raise
    updated = state.store.get_webhook(user.username, webhook_id)
    assert updated is not None
    payload = _serialize_webhook(state.store, updated)
    if secret:
        payload["secret"] = secret
    return payload


@router.delete("/{webhook_id}")
def delete_webhook(
    webhook_id: str,
    state: Annotated[AppState, Depends(get_app_state)],
    user: Annotated[ResolvedUser, Depends(require_allowed_user)],
) -> dict:
    if not state.store.delete_webhook(user.username, webhook_id):
        raise HTTPException(status_code=404, detail="Webhook 不存在")
    return {"ok": True, "id": webhook_id}


@router.post("/{webhook_id}/test")
def test_webhook(
    webhook_id: str,
    state: Annotated[AppState, Depends(get_app_state)],
    user: Annotated[ResolvedUser, Depends(require_allowed_user)],
) -> dict:
    row = state.store.get_webhook(user.username, webhook_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Webhook 不存在")
    result = _get_dispatcher(state).send_test(row)
    return _serialize_delivery_result(result)
