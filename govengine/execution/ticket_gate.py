from __future__ import annotations

from hmac import compare_digest
from typing import Any, Dict, List, Mapping


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
        raise ValueError(f'sclite_ticket_semantics_failed:{exc}') from exc


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
    approved_execution_spec: Dict[str, Any],
    *,
    execution_ticket: Dict[str, Any] | None,
    execution_contract: Dict[str, Any] | None,
    raw_steps: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Validate that an ExecutionTicket authorizes the approved execution shape.

    The approved spec is accepted for signature compatibility with the runtime
    gate, but this pure gate currently validates the ticket, contract digest,
    and command-shape binding only.
    """

    _ = approved_execution_spec
    if not isinstance(execution_ticket, dict):
        raise ValueError('missing_execution_ticket')
    if not isinstance(execution_contract, dict):
        raise ValueError('missing_execution_contract')
    artifact_type = str(execution_ticket.get('artifact_type') or '').strip()
    schema_version = str(execution_ticket.get('schema_version') or '').strip()
    if artifact_type != 'execution_ticket' or schema_version not in SUPPORTED_TICKET_SCHEMA_VERSIONS:
        raise ValueError(f'invalid_execution_ticket:{artifact_type or "missing"}:{schema_version or "missing"}')
    sclite_checks: List[str] = []
    if schema_version == 'v0.3':
        sclite_checks = _sclite_ticket_semantics(execution_ticket, execution_contract)
    approval = execution_ticket.get('approval') if isinstance(execution_ticket.get('approval'), dict) else {}
    status = str(approval.get('status') or '').strip().lower()
    if status not in APPROVED_TICKET_STATUSES:
        raise ValueError(f'invalid_execution_ticket_approval:{status or "missing"}')
    limits = execution_ticket.get('execution_limits') if isinstance(execution_ticket.get('execution_limits'), dict) else {}
    try:
        max_runs = int(limits.get('max_runs', 0) or 0)
    except (TypeError, ValueError):
        max_runs = 0
    if max_runs < 1:
        raise ValueError('invalid_execution_ticket_max_runs')
    contract_digest = _artifact_descriptor(execution_contract)['digest']
    integrity = execution_ticket.get('integrity') if isinstance(execution_ticket.get('integrity'), dict) else {}
    bound_digest = str(integrity.get('ticket_binds_execution_contract_digest') or '').strip()
    if not compare_digest(bound_digest, contract_digest):
        raise ValueError('execution_ticket_contract_digest_mismatch')
    shape = execution_contract.get('execution_shape') if isinstance(execution_contract.get('execution_shape'), dict) else {}
    contract_plan = shape.get('plan') if isinstance(shape.get('plan'), list) else []
    if len(contract_plan) != len(raw_steps):
        raise ValueError('execution_ticket_plan_length_mismatch')
    for idx, (contract_step, approved_step) in enumerate(zip(contract_plan, raw_steps), 1):
        if not isinstance(contract_step, dict):
            raise ValueError(f'execution_ticket_invalid_contract_step:{idx}')
        if str(contract_step.get('tool') or '') != str(approved_step.get('tool') or ''):
            raise ValueError(f'execution_ticket_tool_mismatch:{idx}')
        if [str(item) for item in list(contract_step.get('args') or [])] != [str(item) for item in list(approved_step.get('args') or [])]:
            raise ValueError(f'execution_ticket_args_mismatch:{idx}')
    return {
        'status': 'passed',
        'ticket_id': str(execution_ticket.get('ticket_id') or ''),
        'execution_contract_digest': contract_digest,
        'profile': str(integrity.get('profile') or ''),
        'schema_version': schema_version,
        'sclite_checks': tuple(sclite_checks),
    }
