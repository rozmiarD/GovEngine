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

from govengine.admission import RuntimeAdmissionResult  # noqa: E402
from govengine.api import GovApiError, require_mapping  # noqa: E402
from govengine.execution.runner_protocol import (  # noqa: E402
    GovRunnerRequest,
    normalize_runner_steps,
)
from govengine.execution.supervision import validate_runner_receipt_binding  # noqa: E402


class JsonInputError(Exception):
    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Verify a GovEngine runner receipt binding without executing work.',
    )
    parser.add_argument('--request', required=True, help='Path to a JSON GovRunnerRequest record.')
    parser.add_argument('--receipt', required=True, help='Path to a JSON GovRunnerReceipt record.')
    parser.add_argument(
        '--admission',
        help='Optional path to a JSON RuntimeAdmissionResult record used for id/digest comparison.',
    )
    parser.add_argument('--admission-id', default='', help='Expected admission id when no admission file is supplied.')
    parser.add_argument(
        '--admission-digest',
        default='',
        help='Expected admission digest when no admission file is supplied.',
    )
    parser.add_argument('--ticket-id', default='', help='Expected execution ticket id.')
    parser.add_argument('--ticket-digest', default='', help='Expected execution ticket digest.')
    parser.add_argument(
        '--format',
        choices=('text', 'json'),
        default='text',
        help='Output format. Defaults to compact text.',
    )
    return parser


def _read_json(path: Path, *, reason_prefix: str) -> Mapping[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except OSError as exc:
        raise JsonInputError(f'{reason_prefix}_read_failed') from exc
    except json.JSONDecodeError as exc:
        raise JsonInputError(f'{reason_prefix}_json_invalid') from exc
    if not isinstance(payload, Mapping):
        raise JsonInputError(f'{reason_prefix}_json_not_mapping')
    return payload


def _request_from_mapping(value: Mapping[str, Any]) -> GovRunnerRequest:
    raw = require_mapping(value, reason_code='invalid_runner_request')
    return GovRunnerRequest(
        request_id=str(raw.get('request_id') or '').strip(),
        source=str(raw.get('source') or '').strip(),
        steps=normalize_runner_steps(tuple(raw.get('steps') or ())),
        approved_execution_spec=raw.get('approved_execution_spec')
        if isinstance(raw.get('approved_execution_spec'), Mapping)
        else {},
        execution_ticket_gate=raw.get('execution_ticket_gate')
        if isinstance(raw.get('execution_ticket_gate'), Mapping)
        else {},
        dry_run=bool(raw.get('dry_run', True)),
    )


def _summary(receipt: Mapping[str, Any], *, reason_code: str = 'verified', verified: bool = True) -> dict[str, Any]:
    binding = receipt.get('binding') if isinstance(receipt.get('binding'), Mapping) else {}
    blockers: list[str] = [] if verified else [reason_code]
    return {
        'status': 'verified' if verified else 'failed',
        'verified': verified,
        'reason_code': reason_code,
        'blockers': blockers,
        'request_id': str(receipt.get('request_id') or ''),
        'receipt_status': str(receipt.get('status') or ''),
        'admission_id': str(binding.get('admission_id') or ''),
        'ticket_id': str(binding.get('ticket_id') or ''),
        'execution': 'not performed',
    }


def _render_text(summary: Mapping[str, Any]) -> str:
    lines = [
        f"receipt_binding: {summary['status']}",
        f"verified: {str(summary['verified']).lower()}",
        f"reason_code: {summary['reason_code']}",
        f"request_id: {summary.get('request_id', '')}",
        f"receipt_status: {summary.get('receipt_status', '')}",
        f"admission_id: {summary.get('admission_id', '')}",
        f"ticket_id: {summary.get('ticket_id', '')}",
        'blockers:',
    ]
    blockers = list(summary.get('blockers') or ())
    lines.extend(f'- {item}' for item in blockers) if blockers else lines.append('- none')
    lines.append(f"execution: {summary['execution']}")
    return '\n'.join(lines) + '\n'


def _render(summary: Mapping[str, Any], *, output_format: str) -> str:
    if output_format == 'json':
        return json.dumps(summary, sort_keys=True, separators=(',', ':')) + '\n'
    return _render_text(summary)


def verify_runner_receipt_binding_file(
    *,
    request_path: Path,
    receipt_path: Path,
    admission_path: Path | None = None,
    admission_id: str = '',
    admission_digest: str = '',
    ticket_id: str = '',
    ticket_digest: str = '',
    output_format: str = 'text',
) -> tuple[int, str]:
    request_payload = _read_json(request_path, reason_prefix='runner_request')
    receipt_payload = _read_json(receipt_path, reason_prefix='runner_receipt')

    try:
        admission = None
        if admission_path is not None:
            admission = RuntimeAdmissionResult.from_mapping(
                _read_json(admission_path, reason_prefix='runtime_admission'),
            )
        request = _request_from_mapping(request_payload)
        validate_runner_receipt_binding(
            request,
            receipt_payload,
            admission=admission.as_dict() if admission is not None else None,
            admission_id=admission_id,
            admission_digest=admission_digest,
            ticket_id=ticket_id,
            ticket_digest=ticket_digest,
        )
    except GovApiError as exc:
        return 1, _render(_summary(receipt_payload, reason_code=exc.reason_code, verified=False), output_format=output_format)
    return 0, _render(_summary(receipt_payload), output_format=output_format)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        code, output = verify_runner_receipt_binding_file(
            request_path=Path(args.request),
            receipt_path=Path(args.receipt),
            admission_path=Path(args.admission) if args.admission else None,
            admission_id=args.admission_id,
            admission_digest=args.admission_digest,
            ticket_id=args.ticket_id,
            ticket_digest=args.ticket_digest,
            output_format=args.format,
        )
    except JsonInputError as exc:
        summary = {
            'status': 'failed',
            'verified': False,
            'reason_code': exc.reason_code,
            'blockers': [exc.reason_code],
            'execution': 'not performed',
        }
        print(_render(summary, output_format=args.format), end='')
        return 2
    print(output, end='')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
