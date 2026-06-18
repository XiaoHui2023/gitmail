from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from app_main.identity.client_ip import resolve_client_ip
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
    direct = request.client.host if request.client else None
    return resolve_client_ip(direct, request.headers, state.config.trusted_proxy_header)


def get_current_user(
    request: Request,
    state: Annotated[AppState, Depends(get_app_state)],
    ip: Annotated[str, Depends(get_client_ip)],
) -> ResolvedUser:
    allowed = is_ip_allowed(ip, state.config.ip_whitelist)
    return build_user(
        ip,
        state.config.email_domain,
        state.config.ip_user_map,
        allowed,
        state.config.username_extract_regexes,
    )


def require_allowed_user(user: Annotated[ResolvedUser, Depends(get_current_user)]) -> ResolvedUser:
    if not user.allowed:
        raise HTTPException(status_code=403, detail="当前 IP 不在白名单内")
    return user
