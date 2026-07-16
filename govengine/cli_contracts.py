from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from govengine.cli_errors import CLI_ERROR_SCHEMA

CLI_CONTRACT_REGISTRY_SCHEMA = 'govengine.cli_contract_registry.v0.1'

_SUCCESS = 0
_FAILURE = 2


@dataclass(frozen=True)
class CliExitCode:
    code: int
    meaning: str

    def as_dict(self) -> dict[str, Any]:
        return {'code': self.code, 'meaning': self.meaning}


@dataclass(frozen=True)
class CliContract:
    command: tuple[str, ...]
    schema: str
    stability: str
    group: str
    entrypoint: str
    formats: tuple[str, ...] = ('json',)
    default_format: str = 'json'
    output_policy: str = 'json_optional_flag'
    exit_codes: tuple[CliExitCode, ...] = (
        CliExitCode(_SUCCESS, 'success'),
        CliExitCode(_FAILURE, 'validation_error_or_blocked'),
    )
    redacted: bool = True
    bounded_output: bool = True
    authority: str = 'projection'
    error_schema: str = CLI_ERROR_SCHEMA
    notes: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            'command': ' '.join(self.command),
            'argv': list(self.command),
            'entrypoint': self.entrypoint,
            'schema': self.schema,
            'stability': self.stability,
            'group': self.group,
            'formats': list(self.formats),
            'default_format': self.default_format,
            'output_policy': self.output_policy,
            'exit_codes': [item.as_dict() for item in self.exit_codes],
            'redacted': self.redacted,
            'bounded_output': self.bounded_output,
            'authority': self.authority,
            'error_schema': self.error_schema,
            'notes': list(self.notes),
        }


CLI_CONTRACTS: tuple[CliContract, ...] = (
    CliContract(
        command=('govengine-policy', 'scaffold'),
        entrypoint='govengine-policy',
        schema='govengine.policy_pack.v0.1',
        stability='alpha_contract',
        group='policy_authoring',
        output_policy='json_only',
        notes=('Emits canonical policy-pack JSON.',),
    ),
    CliContract(
        command=('govengine-policy', 'schema'),
        entrypoint='govengine-policy',
        schema='govengine.policy_json_schema.v0.1',
        stability='alpha_contract',
        group='policy_authoring',
        output_policy='json_only',
    ),
    CliContract(
        command=('govengine-policy', 'validate'),
        entrypoint='govengine-policy',
        schema='govengine.policy_pack_validation.v0.1',
        stability='alpha_contract',
        group='policy_authoring',
        exit_codes=(
            CliExitCode(_SUCCESS, 'passed'),
            CliExitCode(_FAILURE, 'failed_or_input_error'),
        ),
    ),
    CliContract(
        command=('govengine-policy', 'compile'),
        entrypoint='govengine-policy',
        schema='govengine.policy_pack.v0.1_or_v1',
        stability='alpha_contract',
        group='policy_authoring',
        exit_codes=(
            CliExitCode(_SUCCESS, 'compiled'),
            CliExitCode(_FAILURE, 'compile_failed_or_input_error'),
        ),
        notes=('Preserves legacy v0.1 equality maps or typed v1 condition AST.',),
    ),
    CliContract(
        command=('govengine-policy', 'explain'),
        entrypoint='govengine-policy',
        schema='govengine.policy_evaluation_explanation.v0.1',
        stability='alpha_contract',
        group='policy_explain',
        exit_codes=(
            CliExitCode(_SUCCESS, 'explained'),
            CliExitCode(_FAILURE, 'blocked_or_input_error'),
        ),
        notes=('Blocked policy outcomes still emit explanation JSON before exit 2.',),
    ),
    CliContract(
        command=('govengine-policy', 'simulate'),
        entrypoint='govengine-policy',
        schema='govengine.policy_evaluation_explanation.v0.1',
        stability='alpha_contract',
        group='policy_explain',
        exit_codes=(
            CliExitCode(_SUCCESS, 'explained'),
            CliExitCode(_FAILURE, 'blocked_or_input_error'),
        ),
        notes=('Alias for explain.',),
    ),
    CliContract(
        command=('govengine-policy', 'profile-governance'),
        entrypoint='govengine-policy',
        schema='govengine.profile_governance_bundle.v0.1',
        stability='alpha_contract',
        group='profile_governance',
        exit_codes=(
            CliExitCode(_SUCCESS, 'passed'),
            CliExitCode(_FAILURE, 'failed_or_input_error'),
        ),
    ),
    CliContract(
        command=('govengine-policy', 'automation-transition'),
        entrypoint='govengine-policy',
        schema='govengine.automation_transition_explanation.v0.1',
        stability='alpha_contract',
        group='automation_transition',
        exit_codes=(
            CliExitCode(_SUCCESS, 'explained'),
            CliExitCode(_FAILURE, 'blocked_or_input_error'),
        ),
        notes=('Child-operation planning admission explanation without runtime mutation.',),
    ),
    CliContract(
        command=('govengine-policy', 'compatibility'),
        entrypoint='govengine-policy',
        schema='govengine.contract_compatibility_report.v0.1',
        stability='alpha_contract',
        group='contract_compatibility',
        exit_codes=(
            CliExitCode(_SUCCESS, 'catalog_or_passed'),
            CliExitCode(_FAILURE, 'compatibility_failed_or_input_error'),
        ),
        notes=('Without request path emits supported contract catalog.',),
    ),
    CliContract(
        command=('govengine-policy', 'typed-execution-control-catalog'),
        entrypoint='govengine-policy',
        schema='govengine.typed_execution_control_catalog.v0.1',
        stability='alpha_contract',
        group='typed_execution',
        output_policy='json_optional_flag',
    ),
    CliContract(
        command=('govengine-policy', 'typed-execution-compatibility'),
        entrypoint='govengine-policy',
        schema='govengine.typed_execution_stack_compatibility.v0.1',
        stability='alpha_contract',
        group='typed_execution',
        exit_codes=(
            CliExitCode(_SUCCESS, 'passed'),
            CliExitCode(_FAILURE, 'unsupported_or_input_error'),
        ),
    ),
    CliContract(
        command=('govengine-policy', 'typed-execution-governance'),
        entrypoint='govengine-policy',
        schema='govengine.typed_execution_governance_bundle.v0.1',
        stability='alpha_contract',
        group='typed_execution',
        exit_codes=(
            CliExitCode(_SUCCESS, 'passed'),
            CliExitCode(_FAILURE, 'failed_or_input_error'),
        ),
    ),
    CliContract(
        command=('govengine-supervisor', 'explain'),
        entrypoint='govengine-supervisor',
        schema='govengine.supervisor_action_explanation.v0.1',
        stability='alpha_contract',
        group='supervisor_explain',
        exit_codes=(
            CliExitCode(_SUCCESS, 'explained'),
            CliExitCode(_FAILURE, 'blocked_or_input_error'),
        ),
        notes=('Recovery/triage reason codes without executing recovery.',),
    ),
)

_OUTPUT_POLICIES = frozenset({'json_only', 'json_optional_flag'})


def cli_contract_registry() -> dict[str, Any]:
    sorted_contracts = tuple(sorted(CLI_CONTRACTS, key=lambda item: item.command))
    contracts = [item.as_dict() for item in sorted_contracts]
    return {
        'schema': CLI_CONTRACT_REGISTRY_SCHEMA,
        'status': 'present',
        'scope': 'govengine_policy_and_supervisor_cli',
        'contract_count': len(contracts),
        'contracts': contracts,
        'command_groups': _command_groups(sorted_contracts),
        'format_matrix': _format_matrix(sorted_contracts),
        'exit_code_matrix': _exit_code_matrix(sorted_contracts),
        'non_claims': [
            'Does not execute work, recovery, or backend IO.',
            'Does not validate private runtime state.',
            'Human text output is not a stable contract unless --json is used.',
            'Does not replace command-specific tests.',
        ],
    }


def _command_groups(contracts: tuple[CliContract, ...]) -> list[dict[str, Any]]:
    groups: dict[str, list[str]] = {}
    for item in contracts:
        groups.setdefault(item.group, []).append(' '.join(item.command))
    return [
        {'group': group, 'command_count': len(commands), 'commands': commands}
        for group, commands in sorted(groups.items())
    ]


def _format_matrix(contracts: tuple[CliContract, ...]) -> list[dict[str, Any]]:
    return [
        {
            'command': ' '.join(item.command),
            'group': item.group,
            'entrypoint': item.entrypoint,
            'output_policy': item.output_policy,
            'formats': list(item.formats),
            'default_format': item.default_format,
        }
        for item in contracts
    ]


def _exit_code_matrix(contracts: tuple[CliContract, ...]) -> list[dict[str, Any]]:
    return [
        {
            'command': ' '.join(item.command),
            'group': item.group,
            'entrypoint': item.entrypoint,
            'exit_codes': [code.as_dict() for code in item.exit_codes],
            'error_schema': item.error_schema,
        }
        for item in contracts
    ]


def validate_cli_contract_registry(payload: dict[str, Any] | None = None) -> list[str]:
    registry = payload or cli_contract_registry()
    errors: list[str] = []
    if registry.get('schema') != CLI_CONTRACT_REGISTRY_SCHEMA:
        errors.append('schema')
    seen: set[str] = set()
    for item in registry.get('contracts') or []:
        if not isinstance(item, dict):
            errors.append('contract_not_object')
            continue
        command = str(item.get('command') or '')
        if not command:
            errors.append('command')
        if command in seen:
            errors.append(f'duplicate:{command}')
        seen.add(command)
        if not str(item.get('schema') or '').startswith('govengine.'):
            errors.append(f'{command}:schema')
        if not str(item.get('group') or ''):
            errors.append(f'{command}:group')
        if not str(item.get('entrypoint') or ''):
            errors.append(f'{command}:entrypoint')
        if item.get('output_policy') not in _OUTPUT_POLICIES:
            errors.append(f'{command}:output_policy')
        formats = item.get('formats')
        if not isinstance(formats, list) or not formats:
            errors.append(f'{command}:formats')
        elif item.get('default_format') not in formats:
            errors.append(f'{command}:default_format')
        if item.get('error_schema') != CLI_ERROR_SCHEMA:
            errors.append(f'{command}:error_schema')
        exit_codes = item.get('exit_codes')
        if not isinstance(exit_codes, list) or not exit_codes:
            errors.append(f'{command}:exit_codes')
        elif not any(isinstance(code, dict) and code.get('code') == _SUCCESS for code in exit_codes):
            errors.append(f'{command}:exit_code_0')
        if item.get('redacted') is not True:
            errors.append(f'{command}:redacted')
        if item.get('bounded_output') is not True:
            errors.append(f'{command}:bounded_output')
    if not registry.get('command_groups'):
        errors.append('command_groups')
    if not registry.get('format_matrix'):
        errors.append('format_matrix')
    if not registry.get('exit_code_matrix'):
        errors.append('exit_code_matrix')
    return errors
