#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from govengine.admission import JsonlAuditLedgerAdapter  # noqa: E402
from govengine.api import GovApiError  # noqa: E402


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Verify a development JSONL audit ledger without appending or rewriting it.',
    )
    parser.add_argument('ledger', help='Path to a JSONL audit ledger.')
    parser.add_argument(
        '--limit',
        type=int,
        default=1000,
        help='Maximum entries to read. Defaults to 1000.',
    )
    parser.add_argument(
        '--format',
        choices=('text', 'json'),
        default='text',
        help='Output format. Defaults to compact text.',
    )
    return parser


def _summary(
    *,
    status: str,
    verified: bool,
    reason_code: str,
    blockers: tuple[str, ...] = (),
    checked_entries: int = 0,
    last_entry_id: str = '',
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        'status': status,
        'verified': verified,
        'reason_code': reason_code,
        'blockers': list(blockers),
        'checked_entries': checked_entries,
        'last_entry_id': last_entry_id,
        'context': dict(context or {}),
        'writes': 'none',
    }


def _render_text(summary: Mapping[str, Any]) -> str:
    lines = [
        f"audit_ledger: {summary['status']}",
        f"verified: {str(summary['verified']).lower()}",
        f"reason_code: {summary['reason_code']}",
        f"checked_entries: {summary['checked_entries']}",
        f"last_entry_id: {summary['last_entry_id']}",
        'blockers:',
    ]
    blockers = list(summary.get('blockers') or ())
    lines.extend(f'- {item}' for item in blockers) if blockers else lines.append('- none')
    lines.append(f"writes: {summary['writes']}")
    return '\n'.join(lines) + '\n'


def _render(summary: Mapping[str, Any], *, output_format: str) -> str:
    if output_format == 'json':
        return json.dumps(summary, sort_keys=True, separators=(',', ':')) + '\n'
    return _render_text(summary)


def verify_audit_ledger_file(path: Path, *, limit: int = 1000, output_format: str = 'text') -> tuple[int, str]:
    if limit < 1:
        summary = _summary(
            status='failed',
            verified=False,
            reason_code='invalid_audit_ledger_read_limit',
            blockers=('invalid_audit_ledger_read_limit',),
        )
        return 2, _render(summary, output_format=output_format)
    ledger = JsonlAuditLedgerAdapter(path)
    try:
        entries = ledger.read(limit=limit)
        result = ledger.verify(entries)
    except GovApiError as exc:
        summary = _summary(
            status='failed',
            verified=False,
            reason_code=exc.reason_code,
            blockers=(exc.reason_code,),
            context=exc.context,
        )
        return 1, _render(summary, output_format=output_format)
    summary = _summary(
        status=result.status,
        verified=result.verified,
        reason_code=result.reason_code,
        blockers=result.blockers,
        checked_entries=result.checked_entries,
        last_entry_id=result.last_entry_id,
    )
    return (0 if result.verified else 1), _render(summary, output_format=output_format)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    code, output = verify_audit_ledger_file(Path(args.ledger), limit=args.limit, output_format=args.format)
    print(output, end='')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
