from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from govengine.api import GovApiError
from govengine.governance_decision import (
    GovernanceAuthorization,
    GovernanceDecision,
    _governance_decision_body_digest,
)
from govengine.policy import RuntimeControlProjection
from govengine.receipt_conformance import (
    RuntimeReceiptBinding,
    build_runtime_receipt_binding,
    evaluate_receipt_conformance,
    receipt_conformance_result_digest,
)


NOW = datetime(2026, 7, 15, 18, 0, tzinfo=timezone.utc)
DIGEST_A = 'sha256:' + 'a' * 64
DIGEST_B = 'sha256:' + 'b' * 64
PERMIT_DIGEST = 'sha256:' + 'c' * 64
OUTPUT_DIGEST = 'sha256:' + 'd' * 64


def _decision() -> GovernanceDecision:
    grant = GovernanceAuthorization(
        authorization_id='gov-auth:decision-1',
        operation_id='op-1',
        step_id='step-1',
        attempt_id='attempt-1',
        runtime_instance_id='runtime-1',
        lease_id=DIGEST_A,
        lease_epoch=7,
        fencing_token_digest=DIGEST_B,
        execution_spec_digest='sha256:' + '1' * 64,
        payload_digest='sha256:' + '2' * 64,
        requested_scope_digest='sha256:' + '3' * 64,
        capability_inventory_digest='sha256:' + '4' * 64,
        inventory_epoch=11,
        policy_pack_digest='sha256:' + '5' * 64,
        policy_epoch=13,
        issued_at=NOW.isoformat(),
        expires_at=(NOW + timedelta(seconds=30)).isoformat(),
        nonce='nonce-1',
    )
    item = GovernanceDecision(
        decision_id='decision-1',
        transaction_id='transaction-1',
        request_digest='sha256:' + '6' * 64,
        status='allowed',
        reason_code='all_governance_gates_passed',
        policy_evaluation_digest='sha256:' + '7' * 64,
        policy_verdict_digest='sha256:' + '8' * 64,
        enforcement_plan_digest='sha256:' + '9' * 64,
        governance_trace_digest='sha256:' + 'a' * 64,
        scope_decision_digest='sha256:' + 'b' * 64,
        capability_compatibility_digest='sha256:' + 'c' * 64,
        approval_attestation_digest='',
        controls=RuntimeControlProjection(
            max_output_bytes=4096,
            output_digest_required=True,
        ),
        authorization=grant,
    )
    return replace(item, decision_digest=_governance_decision_body_digest(item))


def _receipt(
    decision: GovernanceDecision,
    **overrides: object,
) -> RuntimeReceiptBinding:
    assert decision.authorization is not None
    grant = decision.authorization
    values: dict[str, object] = {
        'receipt_id': 'runtime-receipt:attempt-1',
        'operation_id': grant.operation_id,
        'step_id': grant.step_id,
        'attempt_id': grant.attempt_id,
        'runtime_instance_id': grant.runtime_instance_id,
        'decision_digest': decision.decision_digest,
        'runtime_permit_digest': PERMIT_DIGEST,
        'lease_id': grant.lease_id,
        'lease_epoch': grant.lease_epoch,
        'fencing_token_digest': grant.fencing_token_digest,
        'execution_spec_digest': grant.execution_spec_digest,
        'payload_digest': grant.payload_digest,
        'requested_scope_digest': grant.requested_scope_digest,
        'capability_inventory_digest': grant.capability_inventory_digest,
        'inventory_epoch': grant.inventory_epoch,
        'policy_pack_digest': grant.policy_pack_digest,
        'policy_epoch': grant.policy_epoch,
        'terminal_status': 'completed',
        'output_digests': {'record': OUTPUT_DIGEST},
        'output_bytes': 1024,
    }
    values.update(overrides)
    return build_runtime_receipt_binding(**values)  # type: ignore[arg-type]


def test_receipt_conformance_binds_decision_permit_attempt_and_postconditions() -> None:
    decision = _decision()
    result = evaluate_receipt_conformance(
        decision,
        _receipt(decision),
        expected_runtime_permit_digest=PERMIT_DIGEST,
    )

    assert result.conformant is True
    assert result.reason_code == 'receipt_conforms'
    assert result.failures == ()
    assert 'receipt_attempt_bound' in result.checks
    assert 'required_output_digest_present' in result.checks
    assert result.result_digest == receipt_conformance_result_digest(result)


@pytest.mark.parametrize(
    ('field', 'value', 'reason_code'),
    (
        ('decision_digest', DIGEST_B, 'receipt_decision_digest_mismatch'),
        ('attempt_id', 'attempt-other', 'receipt_attempt_id_mismatch'),
        ('lease_epoch', 8, 'receipt_lease_epoch_mismatch'),
        (
            'fencing_token_digest',
            DIGEST_A,
            'receipt_fencing_token_digest_mismatch',
        ),
        (
            'capability_inventory_digest',
            DIGEST_A,
            'receipt_capability_inventory_digest_mismatch',
        ),
        ('inventory_epoch', 12, 'receipt_inventory_epoch_mismatch'),
    ),
)
def test_receipt_binding_drift_is_nonconformant(
    field: str,
    value: object,
    reason_code: str,
) -> None:
    decision = _decision()
    result = evaluate_receipt_conformance(
        decision,
        _receipt(decision, **{field: value}),
        expected_runtime_permit_digest=PERMIT_DIGEST,
    )

    assert result.conformant is False
    assert reason_code in result.failures


def test_receipt_permit_drift_is_nonconformant() -> None:
    decision = _decision()
    result = evaluate_receipt_conformance(
        decision,
        _receipt(decision),
        expected_runtime_permit_digest=DIGEST_A,
    )

    assert result.reason_code == 'receipt_runtime_permit_digest_mismatch'


@pytest.mark.parametrize(
    ('overrides', 'reason_code'),
    (
        ({'output_digests': {}}, 'required_output_digest_missing'),
        ({'output_bytes': 4097}, 'receipt_output_limit_exceeded'),
    ),
)
def test_receipt_postcondition_failure_is_reported(
    overrides: dict[str, object],
    reason_code: str,
) -> None:
    decision = _decision()
    result = evaluate_receipt_conformance(
        decision,
        _receipt(decision, **overrides),
        expected_runtime_permit_digest=PERMIT_DIGEST,
    )

    assert result.conformant is False
    assert reason_code in result.failures


def test_runtime_receipt_digest_drift_is_rejected() -> None:
    decision = _decision()
    receipt = _receipt(decision).as_dict()
    receipt['output_bytes'] = 2048

    with pytest.raises(GovApiError, match='runtime_receipt_digest_mismatch'):
        evaluate_receipt_conformance(
            decision,
            receipt,
            expected_runtime_permit_digest=PERMIT_DIGEST,
        )
