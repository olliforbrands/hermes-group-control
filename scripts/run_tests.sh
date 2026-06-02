#!/usr/bin/env bash
set -euo pipefail

HERMES_AGENT="${HERMES_AGENT:-$HOME/.hermes/hermes-agent}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY="$HERMES_AGENT/venv/bin/python3"

if [[ ! -x "$PY" ]]; then
  echo "Hermes venv not found at $PY" >&2
  exit 1
fi

cd "$HERMES_AGENT"
TEST_FILE="$HERMES_AGENT/tests/plugins/test_group_control.py"
if [[ ! -f "$TEST_FILE" ]]; then
  cp "$REPO/tests/test_group_control.py" "$TEST_FILE"
fi
exec "$PY" -m pytest "$TEST_FILE" -v "$@"
