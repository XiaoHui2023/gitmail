from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

_LAN_CMD_TIMEOUT_SECONDS = 3


def resolve_lan_hostname(ip: str) -> tuple[str, str]:
    """用局域网工具按 IP 查主机名。

    Returns:
        (主机名, 方式)；未解析到时为 ("", "")。方式取 avahi 或 nmblookup。
    """
    for method, resolver in (
        ("avahi", _avahi_hostname),
        ("nmblookup", _nmblookup_hostname),
    ):
        host = resolver(ip)
        if host:
            return host, method
    return "", ""


def hostname_to_username(host: str) -> str:
    """从主机名截取登录名，去掉常见设备后缀。"""
    short = host.split(".")[0]
    for suffix in ("-pc", "-laptop", "-desktop"):
        if short.endswith(suffix):
            short = short[: -len(suffix)]
            break
    if short.endswith(".local"):
        short = short[: -len(".local")]
    return short


def _run_command(args: list[str]) -> str:
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=_LAN_CMD_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if proc.returncode != 0:
        return ""
    return proc.stdout


def _tool_path(name: str) -> str | None:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        bundled = Path(sys._MEIPASS) / "lan-bin" / "bin" / name
        if bundled.is_file():
            return str(bundled)
    return shutil.which(name)


def _avahi_hostname(ip: str) -> str:
    tool = _tool_path("avahi-resolve")
    if not tool:
        return ""
    out = _run_command([tool, "-a", ip])
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 2:
            return parts[1]
    return ""


def _nmblookup_hostname(ip: str) -> str:
    tool = _tool_path("nmblookup")
    if not tool:
        return ""
    out = _run_command([tool, "-A", ip])
    for line in out.splitlines():
        if "<00>" not in line or "<GROUP>" in line:
            continue
        parts = line.split()
        if parts:
            return parts[0]
    return ""
