from __future__ import annotations

import ipaddress
import re


def ip_matches_pattern(ip: str, pattern: str) -> bool:
    """判断 IP 是否匹配通配符模式（如 192.168.1.*）。"""
    ip = ip.strip()
    pattern = pattern.strip()
    if not ip or not pattern:
        return False
    if pattern == ip:
        return True
    if "*" not in pattern:
        try:
            return ipaddress.ip_address(ip) in ipaddress.ip_network(pattern, strict=False)
        except ValueError:
            return False
    regex = "^" + re.escape(pattern).replace(r"\*", r"\d+") + "$"
    return re.match(regex, ip) is not None


def is_ip_allowed(ip: str, patterns: list[str]) -> bool:
    return any(ip_matches_pattern(ip, p) for p in patterns)
