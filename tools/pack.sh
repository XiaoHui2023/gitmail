#!/usr/bin/env bash
# 统一打包：构建 frontend/dist、PyInstaller onefile；Linux 默认 staticx，PACK_LINUX_SKIP_STATICX=1 时跳过。
# 每次 pip 对项目与打包工具 --force-reinstall，避免 .venv 残留旧依赖。
#
# 用法（仓库根）：
#   ./tools/pack.sh [src]
#   bash tools/pack.sh [src]
# 产物：dist/gitmail（Linux；默认经 staticx，或 PACK_LINUX_SKIP_STATICX=1 仅 PyInstaller）
#       或 dist/gitmail.exe（Windows）；另有 dist/gitmail-<version>-<platform>.zip 或 .tar.gz。
# Linux staticx 另需系统 patchelf（apt install patchelf）；PACK_LINUX_SKIP_STATICX=1 时跳过 staticx/patchelf。
# GitHub Release CI（ubuntu:16.04）设 PACK_LINUX_SKIP_STATICX=1，见 tools/ci_pack_ubuntu16.sh；
# CI 在宿主机先 npm build，容器内 PACK_SKIP_FRONTEND_BUILD=1 跳过前端。
# CI 前端在 GHA 宿主机 npm build，容器内 PACK_SKIP_FRONTEND_BUILD=1 跳过 npm。
# Linux 打包另须在构建机安装 avahi-utils、samba-common-bin（收集进 onefile，目标机可离线运行）。
# 兼容：单文件 ABI 取决于构建机 glibc；Release 在 Ubuntu 16.04 容器内构建（glibc 2.23）。
# Spec：仓库根 gitmail-cli.spec，二进制名 gitmail。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TARGET="${1:-src}"

ensure_venv() {
  if [[ -f "$ROOT/.venv/bin/python" ]]; then
    PYTHON_CMD=("$ROOT/.venv/bin/python")
  elif [[ -f "$ROOT/.venv/Scripts/python.exe" ]]; then
    PYTHON_CMD=("$ROOT/.venv/Scripts/python.exe")
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
  if [[ "${PACK_SKIP_FRONTEND_BUILD:-}" == "1" ]] && [[ -f "$ROOT/frontend/dist/index.html" ]]; then
    echo "==> 跳过前端构建（PACK_SKIP_FRONTEND_BUILD=1，沿用已有 frontend/dist）"
    return 0
  fi
  echo "==> 构建前端 frontend/dist"
  if ! command -v npm >/dev/null 2>&1; then
    echo "错误: 未找到 npm，无法构建 frontend/dist。" >&2
    exit 1
  fi
  (cd "$ROOT/frontend" && npm install && npm run build)
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

collect_lan_binaries() {
  case "$(uname -s 2>/dev/null || true)" in
    Linux)
      echo "==> 收集局域网解析工具（avahi-resolve、nmblookup）"
      "${PYTHON_CMD[@]}" "$ROOT/tools/collect_lan_binaries.py"
      ;;
  esac
}

build_target() {
  local spec="$ROOT/gitmail-cli.spec"
  if [[ ! -f "$spec" ]]; then
    echo "错误: 未找到 $spec" >&2
    exit 1
  fi
  build_frontend
  collect_lan_binaries
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
    Linux)
      chmod +x "$ROOT/dist/${dist_name}"
      if [[ "${PACK_LINUX_SKIP_STATICX:-}" == "1" ]]; then
        echo "完成: $ROOT/dist/${dist_name}（PACK_LINUX_SKIP_STATICX=1，跳过 staticx）"
      else
        apply_staticx_linux "$dist_name"
      fi
      ;;
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
