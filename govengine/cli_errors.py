from __future__ import annotations

import json
import sys
from typing import Any

CLI_ERROR_SCHEMA = 'govengine.cli_error.v0.1'


def cli_error_payload(
    *,
    error_class: str,
    reason_code: str,
    message: str,
    command: tuple[str, ...],
    safe_next_actions: tuple[str, ...] = (),
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        'schema': CLI_ERROR_SCHEMA,
        'status': 'error',
        'error_class': error_class,
        'reason_code': reason_code,
        'message': message,
        'command': ' '.join(command),
        'argv': list(command),
        'safe_next_actions': list(safe_next_actions),
        'details': dict(details or {}),
        'non_claims': [
            'Does not execute work or recovery actions.',
            'Does not expose raw credentials or private topology.',
            'Details are diagnostic projections only.',
        ],
    }


def cli_error_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def validation_cli_error(
    *,
    command: tuple[str, ...],
    message: str,
    reason_code: str = 'validation_error',
    safe_next_actions: tuple[str, ...] = (),
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return cli_error_payload(
        error_class='validation_error',
        reason_code=reason_code,
        message=message,
        command=command,
        safe_next_actions=safe_next_actions,
        details=details,
    )


def emit_cli_failure(
    *,
    command: tuple[str, ...],
    reason_code: str,
    message: str,
    emit_json: bool,
    legacy_prefix: str,
    error_class: str = 'validation_error',
    safe_next_actions: tuple[str, ...] = (),
    details: dict[str, Any] | None = None,
) -> int:
    if emit_json:
        payload = cli_error_payload(
            error_class=error_class,
            reason_code=reason_code,
            message=message,
            command=command,
            safe_next_actions=safe_next_actions,
            details=details,
        )
        print(cli_error_json(payload))
    else:
        print(f'{legacy_prefix}: {reason_code}', file=sys.stderr)
    return 2


def blocked_cli_error(
    *,
    command: tuple[str, ...],
    message: str,
    reason_code: str,
    safe_next_actions: tuple[str, ...] = (),
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return cli_error_payload(
        error_class='policy_blocked',
        reason_code=reason_code,
        message=message,
        command=command,
        safe_next_actions=safe_next_actions,
        details=details,
    )