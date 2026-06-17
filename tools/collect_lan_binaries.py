"""Pack-time: copy avahi-resolve / nmblookup and ldd shared libs into build/lan-bin/linux.

Samba 等系统包自带的 .so 常带 DT_RUNPATH；staticx 无法修改 PyInstaller 归档内的库，
须在打入 onefile 前用 patchelf 去掉 RPATH/RUNPATH（见 staticx issue #188）。
"""

from __future__ import annotations

import pathlib
import platform
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "build" / "lan-bin" / "linux"
OUT_BIN = OUT_ROOT / "bin"
OUT_LIB = OUT_ROOT / "lib"

LAN_TOOLS = ("avahi-resolve", "nmblookup")


def main() -> int:
    if platform.system() != "Linux":
        print("跳过局域网工具收集（仅 Linux 打包需要）。")
        return 0

    if not shutil.which("patchelf"):
        print(
            "错误: Linux 打包需要 patchelf（清理 samba 库的 RUNPATH，供 staticx 使用）。"
            "请安装: sudo apt install patchelf",
            file=sys.stderr,
        )
        return 1

    missing = [name for name in LAN_TOOLS if not shutil.which(name)]
    if missing:
        print(
            "错误: 构建机缺少 "
            + "、".join(missing)
            + "。请安装: sudo apt install avahi-utils samba-common-bin",
            file=sys.stderr,
        )
        return 1

    if OUT_ROOT.exists():
        shutil.rmtree(OUT_ROOT)
    OUT_BIN.mkdir(parents=True)
    OUT_LIB.mkdir(parents=True)

    seen_libs: set[str] = set()
    for name in LAN_TOOLS:
        src = pathlib.Path(shutil.which(name) or "")
        dest = OUT_BIN / name
        shutil.copy2(src, dest)
        dest.chmod(0o755)
        _strip_rpath(dest)
        _collect_ldd_libs(src, seen_libs)

    print(f"完成: {OUT_ROOT}（{len(LAN_TOOLS)} 个工具，{len(seen_libs)} 个共享库）")
    return 0


def _strip_rpath(path: pathlib.Path) -> None:
    """Remove DT_RPATH/DT_RUNPATH so staticx accepts PyInstaller-bundled libs."""
    try:
        proc = subprocess.run(
            ["patchelf", "--remove-rpath", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        print(f"错误: patchelf 执行失败 ({path}): {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        print(
            f"错误: patchelf --remove-rpath 失败 ({path})"
            + (f": {detail}" if detail else ""),
            file=sys.stderr,
        )
        raise SystemExit(1)


def _collect_ldd_libs(binary: pathlib.Path, seen: set[str]) -> None:
    try:
        proc = subprocess.run(
            ["ldd", str(binary)],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return
    for line in proc.stdout.splitlines():
        if "=>" not in line:
            continue
        _, rhs = line.split("=>", 1)
        lib_path = rhs.split("(")[0].strip()
        if not lib_path.startswith("/"):
            continue
        lib = pathlib.Path(lib_path)
        if not lib.is_file() or lib_path in seen:
            continue
        seen.add(lib_path)
        dest = OUT_LIB / lib.name
        shutil.copy2(lib, dest)
        _strip_rpath(dest)


if __name__ == "__main__":
    raise SystemExit(main())
