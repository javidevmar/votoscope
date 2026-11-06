#!/usr/bin/env bash
# init.sh — executable gate for the SDD harness.
#
# Runs the project setup commands, validates the harness state and runs every
# check configured in harness.config.json. Exit code 0 means the working tree is
# allowed to close a feature.
#
# This file is generic. Put project-specific commands in harness.config.json.

set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -f "$ROOT/.harness/bin/validate.py" ]; then
  VALIDATOR="$ROOT/.harness/bin/validate.py"
elif [ -f "$ROOT/bin/validate.py" ]; then
  VALIDATOR="$ROOT/bin/validate.py"
else
  echo "[FAIL]  validate.py not found (looked in .harness/bin and bin)" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "[FAIL]  python3 not found; install Python 3.10+" >&2
  exit 1
fi

exec python3 "$VALIDATOR" "$ROOT" --run-checks "$@"
