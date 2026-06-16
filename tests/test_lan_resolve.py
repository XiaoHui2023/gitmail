from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

from app_main.identity.lan_resolve import _avahi_hostname, _nmblookup_hostname, resolve_lan_hostname


def test_resolve_lan_hostname_prefers_avahi() -> None:
    with (
        patch("app_main.identity.lan_resolve._avahi_hostname", return_value="alice.local"),
        patch("app_main.identity.lan_resolve._nmblookup_hostname") as nmb,
    ):
        host, method = resolve_lan_hostname("192.168.1.10")
    nmb.assert_not_called()
    assert host == "alice.local"
    assert method == "avahi"


def test_resolve_lan_hostname_falls_back_to_nmblookup() -> None:
    with (
        patch("app_main.identity.lan_resolve._avahi_hostname", return_value=""),
        patch(
            "app_main.identity.lan_resolve._nmblookup_hostname",
            return_value="BOB-PC",
        ),
    ):
        host, method = resolve_lan_hostname("192.168.1.11")
    assert host == "BOB-PC"
    assert method == "nmblookup"


def test_avahi_hostname_parses_output() -> None:
    with (
        patch("app_main.identity.lan_resolve.shutil.which", return_value="/usr/bin/avahi-resolve"),
        patch(
            "app_main.identity.lan_resolve._run_command",
            return_value="192.168.1.42\tworkstation.local\n",
        ),
    ):
        assert _avahi_hostname("192.168.1.42") == "workstation.local"


def test_avahi_hostname_uses_bundled_tool(tmp_path: Path) -> None:
    bin_dir = tmp_path / "lan-bin" / "bin"
    bin_dir.mkdir(parents=True)
    tool = bin_dir / "avahi-resolve"
    tool.write_text("", encoding="utf-8")
    with (
        patch.object(sys, "frozen", True, create=True),
        patch.object(sys, "_MEIPASS", str(tmp_path), create=True),
        patch(
            "app_main.identity.lan_resolve._run_command",
            return_value="192.168.1.42\tworkstation.local\n",
        ) as run,
    ):
        assert _avahi_hostname("192.168.1.42") == "workstation.local"
    assert run.call_args[0][0][0] == str(tool)


def test_nmblookup_hostname_parses_output() -> None:
    with (
        patch("app_main.identity.lan_resolve.shutil.which", return_value="/usr/bin/nmblookup"),
        patch(
            "app_main.identity.lan_resolve._run_command",
            return_value=(
                "Looking up status of 192.168.1.50\n"
                "\tWORKGROUP       <00> - <GROUP> B <ACTIVE>\n"
                "\tCAROL-PC        <00> -         B <ACTIVE>\n"
            ),
        ),
    ):
        assert _nmblookup_hostname("192.168.1.50") == "CAROL-PC"
