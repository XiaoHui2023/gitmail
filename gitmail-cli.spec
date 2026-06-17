# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 规格：gitmail onefile 单可执行文件。

构建入口与平台差异见 tools/pack.sh、tools/pack.bat 文件头注释。
Linux 打包前由 tools/collect_lan_binaries.py 收集 avahi-resolve / nmblookup。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from PyInstaller.building.api import EXE, PYZ
from PyInstaller.building.build_main import Analysis
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None


def _repo_root_from_spec() -> Path:
    """SPECPATH 常为相对路径；从 spec 所在目录与 cwd 双向向上找含 pyproject.toml 的仓库根。"""
    spec = Path(SPECPATH).resolve()
    seeds = [spec.parent]
    try:
        seeds.append(Path.cwd().resolve())
    except OSError:
        pass
    for seed in seeds:
        for base in [seed, *seed.parents]:
            if (base / "pyproject.toml").is_file() and (
                base / "src" / "app_main" / "__main__.py"
            ).is_file():
                return base
    return spec.parent


def _sqlite_binaries() -> list[tuple[str, str]]:
    """把构建环境的 libsqlite3 打进 onefile，避免目标机旧系统库缺 sqlite3_trace_v2。"""
    lib_dirs: list[Path] = []
    conda_prefix = os.environ.get("CONDA_PREFIX")
    if conda_prefix:
        lib_dirs.append(Path(conda_prefix) / "lib")
    lib_dirs.append(Path(sys.executable).resolve().parent.parent / "lib")
    for lib_dir in lib_dirs:
        for name in ("libsqlite3.so.0", "libsqlite3.so"):
            candidate = lib_dir / name
            if candidate.is_file():
                return [(str(candidate.resolve()), ".")]
    return []


def _lan_binaries(repo_root: Path) -> list[tuple[str, str]]:
    root = repo_root / "build" / "lan-bin" / "linux"
    if not root.is_dir():
        return []
    out: list[tuple[str, str]] = []
    bin_dir = root / "bin"
    for name in ("avahi-resolve", "nmblookup"):
        tool = bin_dir / name
        if tool.is_file():
            out.append((str(tool), "lan-bin/bin"))
    lib_dir = root / "lib"
    if lib_dir.is_dir():
        for lib in sorted(lib_dir.iterdir()):
            if lib.is_file():
                out.append((str(lib), "lan-bin/lib"))
    return out


repo_root = _repo_root_from_spec()
entry = repo_root / "src" / "app_main" / "__main__.py"
frontend_dist = repo_root / "frontend" / "dist"

datas: list[tuple[str, str]] = []
if frontend_dist.is_dir():
    datas.append((str(frontend_dist), "frontend/dist"))

hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    "pydantic_settings",
    "yaml",
    "dotenv",
    "httptools",
    "websockets",
    "websockets.legacy",
    "websockets.legacy.server",
    "watchfiles",
    "anyio",
    "anyio._backends._asyncio",
    "sniffio",
    "email.mime.multipart",
    "email.mime.text",
]
hiddenimports += collect_submodules("app_main")
hiddenimports += collect_submodules("uvicorn")
hiddenimports += collect_submodules("starlette")
hiddenimports += collect_submodules("fastapi")

runtime_hooks = [str(repo_root / "tools" / "pyi_rth_lan_bin.py")]

a = Analysis(
    [str(entry)],
    pathex=[str(repo_root / "src")],
    binaries=_lan_binaries(repo_root) + _sqlite_binaries(),
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=runtime_hooks,
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="gitmail",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
