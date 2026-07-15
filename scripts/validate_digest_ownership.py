#!/usr/bin/env python3
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from govengine._digest_ownership import validate_digest_ownership_inventory  # noqa: E402


def main() -> int:
    inventory = validate_digest_ownership_inventory()
    counts = Counter(item.mode for item in inventory)
    summary = ','.join(f'{mode}={counts[mode]}' for mode in sorted(counts))
    print(f'digest_ownership_ok:bindings={len(inventory)}:{summary}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
