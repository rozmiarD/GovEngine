#!/usr/bin/env python3
"""Run the canonical G3 receipt binding and postcondition gate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', '-q', 'tests/test_receipt_conformance.py'],
        cwd=ROOT,
        check=False,
    )
    if result.returncode:
        return result.returncode
    print(
        'g3_receipt_conformance_gate_ok:decision_binding=OK:'
        'runtime_permit_binding=OK:attempt_lease_inventory_binding=OK:'
        'output_digest_postcondition=OK:output_limit_postcondition=OK'
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
