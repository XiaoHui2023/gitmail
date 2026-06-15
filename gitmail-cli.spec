# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 规格：gitmail onefile 单可执行文件。

构建入口与平台差异见 tools/pack.sh、tools/pack.bat 文件头注释。
"""
from __future__ import annotations

from pathlib import Path

from PyInstaller.building.api import EXE, PYZ
from PyInstaller.building.build_main import Analysis

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


repo_root = _repo_root_from_spec()
entry = repo_root / "src" / "app_main" / "__main__.py"
frontend_dist = repo_root / "frontend" / "dist"

datas = []
if frontend_dist.is_dir():
    datas.append((str(frontend_dist), "frontend/dist"))

a = Analysis(
    [str(entry)],
    pathex=[str(repo_root / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.protocols.websockets.websockets_impl",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "uvicorn.lifespan.off",
        "pydantic_settings",
        "yaml",
        "dotenv",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
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
