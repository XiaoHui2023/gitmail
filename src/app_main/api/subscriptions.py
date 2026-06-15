from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app_main.api.deps import AppState, get_app_state, require_allowed_user
from app_main.identity.user_resolver import ResolvedUser

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


class SubscribeBody(BaseModel):
    repo_key: str = Field(description="仓库唯一键 project::path")


@router.post("")
def subscribe(
    body: SubscribeBody,
    state: Annotated[AppState, Depends(get_app_state)],
    user: Annotated[ResolvedUser, Depends(require_allowed_user)],
) -> dict:
    if state.store.get_repo_row(body.repo_key) is None:
        raise HTTPException(status_code=404, detail="仓库不存在")
    state.store.subscribe(user.username, body.repo_key)
    return {"ok": True, "repo_key": body.repo_key}


@router.delete("/{repo_key:path}")
def unsubscribe(
    repo_key: str,
    state: Annotated[AppState, Depends(get_app_state)],
    user: Annotated[ResolvedUser, Depends(require_allowed_user)],
) -> dict:
    state.store.unsubscribe(user.username, repo_key)
    return {"ok": True, "repo_key": repo_key}
