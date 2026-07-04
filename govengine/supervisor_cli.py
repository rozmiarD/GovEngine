from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from govengine.api import GovApiError
from govengine.supervisor_explain import explain_supervisor_action

DEFAULT_MAX_BYTES = 256 * 1024


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='govengine-supervisor',
        description='Explain GovEngine supervisor action admission without executing recovery.',
    )
    sub = parser.add_subparsers(dest='command', required=True)

    explain = sub.add_parser(
        'explain',
        help='Evaluate a supervisor action request and emit a stable explanation JSON.',
    )
    explain.add_argument('request', type=Path, help='SupervisorActionRequest JSON file.')
    explain.add_argument('--json', action='store_true', help='Emit machine-readable JSON.')
    explain.add_argument('--max-bytes', type=int, default=DEFAULT_MAX_BYTES)
    return parser


def _read_json_mapping(path: Path, *, max_bytes: int) -> dict[str, Any]:
    try:
        if max_bytes <= 0:
            raise GovApiError('supervisor_request_invalid_max_bytes')
        raw = path.read_bytes()
        if len(raw) > max_bytes:
            raise GovApiError('supervisor_request_input_too_large')
        data = json.loads(raw.decode('utf-8'))
    except GovApiError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GovApiError('supervisor_request_json_invalid', str(exc)) from exc
    if not isinstance(data, dict):
        raise GovApiError('supervisor_request_json_not_mapping')
    return {str(key): data[key] for key in data}


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == 'explain':
            request = _read_json_mapping(args.request, max_bytes=args.max_bytes)
            explanation = explain_supervisor_action(request)
            payload = explanation.as_dict()
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                print(
                    f"supervisor_explain_{payload['status']}:"
                    f"{payload['action']}:{payload['outcome']}:"
                    f"reason={payload['reason_code']}"
                )
            return 0 if payload['status'] == 'explained' else 2
    except GovApiError as exc:
        reason = getattr(exc, 'reason_code', str(exc))
        print(f'supervisor_authoring_error: {reason}', file=sys.stderr)
        return 2
    return 2


if __name__ == '__main__':
    raise SystemExit(main())