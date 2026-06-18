from __future__ import annotations

from unittest.mock import patch

from app_main.identity.lan_resolve import hostname_to_username
from app_main.identity.user_resolver import resolve_username


def test_hostname_to_username_strips_suffixes() -> None:
    assert hostname_to_username("alice-pc.corp.example.com") == "alice"
    assert hostname_to_username("bob-laptop.local") == "bob"
    assert hostname_to_username("carol-desktop") == "carol"


def test_resolve_username_map_wins() -> None:
    with patch("app_main.identity.user_resolver.resolve_lan_hostname") as lan:
        username, method = resolve_username("192.168.1.10", {"192.168.1.10": "mapped"})
    lan.assert_not_called()
    assert username == "mapped"
    assert method == "map"


def test_resolve_username_avahi() -> None:
    with patch(
        "app_main.identity.user_resolver.resolve_lan_hostname",
        return_value=("alice-pc.local", "avahi"),
    ):
        username, method = resolve_username("192.168.1.11", {})
    assert username == "alice"
    assert method == "avahi"


def test_resolve_username_nmblookup() -> None:
    with patch(
        "app_main.identity.user_resolver.resolve_lan_hostname",
        return_value=("BOB-PC", "nmblookup"),
    ):
        username, method = resolve_username("192.168.1.12", {})
    assert username == "BOB-PC"
    assert method == "nmblookup"


def test_resolve_username_extracts_email_prefix() -> None:
    with patch(
        "app_main.identity.user_resolver.resolve_lan_hostname",
        return_value=("user-Lenovo", "nmblookup"),
    ):
        username, method = resolve_username("192.168.1.12", {}, [r"^([^-]+)-"])
    assert username == "user"
    assert method == "nmblookup"


def test_resolve_username_uses_original_when_extract_misses() -> None:
    with patch(
        "app_main.identity.user_resolver.resolve_lan_hostname",
        return_value=("user-Lenovo", "nmblookup"),
    ):
        username, method = resolve_username("192.168.1.12", {}, [r"^pc-(.+)$"])
    assert username == "user-Lenovo"
    assert method == "nmblookup"


def test_resolve_username_none() -> None:
    with patch(
        "app_main.identity.user_resolver.resolve_lan_hostname",
        return_value=("", ""),
    ):
        username, method = resolve_username("192.168.1.13", {})
    assert username == "unknown"
    assert method == "none"
