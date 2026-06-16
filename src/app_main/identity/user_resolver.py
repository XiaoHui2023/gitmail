from __future__ import annotations

from dataclasses import dataclass

from app_main.identity.lan_resolve import hostname_to_username, resolve_lan_hostname
from app_main.identity.whitelist import ip_matches_pattern


@dataclass
class ResolvedUser:
    username: str
    ip: str
    email: str
    email_domain: str
    resolve_method: str
    allowed: bool


def resolve_username(ip: str, ip_user_map: dict[str, str]) -> tuple[str, str]:
    """按 IP 解析用户名，返回 (用户名, 解析方式)。"""
    mapped = _lookup_mapping(ip, ip_user_map)
    if mapped:
        return mapped, "map"
    host, method = resolve_lan_hostname(ip)
    if host:
        username = hostname_to_username(host)
        if username:
            return username, method
    return "unknown", "none"


def build_user(
    ip: str,
    email_domain: str,
    ip_user_map: dict[str, str],
    allowed: bool,
) -> ResolvedUser:
    username, method = resolve_username(ip, ip_user_map)
    email = f"{username}@{email_domain}" if username != "unknown" else ""
    return ResolvedUser(
        username=username,
        ip=ip,
        email=email,
        email_domain=email_domain,
        resolve_method=method,
        allowed=allowed,
    )


def _lookup_mapping(ip: str, ip_user_map: dict[str, str]) -> str | None:
    if ip in ip_user_map:
        return ip_user_map[ip]
    for pattern, name in ip_user_map.items():
        if ip_matches_pattern(ip, pattern):
            return name
    return None
