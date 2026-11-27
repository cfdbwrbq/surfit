#!/usr/bin/env bash
# Start the local surface workbench.
set -euo pipefail

cd "$(dirname "$0")"

if [ -z "${SURFIT_BIN:-}" ]; then
  for candidate in \
    "$PWD/../surfit/build-ci/bin" \
    "$PWD/../surfit/build/bin" \
    "$PWD/.site"; do
    if [ -f "$candidate/surfit/__init__.py" ]; then
      export SURFIT_BIN="$candidate"
      break
    fi
  done
fi

if [ -z "${SURFIT_BIN:-}" ]; then
  echo "SURFIT_BIN is not set and no built surfit package was found." >&2
  echo "Try: SURFIT_BIN=/path/to/surfit/build-ci/bin ./run.sh" >&2
  exit 1
fi

PYTHONPATH="$PWD:$PWD/.site:$SURFIT_BIN${PYTHONPATH:+:$PYTHONPATH}" \
  exec python3 -m uvicorn backend.app:app \
  --host "${HOST:-127.0.0.1}" \
  --port "${PORT:-8000}" \
  "$@"
