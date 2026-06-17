#!/usr/bin/env bash
# GitHub Actions：在 Ubuntu 16.04（glibc 2.23）容器内执行 PyInstaller 打包，跳过 staticx。
# 由 .github/workflows/release.yml 通过 docker run 调用；勿在 GHA ubuntu-latest 宿主机直接 apt。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

rm -rf .venv build dist

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq wget bzip2 ca-certificates binutils \
  avahi-utils samba-common-bin

NODE_VERSION="20.18.0"
NODE_DIR="/opt/node"
if [[ ! -x "$NODE_DIR/bin/npm" ]]; then
  for attempt in 1 2 3 4 5; do
    if wget -q "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" \
      -O /tmp/node.tar.xz; then
      break
    fi
    if [[ "$attempt" -eq 5 ]]; then
      echo "错误: 下载 Node.js 失败。" >&2
      exit 1
    fi
    sleep 5
  done
  mkdir -p "$NODE_DIR"
  tar -xJf /tmp/node.tar.xz -C "$NODE_DIR" --strip-components=1
fi
export PATH="$NODE_DIR/bin:$PATH"

MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-py311_23.11.0-2-Linux-x86_64.sh"
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
npm -v

export PACK_LINUX_SKIP_STATICX=1
bash tools/pack.sh src
