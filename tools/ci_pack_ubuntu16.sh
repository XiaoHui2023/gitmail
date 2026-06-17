#!/usr/bin/env bash
# GitHub Actions：在 Ubuntu 16.04（glibc 2.23）容器内执行 PyInstaller 打包。
# 前端须在 GHA ubuntu-latest 宿主机先 npm build（Vite 6 / Node 20 无法在 xenial 内运行）。
# 由 release.yml 通过 docker run 调用。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f "$ROOT/frontend/dist/index.html" ]]; then
  echo "错误: 缺少 frontend/dist，请在 docker 外先 npm run build。" >&2
  exit 1
fi

rm -rf .venv build dist

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq wget bzip2 ca-certificates binutils xz-utils \
  avahi-utils samba-common-bin

MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-py310_23.5.2-0-Linux-x86_64.sh"
MINICONDA_SH="/tmp/miniconda.sh"
if [[ ! -x /opt/miniconda/bin/python ]]; then
  for attempt in 1 2 3 4 5; do
    if wget -q "$MINICONDA_URL" -O "$MINICONDA_SH"; then
      break
    fi
    if [[ "$attempt" -eq 5 ]]; then
      echo "错误: 下载 Miniconda 失败。" >&2
      exit 1
    fi
    sleep 5
  done
  bash "$MINICONDA_SH" -b -p /opt/miniconda
fi
export PATH="/opt/miniconda/bin:$PATH"

python -V

export PACK_SKIP_FRONTEND_BUILD=1
bash tools/pack.sh src
