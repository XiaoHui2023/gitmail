#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -x .venv/bin/python ]]; then
  ./update.sh
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pytest
