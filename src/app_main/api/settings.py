from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app_main.api.deps import AppState, get_app_state, require_allowed_user
from app_main.identity.user_resolver import ResolvedUser

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsBody(BaseModel):
    email_enabled: bool = Field(description="是否在仓库更新时发送邮件")


@router.get("")
def get_settings(
    state: Annotated[AppState, Depends(get_app_state)],
    user: Annotated[ResolvedUser, Depends(require_allowed_user)],
) -> dict:
    return {"email_enabled": state.store.get_email_enabled(user.username)}


@router.put("")
def put_settings(
    body: SettingsBody,
    state: Annotated[AppState, Depends(get_app_state)],
    user: Annotated[ResolvedUser, Depends(require_allowed_user)],
) -> dict:
    if body.email_enabled and user.username == "unknown":
        raise HTTPException(status_code=400, detail="无法识别用户名，不能开启邮件推送")
    state.store.set_email_enabled(user.username, body.email_enabled)
    return {"email_enabled": body.email_enabled}
