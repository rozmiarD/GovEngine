from __future__ import annotations

from dataclasses import dataclass, replace
from hmac import compare_digest
from typing import Any, Mapping

from govengine._governance_validation import (
    reject_unknown_fields,
    require_sha256_digest,
    required_nonnegative_int,
    required_text,
    schema_version,
)
from govengine.api import GovApiError, require_mapping
from govengine.governance_decision import (
    GovernanceDecision,
    validate_governance_decision,
)
from govengine.signing import govengine_record_digest


RUNTIME_RECEIPT_BINDING_SCHEMA_VERSION = 'v1'
RECEIPT_CONFORMANCE_RESULT_SCHEMA_VERSION = 'v1'
SUPPORTED_RUNTIME_RECEIPT_STATUSES = frozenset(
    {'completed', 'failed', 'indeterminate'}
)
RUNTIME_RECEIPT_BINDING_FIELDS = frozenset(
    {
        'schema_version',
        'receipt_id',
        'operation_id',
        'step_id',
        'attempt_id',
        'runtime_instance_id',
        'decision_digest',
        'runtime_permit_digest',
        'lease_id',
        'lease_epoch',
        'fencing_token_digest',
        'execution_spec_digest',
        'payload_digest',
        'requested_scope_digest',
        'capability_inventory_digest',
        'inventory_epoch',
        'policy_pack_digest',
        'policy_epoch',
        'terminal_status',
        'output_digests',
        'output_bytes',
        'receipt_digest',
    }
)
MAX_OUTPUT_DIGESTS = 16
MAX_OUTPUT_DIGEST_NAME_LENGTH = 64

__all__ = [
    'RECEIPT_CONFORMANCE_RESULT_SCHEMA_VERSION',
    'RUNTIME_RECEIPT_BINDING_SCHEMA_VERSION',
    'ReceiptConformanceResult',
    'RuntimeReceiptBinding',
    'build_runtime_receipt_binding',
    'evaluate_receipt_conformance',
    'receipt_conformance_result_digest',
    'runtime_receipt_binding_digest',
    'validate_runtime_receipt_binding',
]


@dataclass(frozen=True)
class RuntimeReceiptBinding:
    """Bounded RExecOp receipt facts checked against one GovEngine decision.

    The record is not a SCLite receipt and does not prove that runtime facts are
    honest. It lets a host bind its terminal attempt receipt to the exact
    decision and runtime permit that preceded connector I/O.
    """

    receipt_id: str
    operation_id: str
    step_id: str
    attempt_id: str
    runtime_instance_id: str
    decision_digest: str
    runtime_permit_digest: str
    lease_id: str
    lease_epoch: int
    fencing_token_digest: str
    execution_spec_digest: str
    payload_digest: str
    requested_scope_digest: str
    capability_inventory_digest: str
    inventory_epoch: int
    policy_pack_digest: str
    policy_epoch: int
    terminal_status: str
    output_digests: Mapping[str, str]
    output_bytes: int
    schema_version: str = RUNTIME_RECEIPT_BINDING_SCHEMA_VERSION
    receipt_digest: str = ''

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'RuntimeReceiptBinding':
        raw = require_mapping(value, reason_code='invalid_runtime_receipt_binding')
        reject_unknown_fields(
            raw,
            allowed=RUNTIME_RECEIPT_BINDING_FIELDS,
            reason_code='unknown_runtime_receipt_binding_field',
        )
        item = cls(
            receipt_id=required_text(
                raw,
                'receipt_id',
                'missing_runtime_receipt_id',
            ),
            operation_id=required_text(
                raw,
                'operation_id',
                'missing_runtime_receipt_operation_id',
            ),
            step_id=required_text(
                raw,
                'step_id',
                'missing_runtime_receipt_step_id',
            ),
            attempt_id=required_text(
                raw,
                'attempt_id',
                'missing_runtime_receipt_attempt_id',
            ),
            runtime_instance_id=required_text(
                raw,
                'runtime_instance_id',
                'missing_runtime_receipt_runtime_instance_id',
            ),
            decision_digest=_required_digest(
                raw,
                'decision_digest',
                'invalid_runtime_receipt_decision_digest',
            ),
            runtime_permit_digest=_required_digest(
                raw,
                'runtime_permit_digest',
                'invalid_runtime_receipt_permit_digest',
            ),
            lease_id=_required_digest(
                raw,
                'lease_id',
                'invalid_runtime_receipt_lease_id',
            ),
            lease_epoch=required_nonnegative_int(
                raw,
                'lease_epoch',
                'invalid_runtime_receipt_lease_epoch',
            ),
            fencing_token_digest=_required_digest(
                raw,
                'fencing_token_digest',
                'invalid_runtime_receipt_fencing_token_digest',
            ),
            execution_spec_digest=_required_digest(
                raw,
                'execution_spec_digest',
                'invalid_runtime_receipt_execution_spec_digest',
            ),
            payload_digest=_required_digest(
                raw,
                'payload_digest',
                'invalid_runtime_receipt_payload_digest',
            ),
            requested_scope_digest=_required_digest(
                raw,
                'requested_scope_digest',
                'invalid_runtime_receipt_requested_scope_digest',
            ),
            capability_inventory_digest=_required_digest(
                raw,
                'capability_inventory_digest',
                'invalid_runtime_receipt_capability_inventory_digest',
            ),
            inventory_epoch=required_nonnegative_int(
                raw,
                'inventory_epoch',
                'invalid_runtime_receipt_inventory_epoch',
            ),
            policy_pack_digest=_required_digest(
                raw,
                'policy_pack_digest',
                'invalid_runtime_receipt_policy_pack_digest',
            ),
            policy_epoch=required_nonnegative_int(
                raw,
                'policy_epoch',
                'invalid_runtime_receipt_policy_epoch',
            ),
            terminal_status=required_text(
                raw,
                'terminal_status',
                'missing_runtime_receipt_terminal_status',
            ),
            output_digests=_output_digests(raw.get('output_digests')),
            output_bytes=required_nonnegative_int(
                raw,
                'output_bytes',
                'invalid_runtime_receipt_output_bytes',
            ),
            schema_version=schema_version(
                raw,
                default=RUNTIME_RECEIPT_BINDING_SCHEMA_VERSION,
                reason_code='invalid_runtime_receipt_schema_version',
            ),
            receipt_digest=_required_digest(
                raw,
                'receipt_digest',
                'invalid_runtime_receipt_digest',
            ),
        )
        return validate_runtime_receipt_binding(item)

    def as_dict(self) -> dict[str, Any]:
        return {
            'schema_version': self.schema_version,
            'receipt_id': self.receipt_id,
            'operation_id': self.operation_id,
            'step_id': self.step_id,
            'attempt_id': self.attempt_id,
            'runtime_instance_id': self.runtime_instance_id,
            'decision_digest': self.decision_digest,
            'runtime_permit_digest': self.runtime_permit_digest,
            'lease_id': self.lease_id,
            'lease_epoch': self.lease_epoch,
            'fencing_token_digest': self.fencing_token_digest,
            'execution_spec_digest': self.execution_spec_digest,
            'payload_digest': self.payload_digest,
            'requested_scope_digest': self.requested_scope_digest,
            'capability_inventory_digest': self.capability_inventory_digest,
            'inventory_epoch': self.inventory_epoch,
            'policy_pack_digest': self.policy_pack_digest,
            'policy_epoch': self.policy_epoch,
            'terminal_status': self.terminal_status,
            'output_digests': dict(self.output_digests),
            'output_bytes': self.output_bytes,
            'receipt_digest': self.receipt_digest,
        }


@dataclass(frozen=True)
class ReceiptConformanceResult:
    conformance_id: str
    status: str
    reason_code: str
    decision_digest: str
    receipt_digest: str
    runtime_permit_digest: str
    checks: tuple[str, ...]
    failures: tuple[str, ...] = ()
    schema_version: str = RECEIPT_CONFORMANCE_RESULT_SCHEMA_VERSION
    result_digest: str = ''

    @property
    def conformant(self) -> bool:
        return self.status == 'conformant'

    def as_dict(self) -> dict[str, Any]:
        return {
            'schema_version': self.schema_version,
            'conformance_id': self.conformance_id,
            'status': self.status,
            'conformant': self.conformant,
            'reason_code': self.reason_code,
            'decision_digest': self.decision_digest,
            'receipt_digest': self.receipt_digest,
            'runtime_permit_digest': self.runtime_permit_digest,
            'checks': list(self.checks),
            'failures': list(self.failures),
            'result_digest': self.result_digest,
        }


def build_runtime_receipt_binding(
    *,
    receipt_id: str,
    operation_id: str,
    step_id: str,
    attempt_id: str,
    runtime_instance_id: str,
    decision_digest: str,
    runtime_permit_digest: str,
    lease_id: str,
    lease_epoch: int,
    fencing_token_digest: str,
    execution_spec_digest: str,
    payload_digest: str,
    requested_scope_digest: str,
    capability_inventory_digest: str,
    inventory_epoch: int,
    policy_pack_digest: str,
    policy_epoch: int,
    terminal_status: str,
    output_digests: Mapping[str, str],
    output_bytes: int,
) -> RuntimeReceiptBinding:
    item = RuntimeReceiptBinding(
        receipt_id=receipt_id,
        operation_id=operation_id,
        step_id=step_id,
        attempt_id=attempt_id,
        runtime_instance_id=runtime_instance_id,
        decision_digest=decision_digest,
        runtime_permit_digest=runtime_permit_digest,
        lease_id=lease_id,
        lease_epoch=lease_epoch,
        fencing_token_digest=fencing_token_digest,
        execution_spec_digest=execution_spec_digest,
        payload_digest=payload_digest,
        requested_scope_digest=requested_scope_digest,
        capability_inventory_digest=capability_inventory_digest,
        inventory_epoch=inventory_epoch,
        policy_pack_digest=policy_pack_digest,
        policy_epoch=policy_epoch,
        terminal_status=terminal_status,
        output_digests=dict(output_digests),
        output_bytes=output_bytes,
    )
    _validate_runtime_receipt_shape(item, require_digest=False)
    return validate_runtime_receipt_binding(
        replace(item, receipt_digest=runtime_receipt_binding_digest(item))
    )


def runtime_receipt_binding_digest(receipt: RuntimeReceiptBinding) -> str:
    if not isinstance(receipt, RuntimeReceiptBinding):
        raise GovApiError('invalid_runtime_receipt_binding')
    _validate_runtime_receipt_shape(receipt, require_digest=False)
    payload = receipt.as_dict()
    payload['receipt_digest'] = ''
    return govengine_record_digest(
        payload,
        record_type='govengine.receipt_conformance.RuntimeReceiptBinding',
        schema_version=RUNTIME_RECEIPT_BINDING_SCHEMA_VERSION,
    )


def validate_runtime_receipt_binding(
    receipt: RuntimeReceiptBinding,
) -> RuntimeReceiptBinding:
    if not isinstance(receipt, RuntimeReceiptBinding):
        raise GovApiError('invalid_runtime_receipt_binding')
    _validate_runtime_receipt_shape(receipt, require_digest=True)
    expected = runtime_receipt_binding_digest(receipt)
    if not compare_digest(expected, receipt.receipt_digest):
        raise GovApiError('runtime_receipt_digest_mismatch')
    return receipt


def evaluate_receipt_conformance(
    decision: GovernanceDecision,
    receipt: Mapping[str, Any] | RuntimeReceiptBinding,
    *,
    expected_runtime_permit_digest: str,
) -> ReceiptConformanceResult:
    """Check terminal runtime facts against one canonical governance decision."""

    checked_decision = validate_governance_decision(decision)
    checked_receipt = (
        receipt
        if isinstance(receipt, RuntimeReceiptBinding)
        else RuntimeReceiptBinding.from_mapping(receipt)
    )
    validate_runtime_receipt_binding(checked_receipt)
    expected_permit = require_sha256_digest(
        expected_runtime_permit_digest,
        'invalid_expected_runtime_permit_digest',
    )
    checks: list[str] = ['receipt_digest_verified']
    failures: list[str] = []

    if not checked_decision.allowed or checked_decision.authorization is None:
        failures.append('receipt_governance_decision_not_allowed')
    else:
        grant = checked_decision.authorization
        _binding_check(
            checked_receipt.decision_digest,
            checked_decision.decision_digest,
            'receipt_decision_digest_mismatch',
            'receipt_decision_bound',
            checks,
            failures,
        )
        _binding_check(
            checked_receipt.runtime_permit_digest,
            expected_permit,
            'receipt_runtime_permit_digest_mismatch',
            'receipt_runtime_permit_bound',
            checks,
            failures,
        )
        for actual, expected, failure, passed in (
            (
                checked_receipt.operation_id,
                grant.operation_id,
                'receipt_operation_id_mismatch',
                'receipt_operation_bound',
            ),
            (
                checked_receipt.step_id,
                grant.step_id,
                'receipt_step_id_mismatch',
                'receipt_step_bound',
            ),
            (
                checked_receipt.attempt_id,
                grant.attempt_id,
                'receipt_attempt_id_mismatch',
                'receipt_attempt_bound',
            ),
            (
                checked_receipt.runtime_instance_id,
                grant.runtime_instance_id,
                'receipt_runtime_instance_id_mismatch',
                'receipt_runtime_instance_bound',
            ),
            (
                checked_receipt.lease_id,
                grant.lease_id,
                'receipt_lease_id_mismatch',
                'receipt_lease_bound',
            ),
            (
                checked_receipt.lease_epoch,
                grant.lease_epoch,
                'receipt_lease_epoch_mismatch',
                'receipt_lease_epoch_bound',
            ),
            (
                checked_receipt.fencing_token_digest,
                grant.fencing_token_digest,
                'receipt_fencing_token_digest_mismatch',
                'receipt_fencing_token_bound',
            ),
            (
                checked_receipt.execution_spec_digest,
                grant.execution_spec_digest,
                'receipt_execution_spec_digest_mismatch',
                'receipt_execution_spec_bound',
            ),
            (
                checked_receipt.payload_digest,
                grant.payload_digest,
                'receipt_payload_digest_mismatch',
                'receipt_payload_bound',
            ),
            (
                checked_receipt.requested_scope_digest,
                grant.requested_scope_digest,
                'receipt_requested_scope_digest_mismatch',
                'receipt_requested_scope_bound',
            ),
            (
                checked_receipt.capability_inventory_digest,
                grant.capability_inventory_digest,
                'receipt_capability_inventory_digest_mismatch',
                'receipt_capability_inventory_bound',
            ),
            (
                checked_receipt.inventory_epoch,
                grant.inventory_epoch,
                'receipt_inventory_epoch_mismatch',
                'receipt_inventory_epoch_bound',
            ),
            (
                checked_receipt.policy_pack_digest,
                grant.policy_pack_digest,
                'receipt_policy_pack_digest_mismatch',
                'receipt_policy_pack_bound',
            ),
            (
                checked_receipt.policy_epoch,
                grant.policy_epoch,
                'receipt_policy_epoch_mismatch',
                'receipt_policy_epoch_bound',
            ),
        ):
            _binding_check(actual, expected, failure, passed, checks, failures)

    checks.append('terminal_receipt_present')
    if checked_decision.controls.output_digest_required:
        if checked_receipt.output_digests:
            checks.append('required_output_digest_present')
        else:
            failures.append('required_output_digest_missing')
    elif checked_receipt.output_digests:
        checks.append('optional_output_digest_present')
    output_limit = checked_decision.controls.max_output_bytes
    if output_limit > 0 and checked_receipt.output_bytes > output_limit:
        failures.append('receipt_output_limit_exceeded')
    else:
        checks.append('receipt_output_within_limit')

    unique_failures = tuple(dict.fromkeys(failures))
    status = 'conformant' if not unique_failures else 'nonconformant'
    reason_code = 'receipt_conforms' if not unique_failures else unique_failures[0]
    item = ReceiptConformanceResult(
        conformance_id=f'receipt-conformance:{checked_receipt.receipt_id}',
        status=status,
        reason_code=reason_code,
        decision_digest=checked_decision.decision_digest,
        receipt_digest=checked_receipt.receipt_digest,
        runtime_permit_digest=checked_receipt.runtime_permit_digest,
        checks=tuple(checks),
        failures=unique_failures,
    )
    return replace(item, result_digest=receipt_conformance_result_digest(item))


def receipt_conformance_result_digest(result: ReceiptConformanceResult) -> str:
    if not isinstance(result, ReceiptConformanceResult):
        raise GovApiError('invalid_receipt_conformance_result')
    payload = result.as_dict()
    payload['result_digest'] = ''
    return govengine_record_digest(
        payload,
        record_type='govengine.receipt_conformance.ReceiptConformanceResult',
        schema_version=RECEIPT_CONFORMANCE_RESULT_SCHEMA_VERSION,
    )


def _validate_runtime_receipt_shape(
    item: RuntimeReceiptBinding,
    *,
    require_digest: bool,
) -> None:
    if item.schema_version != RUNTIME_RECEIPT_BINDING_SCHEMA_VERSION:
        raise GovApiError('unknown_runtime_receipt_schema_version')
    payload = item.as_dict()
    for key, reason_code in (
        ('receipt_id', 'missing_runtime_receipt_id'),
        ('operation_id', 'missing_runtime_receipt_operation_id'),
        ('step_id', 'missing_runtime_receipt_step_id'),
        ('attempt_id', 'missing_runtime_receipt_attempt_id'),
        ('runtime_instance_id', 'missing_runtime_receipt_runtime_instance_id'),
    ):
        required_text(payload, key, reason_code)
    for value, reason_code in (
        (item.decision_digest, 'invalid_runtime_receipt_decision_digest'),
        (item.runtime_permit_digest, 'invalid_runtime_receipt_permit_digest'),
        (item.lease_id, 'invalid_runtime_receipt_lease_id'),
        (item.fencing_token_digest, 'invalid_runtime_receipt_fencing_token_digest'),
        (item.execution_spec_digest, 'invalid_runtime_receipt_execution_spec_digest'),
        (item.payload_digest, 'invalid_runtime_receipt_payload_digest'),
        (item.requested_scope_digest, 'invalid_runtime_receipt_requested_scope_digest'),
        (
            item.capability_inventory_digest,
            'invalid_runtime_receipt_capability_inventory_digest',
        ),
        (item.policy_pack_digest, 'invalid_runtime_receipt_policy_pack_digest'),
    ):
        require_sha256_digest(value, reason_code)
    for value, reason_code in (
        (item.lease_epoch, 'invalid_runtime_receipt_lease_epoch'),
        (item.inventory_epoch, 'invalid_runtime_receipt_inventory_epoch'),
        (item.policy_epoch, 'invalid_runtime_receipt_policy_epoch'),
        (item.output_bytes, 'invalid_runtime_receipt_output_bytes'),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise GovApiError(reason_code)
    if item.terminal_status not in SUPPORTED_RUNTIME_RECEIPT_STATUSES:
        raise GovApiError('unknown_runtime_receipt_terminal_status')
    _output_digests(item.output_digests)
    if require_digest:
        require_sha256_digest(item.receipt_digest, 'invalid_runtime_receipt_digest')


def _required_digest(
    value: Mapping[str, Any],
    key: str,
    reason_code: str,
) -> str:
    return require_sha256_digest(required_text(value, key, reason_code), reason_code)


def _output_digests(value: Any) -> Mapping[str, str]:
    raw = require_mapping(value, reason_code='invalid_runtime_receipt_output_digests')
    if len(raw) > MAX_OUTPUT_DIGESTS:
        raise GovApiError('runtime_receipt_output_digests_too_large')
    result: dict[str, str] = {}
    for key, digest in raw.items():
        if (
            not isinstance(key, str)
            or not key.strip()
            or len(key.strip()) > MAX_OUTPUT_DIGEST_NAME_LENGTH
        ):
            raise GovApiError('invalid_runtime_receipt_output_digest_name')
        if key.strip() in result:
            raise GovApiError('duplicate_runtime_receipt_output_digest_name')
        result[key.strip()] = require_sha256_digest(
            digest,
            'invalid_runtime_receipt_output_digest',
        )
    return result


def _binding_check(
    actual: Any,
    expected: Any,
    failure: str,
    passed: str,
    checks: list[str],
    failures: list[str],
) -> None:
    equal = (
        compare_digest(actual, expected)
        if isinstance(actual, str) and isinstance(expected, str)
        else actual == expected
    )
    if equal:
        checks.append(passed)
    else:
        failures.append(failure)
