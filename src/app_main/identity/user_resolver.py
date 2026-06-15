from __future__ import annotations

import socket
from dataclasses import dataclass

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
    dns_name, dns_user = _reverse_dns_username(ip)
    mapped = _lookup_mapping(ip, ip_user_map)
    if mapped:
        return mapped, "map"
    if dns_user:
        return dns_user, "dns"
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


def _reverse_dns_username(ip: str) -> tuple[str, str]:
    try:
        host, _, _ = socket.gethostbyaddr(ip)
    except (socket.herror, socket.gaierror, OSError):
        return "", ""
    short = host.split(".")[0]
    for suffix in ("-pc", "-laptop", "-desktop"):
        if short.endswith(suffix):
            short = short[: -len(suffix)]
            break
    if short.endswith(".local"):
        short = short[: -len(".local")]
    return host, short or ""
