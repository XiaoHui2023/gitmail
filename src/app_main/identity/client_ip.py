from __future__ import annotations

import ipaddress
import socket
from collections.abc import Mapping

_LOOPBACK_PROXY_HEADERS = ("X-Forwarded-For", "X-Real-IP")


def is_loopback_ip(ip: str) -> bool:
    """判断是否为回环地址。"""
    if ip == "localhost":
        return True
    try:
        return ipaddress.ip_address(ip).is_loopback
    except ValueError:
        return False


def local_lan_ip() -> str:
    """取本机对外通信常用的局域网 IPv4。"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def _first_forwarded(value: str) -> str:
    return value.split(",")[0].strip()


def resolve_client_ip(
    direct_host: str | None,
    headers: Mapping[str, str],
    trusted_proxy_header: str,
) -> str:
    """解析来访客户端 IP，回环连接时尽量还原真实客户端身份。

    Args:
        direct_host: 直连对端地址（如 ASGI client.host）
        headers: 请求头
        trusted_proxy_header: 已配置的可信代理头名；非空时优先采用其值
    """
    direct = (direct_host or "127.0.0.1").strip()
    trusted = trusted_proxy_header.strip()
    if trusted:
        forwarded = headers.get(trusted)
        if forwarded:
            return _first_forwarded(forwarded)

    if not is_loopback_ip(direct):
        return direct

    for name in _LOOPBACK_PROXY_HEADERS:
        forwarded = headers.get(name)
        if forwarded:
            candidate = _first_forwarded(forwarded)
            if candidate:
                return candidate

    lan = local_lan_ip()
    if not is_loopback_ip(lan):
        return lan
    return direct
