from __future__ import annotations

from hmac import compare_digest
from typing import Any, Dict, List, Mapping, Sequence

from govengine.api import GovApiError


def _artifact_descriptor(artifact: Dict[str, Any]) -> Dict[str, Any]:
    from sclite.integrity import artifact_descriptor

    return artifact_descriptor(artifact)

APPROVED_TICKET_STATUSES = {'approve', 'approved', 'approved_for_dry_run'}
SUPPORTED_TICKET_SCHEMA_VERSIONS = {'v0.2', 'v0.3'}


def _sclite_ticket_semantics(ticket: Mapping[str, Any], execution_contract: Mapping[str, Any]) -> List[str]:
    """Delegate scoped-ticket semantic checks to SCLite when a v0.3 ticket is used."""

    from sclite.tickets import TicketSemanticError, validate_ticket_semantics

    try:
        return validate_ticket_semantics(ticket, execution_contract)
    except TicketSemanticError as exc:
        raise GovApiError('sclite_ticket_semantics_failed') from exc


def validate_scoped_ticket_use_gate(
    *,
    execution_ticket: Dict[str, Any] | None,
    execution_contract: Dict[str, Any] | None,
    execution_receipt: Dict[str, Any] | None,
    evidence_contract: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Validate receipt/evidence use against a SCLite v0.3 scoped ticket.

    This is a thin GovEngine host gate around SCLite's `verify_ticket_use`.
    GovEngine does not reimplement SCLite's artifact semantics; it maps the
    result into a small gate receipt that host runtimes can attach to runner
    receipts or review packets.
    """

    if not isinstance(execution_ticket, dict):
        raise ValueError('missing_execution_ticket')
    if not isinstance(execution_contract, dict):
        raise ValueError('missing_execution_contract')
    if not isinstance(execution_receipt, dict):
        raise ValueError('missing_execution_receipt')

    from sclite.tickets import TicketUseVerificationError, verify_ticket_use

    try:
        result = verify_ticket_use(
            execution_ticket,
            execution_contract,
            execution_receipt,
            evidence_contract,
        )
    except TicketUseVerificationError as exc:
        raise ValueError(f'sclite_ticket_use_failed:{exc}') from exc
    return {
        'status': str(result.get('status') or 'passed'),
        'ticket_id': str(result.get('ticket_id') or execution_ticket.get('ticket_id') or ''),
        'receipt_id': str(result.get('receipt_id') or execution_receipt.get('receipt_id') or ''),
        'profile': str(execution_ticket.get('ticket_profile') or ''),
        'checks': tuple(str(check) for check in result.get('checks', ())),
        'source': 'sclite.verify_ticket_use',
    }


def validate_execution_ticket_gate(
    *,
    execution_ticket: Mapping[str, Any] | None,
    execution_contract: Mapping[str, Any] | None,
    raw_steps: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Compatibility-only check for legacy ticket/contract command shapes.

    This deprecated helper has only test call-sites in this repository. It
    intentionally does not accept or bind an ``approved_execution_spec`` and
    does not grant execution permission. RExecOp owns runtime claim/permit
    enforcement, while SCLite owns ticket and receipt verification. Callers
    retaining this migration helper receive only a strict compatibility check
    over the supplied ticket, contract, and typed argv values.
    """

    if not isinstance(execution_ticket, Mapping):
        raise GovApiError('missing_execution_ticket')
    if not isinstance(execution_contract, Mapping):
        raise GovApiError('missing_execution_contract')
    if not isinstance(raw_steps, Sequence) or isinstance(raw_steps, (str, bytes)):
        raise GovApiError('invalid_execution_ticket_raw_steps')
    _validate_typed_raw_steps(raw_steps)
    artifact_type = str(execution_ticket.get('artifact_type') or '').strip()
    schema_version = str(execution_ticket.get('schema_version') or '').strip()
    if artifact_type != 'execution_ticket' or schema_version not in SUPPORTED_TICKET_SCHEMA_VERSIONS:
        raise GovApiError('invalid_execution_ticket')
    sclite_checks: List[str] = []
    if schema_version == 'v0.3':
        sclite_checks = _sclite_ticket_semantics(execution_ticket, execution_contract)
    approval = execution_ticket.get('approval') if isinstance(execution_ticket.get('approval'), dict) else {}
    status = str(approval.get('status') or '').strip().lower()
    if status not in APPROVED_TICKET_STATUSES:
        raise GovApiError('invalid_execution_ticket_approval')
    limits = execution_ticket.get('execution_limits') if isinstance(execution_ticket.get('execution_limits'), dict) else {}
    max_runs = limits.get('max_runs', 0)
    if isinstance(max_runs, bool) or not isinstance(max_runs, int):
        raise GovApiError('invalid_execution_ticket_max_runs')
    if max_runs < 1:
        raise GovApiError('invalid_execution_ticket_max_runs')
    contract_digest = _artifact_descriptor(execution_contract)['digest']
    integrity = execution_ticket.get('integrity') if isinstance(execution_ticket.get('integrity'), dict) else {}
    bound_digest = str(integrity.get('ticket_binds_execution_contract_digest') or '').strip()
    if not compare_digest(bound_digest, contract_digest):
        raise GovApiError('execution_ticket_contract_digest_mismatch')
    shape = execution_contract.get('execution_shape') if isinstance(execution_contract.get('execution_shape'), dict) else {}
    contract_plan = shape.get('plan') if isinstance(shape.get('plan'), list) else []
    if len(contract_plan) != len(raw_steps):
        raise GovApiError('execution_ticket_plan_length_mismatch')
    for idx, (contract_step, approved_step) in enumerate(zip(contract_plan, raw_steps), 1):
        if not isinstance(contract_step, Mapping):
            raise GovApiError('execution_ticket_invalid_contract_step')
        contract_tool = contract_step.get('tool')
        raw_tool = approved_step.get('tool')
        if not isinstance(contract_tool, str) or not contract_tool:
            raise GovApiError('execution_ticket_invalid_contract_tool')
        if contract_tool != raw_tool:
            raise GovApiError('execution_ticket_tool_mismatch')
        contract_args = contract_step.get('args')
        raw_args = approved_step.get('args')
        if not isinstance(contract_args, list) or any(not isinstance(item, str) for item in contract_args):
            raise GovApiError('execution_ticket_invalid_contract_args')
        if contract_args != raw_args:
            raise GovApiError('execution_ticket_args_mismatch')
    return {
        'status': 'compatibility_checked',
        'enforcement': 'not_claimed',
        'deprecated': True,
        'ticket_id': str(execution_ticket.get('ticket_id') or ''),
        'execution_contract_digest': contract_digest,
        'profile': str(integrity.get('profile') or ''),
        'schema_version': schema_version,
        'sclite_checks': tuple(sclite_checks),
    }


def _validate_typed_raw_steps(raw_steps: Sequence[Mapping[str, Any]]) -> None:
    for raw_step in raw_steps:
        if not isinstance(raw_step, Mapping):
            raise GovApiError('execution_ticket_invalid_raw_step')
        tool = raw_step.get('tool')
        if not isinstance(tool, str) or not tool:
            raise GovApiError('execution_ticket_invalid_raw_tool')
        args = raw_step.get('args')
        if not isinstance(args, list) or any(not isinstance(item, str) for item in args):
            raise GovApiError('execution_ticket_invalid_raw_args')
