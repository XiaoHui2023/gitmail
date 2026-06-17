from __future__ import annotations

import ipaddress
import socket
from collections.abc import Mapping

_LOOPBACK_PROXY_HEADERS = ("X-Forwarded-For", "X-Real-IP")
_IPV6_LAN_PROBE = ("2001:4860:4860::8888", 80)


def normalize_client_ip(ip: str) -> str:
    """规范化为 ipaddress 标准字符串；非法输入原样返回。"""
    text = ip.strip()
    if not text:
        return text
    if "%" in text:
        text = text.split("%", 1)[0]
    try:
        return str(ipaddress.ip_address(text))
    except ValueError:
        return ip.strip()


def is_loopback_ip(ip: str) -> bool:
    """判断是否为回环地址。"""
    if ip.strip().lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalize_client_ip(ip)).is_loopback
    except ValueError:
        return False


def is_proxy_peer_ip(ip: str) -> bool:
    """判断直连对端是否为反向代理（本机回环）。"""
    try:
        addr = ipaddress.ip_address(normalize_client_ip(ip))
    except ValueError:
        return False
    return addr.is_loopback


def local_lan_ip() -> str:
    """取本机对外通信常用的局域网地址（优先 IPv4，否则 IPv6）。"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return normalize_client_ip(sock.getsockname()[0])
    except OSError:
        pass
    try:
        with socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as sock:
            sock.connect(_IPV6_LAN_PROBE)
            return normalize_client_ip(sock.getsockname()[0])
    except OSError:
        pass
    return "127.0.0.1"


def _first_forwarded(value: str) -> str:
    return normalize_client_ip(value.split(",")[0])


def _header_value(headers: Mapping[str, str], name: str) -> str | None:
    if not name:
        return None
    value = headers.get(name)
    if value:
        return value
    lower = name.lower()
    for key, item in headers.items():
        if key.lower() == lower:
            return item
    return None


def resolve_client_ip(
    direct_host: str | None,
    headers: Mapping[str, str],
    trusted_proxy_header: str,
) -> str:
    """解析来访客户端 IP，回环连接时尽量还原真实客户端身份。

    ``trusted_proxy_header`` 仅在直连对端为反向代理（回环）时采信，避免
    客户端伪造该头；经代理访问时优先读配置头，再回退常见代理头。
    """
    direct = normalize_client_ip((direct_host or "127.0.0.1").strip())
    trusted = trusted_proxy_header.strip()
    behind_proxy = is_proxy_peer_ip(direct)

    if behind_proxy:
        if trusted:
            forwarded = _header_value(headers, trusted)
            if forwarded:
                return _first_forwarded(forwarded)
        for name in _LOOPBACK_PROXY_HEADERS:
            forwarded = _header_value(headers, name)
            if forwarded:
                candidate = _first_forwarded(forwarded)
                if candidate:
                    return candidate

    if not is_loopback_ip(direct):
        return direct

    lan = local_lan_ip()
    if not is_loopback_ip(lan):
        return lan
    return direct
