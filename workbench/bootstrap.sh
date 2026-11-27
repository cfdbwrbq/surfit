#!/usr/bin/env bash
# Install the workbench's Python dependencies into .site.
set -euo pipefail
cd "$(dirname "$0")"
python3 -m pip install --target "$PWD/.site" -r requirements.txt
