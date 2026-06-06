from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

from govengine.admission import RuntimeAdmissionResult
from govengine.api import GovApiError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Inspect a GovEngine RuntimeAdmissionResult without executing work.',
    )
    parser.add_argument('record', help='Path to a JSON RuntimeAdmissionResult record.')
    parser.add_argument(
        '--format',
        choices=('text', 'json'),
        default='text',
        help='Output format. Defaults to compact text.',
    )
    parser.add_argument(
        '--show-artifact-refs',
        action='store_true',
        help='Include already-bounded artifact references accepted by the admission validator.',
    )
    return parser


def _read_record(path: Path) -> Mapping[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except OSError as exc:
        raise GovApiError('runtime_admission_read_failed', str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise GovApiError('runtime_admission_json_invalid', exc.msg) from exc
    if not isinstance(payload, Mapping):
        raise GovApiError('runtime_admission_json_not_mapping')
    return payload


def _artifact_ref_count(value: Any) -> int:
    if isinstance(value, Mapping):
        return sum(_artifact_ref_count(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return sum(_artifact_ref_count(item) for item in value)
    return 1 if value not in ('', None) else 0


def _receipt_obligation_status(value: Mapping[str, Any]) -> str:
    if not value:
        return 'missing'
    if value.get('required') is True:
        return 'required'
    status = str(value.get('status') or '').strip()
    if status:
        return status
    if value.get('binds'):
        return 'configured'
    return 'missing'


def _summary(record: RuntimeAdmissionResult, *, show_artifact_refs: bool = False) -> dict[str, Any]:
    summary: dict[str, Any] = {
        'admission_id': record.admission_id,
        'subject_ref': record.subject_ref,
        'status': record.status,
        'allowed': record.allowed,
        'reason_code': record.reason_code,
        'blockers': list(record.blockers),
        'required_next_actions': list(record.required_next_actions),
        'receipt_obligation': _receipt_obligation_status(record.receipt_obligation),
        'artifact_ref_count': _artifact_ref_count(record.artifact_refs),
        'execution': 'not performed',
    }
    if show_artifact_refs:
        summary['artifact_refs'] = dict(record.artifact_refs)
    return summary


def _render_text(summary: Mapping[str, Any]) -> str:
    lines = [
        f"Runtime admission: {summary['admission_id']}",
        f"status: {summary['status']}",
        f"allowed: {str(summary['allowed']).lower()}",
        f"reason_code: {summary['reason_code']}",
        'blockers:',
    ]
    blockers = list(summary.get('blockers') or ())
    lines.extend(f'- {item}' for item in blockers) if blockers else lines.append('- none')
    lines.append('required_next_actions:')
    actions = list(summary.get('required_next_actions') or ())
    lines.extend(f'- {item}' for item in actions) if actions else lines.append('- none')
    lines.extend(
        [
            f"receipt_obligation: {summary['receipt_obligation']}",
            f"artifact_refs: {summary['artifact_ref_count']} bounded refs",
            f"execution: {summary['execution']}",
        ],
    )
    if 'artifact_refs' in summary:
        lines.append('artifact_refs_detail:')
        lines.append(json.dumps(summary['artifact_refs'], sort_keys=True, separators=(',', ':')))
    return '\n'.join(lines) + '\n'


def inspect_runtime_admission(
    path: Path,
    *,
    output_format: str = 'text',
    show_artifact_refs: bool = False,
) -> str:
    record = RuntimeAdmissionResult.from_mapping(_read_record(path))
    summary = _summary(record, show_artifact_refs=show_artifact_refs)
    if output_format == 'json':
        return json.dumps(summary, sort_keys=True, separators=(',', ':')) + '\n'
    return _render_text(summary)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        output = inspect_runtime_admission(
            Path(args.record),
            output_format=args.format,
            show_artifact_refs=args.show_artifact_refs,
        )
    except GovApiError as exc:
        print(f'runtime_admission_inspect_error: {exc.reason_code}', file=sys.stderr)
        return 2
    print(output, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
