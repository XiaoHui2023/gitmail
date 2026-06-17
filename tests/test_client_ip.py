from __future__ import annotations

from app_main.identity.client_ip import (
    is_loopback_ip,
    normalize_client_ip,
    resolve_client_ip,
)


def test_is_loopback_ip() -> None:
    assert is_loopback_ip("127.0.0.1")
    assert is_loopback_ip("::1")
    assert is_loopback_ip("localhost")
    assert not is_loopback_ip("192.168.1.10")


def test_normalize_client_ip_ipv6() -> None:
    assert normalize_client_ip("2001:db8::5") == "2001:db8::5"
    assert normalize_client_ip("2001:0db8:0000:0000:0000:0000:0000:0005") == "2001:db8::5"


def test_resolve_client_ip_direct_lan() -> None:
    ip = resolve_client_ip("192.168.1.42", {}, "")
    assert ip == "192.168.1.42"


def test_resolve_client_ip_direct_ipv6() -> None:
    ip = resolve_client_ip("2001:db8::9", {}, "X-Forwarded-For")
    assert ip == "2001:db8::9"


def test_resolve_client_ip_trusted_header_from_proxy() -> None:
    headers = {"X-Forwarded-For": "10.0.0.5, 10.0.0.1"}
    ip = resolve_client_ip("127.0.0.1", headers, "X-Forwarded-For")
    assert ip == "10.0.0.5"


def test_resolve_client_ip_trusted_header_ignored_on_direct_lan() -> None:
    headers = {"X-Forwarded-For": "10.0.0.5"}
    ip = resolve_client_ip("192.168.1.42", headers, "X-Forwarded-For")
    assert ip == "192.168.1.42"


def test_resolve_client_ip_trusted_header_ipv6_from_proxy() -> None:
    headers = {"X-Forwarded-For": "2001:db8::42, ::1"}
    ip = resolve_client_ip("::1", headers, "X-Forwarded-For")
    assert ip == "2001:db8::42"


def test_resolve_client_ip_loopback_uses_proxy_header_without_trust_config() -> None:
    headers = {"X-Forwarded-For": "192.168.2.88"}
    ip = resolve_client_ip("127.0.0.1", headers, "")
    assert ip == "192.168.2.88"


def test_resolve_client_ip_loopback_falls_back_to_lan() -> None:
    ip = resolve_client_ip("127.0.0.1", {}, "")
    assert not is_loopback_ip(ip)
