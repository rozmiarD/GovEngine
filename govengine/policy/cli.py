from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from govengine.api import GovApiError
from govengine.policy.authoring import (
    DEFAULT_POLICY_MAX_BYTES,
    read_policy_pack,
    render_policy_pack_json,
    validate_policy_pack,
)
from govengine.policy.baselines import available_baseline_policy_names, baseline_policy_pack
from govengine.policy.explain import explain_policy_evaluation
from govengine.policy.schema import POLICY_SCHEMA_KINDS, policy_json_schema
from govengine.profile_governance import explain_profile_governance
from govengine.typed_execution_governance import (
    TypedExecutionStackCompatibilityReport,
    evaluate_typed_execution_stack_compatibility,
    explain_typed_execution_governance,
    typed_execution_control_catalog,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='govengine-policy',
        description='Author and validate GovEngine policy packs without executing work.',
    )
    sub = parser.add_subparsers(dest='command', required=True)

    scaffold = sub.add_parser('scaffold', help='Emit a baseline policy pack as canonical JSON.')
    scaffold.add_argument('baseline', choices=available_baseline_policy_names())
    scaffold.add_argument('--policy-id', default='', help='Override the baseline policy_id.')
    scaffold.add_argument('--version', default='', help='Override the baseline version.')
    scaffold.add_argument('--output', type=Path, help='Write JSON to this path instead of stdout.')

    schema = sub.add_parser('schema', help='Emit a JSON Schema document.')
    schema.add_argument('kind', nargs='?', choices=POLICY_SCHEMA_KINDS, default='policy-pack')

    validate = sub.add_parser('validate', help='Validate and compile a policy pack JSON file.')
    validate.add_argument('policy_pack', type=Path)
    validate.add_argument('--json', action='store_true', help='Emit machine-readable JSON.')
    validate.add_argument('--max-bytes', type=int, default=DEFAULT_POLICY_MAX_BYTES)

    compile_cmd = sub.add_parser('compile', help='Validate and emit the normalized compiled policy pack.')
    compile_cmd.add_argument('policy_pack', type=Path)
    compile_cmd.add_argument('--json', action='store_true', help='Emit only the compiled policy JSON.')
    compile_cmd.add_argument('--max-bytes', type=int, default=DEFAULT_POLICY_MAX_BYTES)

    for command, help_text in (
        ('explain', 'Evaluate a policy request and emit a stable redacted explanation JSON.'),
        ('simulate', 'Alias for explain; simulates policy evaluation without executing work.'),
    ):
        explain = sub.add_parser(command, help=help_text)
        explain.add_argument('policy_pack', type=Path)
        explain.add_argument('request', type=Path)
        explain.add_argument('--json', action='store_true', help='Emit machine-readable JSON.')
        explain.add_argument('--max-bytes', type=int, default=DEFAULT_POLICY_MAX_BYTES)

    profile_governance = sub.add_parser(
        'profile-governance',
        help='Evaluate profile governance projection and connector compatibility without backend IO.',
    )
    profile_governance.add_argument('projection', type=Path)
    profile_governance.add_argument('--json', action='store_true', help='Emit machine-readable JSON.')
    profile_governance.add_argument('--max-bytes', type=int, default=DEFAULT_POLICY_MAX_BYTES)

    typed_execution = sub.add_parser(
        'typed-execution-governance',
        help='Evaluate typed execution governance and capability compatibility without backend IO.',
    )
    typed_execution.add_argument('projection', type=Path)
    typed_execution.add_argument('--json', action='store_true', help='Emit machine-readable JSON.')
    typed_execution.add_argument('--max-bytes', type=int, default=DEFAULT_POLICY_MAX_BYTES)

    typed_compat = sub.add_parser(
        'typed-execution-compatibility',
        help='Evaluate typed execution stack compatibility for backend descriptors.',
    )
    typed_compat.add_argument('projection', type=Path)
    typed_compat.add_argument('--json', action='store_true', help='Emit machine-readable JSON.')
    typed_compat.add_argument('--max-bytes', type=int, default=DEFAULT_POLICY_MAX_BYTES)

    control_catalog = sub.add_parser(
        'typed-execution-control-catalog',
        help='Emit the GovEngine typed execution control catalog.',
    )
    control_catalog.add_argument('--json', action='store_true', help='Emit machine-readable JSON.')
    return parser


def _write_or_print(content: str, output: Path | None) -> None:
    if output is None:
        print(content, end='')
        return
    output.write_text(content, encoding='utf-8')


def _validate_report(path: Path, *, max_bytes: int) -> dict[str, Any]:
    pack = read_policy_pack(path, max_bytes=max_bytes)
    result = validate_policy_pack(pack)
    policy_pack = result.policy_pack
    return {
        'artifact_type': 'govengine_policy_pack_validation',
        'schema_version': 'v0.1',
        'status': 'passed' if result.ok else 'failed',
        'reason_code': result.reason_code,
        'diagnostics': list(result.diagnostics),
        'policy_id': policy_pack.policy_id if policy_pack else str(pack.get('policy_id') or ''),
        'version': policy_pack.version if policy_pack else str(pack.get('version') or ''),
        'rule_count': len(policy_pack.rules) if policy_pack else 0,
        'non_claims': [
            'Does not execute work.',
            'Does not verify SCLite artifacts or canonicalize evidence.',
            'Does not run operator approval workflow.',
        ],
    }


def _read_json_mapping(path: Path, *, max_bytes: int) -> dict[str, Any]:
    try:
        if max_bytes <= 0:
            raise GovApiError('policy_authoring_invalid_max_bytes')
        raw = path.read_bytes()
        if len(raw) > max_bytes:
            raise GovApiError('policy_request_input_too_large')
        data = json.loads(raw.decode('utf-8'))
    except GovApiError:
        raise
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GovApiError('policy_request_json_invalid', str(exc)) from exc
    if not isinstance(data, dict):
        raise GovApiError('policy_request_json_not_mapping')
    return {str(key): data[key] for key in data}


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == 'scaffold':
            pack = baseline_policy_pack(args.baseline, policy_id=args.policy_id, version=args.version)
            _write_or_print(render_policy_pack_json(pack), args.output)
            return 0
        if args.command == 'schema':
            print(json.dumps(policy_json_schema(args.kind), indent=2, sort_keys=True))
            return 0
        if args.command == 'validate':
            report = _validate_report(args.policy_pack, max_bytes=args.max_bytes)
            if args.json:
                print(json.dumps(report, indent=2, sort_keys=True))
            else:
                print(
                    f"policy_validate_{report['status']}:"
                    f"{report['policy_id']}:rules={report['rule_count']}:"
                    f"reason={report['reason_code']}"
                )
                for diagnostic in report['diagnostics']:
                    print(f'diagnostic: {diagnostic}')
            return 0 if report['status'] == 'passed' else 2
        if args.command == 'compile':
            pack = read_policy_pack(args.policy_pack, max_bytes=args.max_bytes)
            result = validate_policy_pack(pack)
            if not result.ok or result.policy_pack is None:
                print(f'policy_compile_error: {result.reason_code}', file=sys.stderr)
                return 2
            content = render_policy_pack_json(result.policy_pack.as_dict())
            if args.json:
                print(content, end='')
            else:
                print(f'policy_compile_ok:{result.policy_pack.policy_id}:rules={len(result.policy_pack.rules)}')
                print(content, end='')
            return 0
        if args.command in {'explain', 'simulate'}:
            pack = read_policy_pack(args.policy_pack, max_bytes=args.max_bytes)
            result = validate_policy_pack(pack)
            if not result.ok or result.policy_pack is None:
                print(f'policy_explain_error: {result.reason_code}', file=sys.stderr)
                return 2
            request = _read_json_mapping(args.request, max_bytes=args.max_bytes)
            explanation = explain_policy_evaluation(request, result.policy_pack)
            payload = explanation.as_dict()
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                print(
                    f"policy_explain_{payload['status']}:"
                    f"{payload['policy_id']}:{payload['decision']}:"
                    f"reason={payload['reason_code']}"
                )
            return 0 if payload['status'] == 'explained' else 2
        if args.command == 'profile-governance':
            projection = _read_json_mapping(args.projection, max_bytes=args.max_bytes)
            bundle = explain_profile_governance(projection)
            payload = bundle.as_dict()
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                print(
                    f"profile_governance_{payload['status']}:"
                    f"{payload['profile_name']}:"
                    f"governance={payload['governance']['reason_code']}:"
                    f"compatibility={payload['compatibility']['reason_code']}"
                )
            return 0 if payload['status'] == 'passed' else 2
        if args.command == 'typed-execution-control-catalog':
            payload = typed_execution_control_catalog()
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                print(
                    'typed_execution_control_catalog:'
                    f"controls={len(payload['controls'])}:"
                    f"backends={len(payload['supported_backend_classes'])}"
                )
            return 0
        if args.command == 'typed-execution-compatibility':
            projection = _read_json_mapping(args.projection, max_bytes=args.max_bytes)
            stack_report: TypedExecutionStackCompatibilityReport = (
                evaluate_typed_execution_stack_compatibility(projection)
            )
            payload = stack_report.as_dict()
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                print(
                    f"typed_execution_compatibility_{payload['status']}:"
                    f"supported={len(payload['supported_backends'])}:"
                    f"unsupported={len(payload['unsupported_backends'])}:"
                    f"reason={payload['reason_code']}"
                )
            return 0 if payload['status'] == 'passed' else 2
        if args.command == 'typed-execution-governance':
            projection = _read_json_mapping(args.projection, max_bytes=args.max_bytes)
            bundle = explain_typed_execution_governance(projection)
            payload = bundle.as_dict()
            if args.json:
                print(json.dumps(payload, indent=2, sort_keys=True))
            else:
                print(
                    f"typed_execution_governance_{payload['status']}:"
                    f"{payload['step_id']}:"
                    f"governance={payload['governance']['reason_code']}:"
                    f"compatibility={payload['compatibility']['reason_code']}"
                )
            return 0 if payload['status'] == 'passed' else 2
    except (GovApiError, OSError, KeyError) as exc:
        reason = getattr(exc, 'reason_code', str(exc))
        print(f'policy_authoring_error: {reason}', file=sys.stderr)
        return 2
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
