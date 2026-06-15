#!/usr/bin/env bash
# 统一打包：构建 frontend/dist、PyInstaller onefile、Linux 再 staticx。
# 每次 pip 对项目与打包工具 --force-reinstall，避免 .venv 残留旧依赖。
#
# 用法（仓库根）：
#   ./tools/pack.sh [src]
#   bash tools/pack.sh [src]
# 产物：dist/gitmail（Linux 经 staticx）或 dist/gitmail.exe（Windows）；
#       另有 dist/gitmail-<version>-<platform>.zip 或 .tar.gz（见 tools/bundle_release.py）。
# Linux staticx 另需系统 patchelf（如 apt install patchelf）；macOS 跳过 staticx。
# 兼容：单文件 ABI 取决于构建机 glibc；旧 Linux 须在目标机实测 staticx 产物。
# Spec：仓库根 gitmail-cli.spec，二进制名 gitmail。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TARGET="${1:-src}"

ensure_venv() {
  if [[ -f "$ROOT/.venv/Scripts/python.exe" ]]; then
    PYTHON_CMD=("$ROOT/.venv/Scripts/python.exe")
  elif [[ -f "$ROOT/.venv/bin/python" ]]; then
    PYTHON_CMD=("$ROOT/.venv/bin/python")
  else
    echo "未找到 .venv，正在创建 ..."
    case "$(uname -s 2>/dev/null || true)" in
      MINGW*|MSYS*|CYGWIN*|Windows_NT)
        if command -v py >/dev/null 2>&1; then
          py -3 -m venv "$ROOT/.venv"
        else
          python -m venv "$ROOT/.venv"
        fi
        PYTHON_CMD=("$ROOT/.venv/Scripts/python.exe")
        ;;
      *)
        if ! command -v python3 >/dev/null 2>&1; then
          echo "错误: 需要 python3 以创建 .venv。" >&2
          exit 1
        fi
        python3 -m venv "$ROOT/.venv"
        PYTHON_CMD=("$ROOT/.venv/bin/python")
        ;;
    esac
  fi
  echo "==> 使用虚拟环境: ${PYTHON_CMD[*]} ($("${PYTHON_CMD[@]}" -V 2>/dev/null || true))"
}

build_frontend() {
  if [[ ! -d "$ROOT/frontend/dist" ]]; then
    echo "==> 构建前端 frontend/dist"
    if ! command -v npm >/dev/null 2>&1; then
      echo "错误: 未找到 npm，无法构建 frontend/dist。" >&2
      exit 1
    fi
    (cd "$ROOT/frontend" && npm install && npm run build)
  else
    echo "==> 已存在 frontend/dist，跳过 npm build（删除 dist 可强制重建）"
  fi
}

apply_staticx_linux() {
  local dist_name="$1"
  local pyi_out="$ROOT/dist/${dist_name}"
  if [[ ! -f "$pyi_out" ]]; then
    return 0
  fi
  if ! command -v patchelf >/dev/null 2>&1; then
    echo "错误: Linux 下 staticx 需要系统命令 patchelf（例如: sudo apt install patchelf）。" >&2
    exit 1
  fi
  "${PYTHON_CMD[@]}" -m pip install -q --upgrade --force-reinstall staticx
  local staticx="$ROOT/.venv/bin/staticx"
  if [[ ! -x "$staticx" ]]; then
    echo "错误: 未找到可执行的 .venv/bin/staticx。" >&2
    exit 1
  fi
  local tmp_out="$ROOT/dist/.${dist_name}-staticx.tmp"
  rm -f "$tmp_out"
  echo "==> staticx: $pyi_out -> $dist_name"
  "$staticx" "$pyi_out" "$tmp_out"
  mv -f "$tmp_out" "$pyi_out"
  chmod +x "$pyi_out"
  echo "完成: $pyi_out（staticx 自解压包；请在目标机实测）"
}

build_target() {
  local spec="$ROOT/gitmail-cli.spec"
  if [[ ! -f "$spec" ]]; then
    echo "错误: 未找到 $spec" >&2
    exit 1
  fi
  build_frontend
  echo "==> PyInstaller: $spec"
  "${PYTHON_CMD[@]}" -m PyInstaller --clean --noconfirm "$spec"
  local dist_name="gitmail"
  if [[ -f "$ROOT/dist/${dist_name}.exe" ]]; then
    echo "完成: $ROOT/dist/${dist_name}.exe（Windows：无 staticx 步骤）"
    return 0
  fi
  if [[ ! -f "$ROOT/dist/${dist_name}" ]]; then
    echo "错误: 未在 dist 找到 ${dist_name} 或 ${dist_name}.exe。" >&2
    exit 1
  fi
  case "$(uname -s 2>/dev/null || true)" in
    Linux) apply_staticx_linux "$dist_name" ;;
    *) echo "完成: $ROOT/dist/${dist_name}（非 Linux，跳过 staticx）" ;;
  esac
}

ensure_venv

"${PYTHON_CMD[@]}" -m pip install -q -U pip setuptools wheel
"${PYTHON_CMD[@]}" -m pip install -q --upgrade --force-reinstall -e .
"${PYTHON_CMD[@]}" -m pip install -q --upgrade --force-reinstall "pyinstaller>=6.0"

rm -rf "$ROOT/build" "$ROOT/dist"

case "$TARGET" in
  src|"")
    build_target
    echo "==> 组装发布压缩包"
    "${PYTHON_CMD[@]}" "$ROOT/tools/bundle_release.py"
    ;;
  *)
    echo "用法: ./tools/pack.sh [src]" >&2
    exit 1
    ;;
esac

echo "PyInstaller 输出目录: $ROOT/dist"
