#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-}"
if [[ -z "$PYTHON" && -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
elif [[ -z "$PYTHON" ]]; then
  PYTHON=python3
fi

GATE_REPORT=()

record_gate() {
  local name="$1"
  local status="$2"
  GATE_REPORT+=("${name}=${status}")
}

run_step() {
  local name="$1"
  shift
  echo "==> ${name}"
  if "$@"; then
    record_gate "$name" OK
  else
    record_gate "$name" FAIL
    echo "gate_fail:${name}" >&2
    exit 1
  fi
}

run_step public_truth "$PYTHON" scripts/validate_public_truth.py
run_step api_stability "$PYTHON" scripts/validate_api_stability.py
run_step alpha_readiness "$PYTHON" scripts/validate_alpha_readiness.py
run_step g3_receipt_conformance "$PYTHON" scripts/validate_g3_receipt_conformance_gate.py
run_step ruff "$PYTHON" -m ruff check .
run_step mypy "$PYTHON" -m mypy govengine
run_step pytest "$PYTHON" -m pytest -q

printf 'GATE_REPORT: %s\n' "$(IFS=' '; echo "${GATE_REPORT[*]}")"
echo ci_parity_checks_ok
