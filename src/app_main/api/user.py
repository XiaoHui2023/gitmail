from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app_main.api.deps import get_current_user
from app_main.identity.user_resolver import ResolvedUser

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/me")
def get_me(user: Annotated[ResolvedUser, Depends(get_current_user)]) -> dict:
    return {
        "username": user.username,
        "ip": user.ip,
        "email": user.email,
        "email_domain": user.email_domain,
        "resolve_method": user.resolve_method,
        "allowed": user.allowed,
    }
