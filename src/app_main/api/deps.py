from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from app_main.identity.user_resolver import ResolvedUser, build_user
from app_main.identity.whitelist import is_ip_allowed
from app_main.models.config import AppConfig


@dataclass
class AppState:
    config: AppConfig
    store: object
    monitor: object
    smtp: object


def get_app_state(request: Request) -> AppState:
    return request.app.state.ctx  # type: ignore[attr-defined]


def get_client_ip(request: Request, state: Annotated[AppState, Depends(get_app_state)]) -> str:
    header = state.config.trusted_proxy_header.strip()
    if header:
        forwarded = request.headers.get(header)
        if forwarded:
            return forwarded.split(",")[0].strip()
    if request.client is None:
        return "127.0.0.1"
    return request.client.host


def get_current_user(
    request: Request,
    state: Annotated[AppState, Depends(get_app_state)],
    ip: Annotated[str, Depends(get_client_ip)],
) -> ResolvedUser:
    allowed = is_ip_allowed(ip, state.config.ip_whitelist)
    return build_user(ip, state.config.email_domain, state.config.ip_user_map, allowed)


def require_allowed_user(user: Annotated[ResolvedUser, Depends(get_current_user)]) -> ResolvedUser:
    if not user.allowed:
        raise HTTPException(status_code=403, detail="当前 IP 不在白名单内")
    return user
