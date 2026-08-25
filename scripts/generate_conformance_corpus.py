from __future__ import annotations

import argparse
import copy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from govengine.approvals import (  # noqa: E402
    ApprovalAttestation,
    approval_attestation_digest,
)
from govengine.capabilities import (  # noqa: E402
    CapabilityInventoryBinding,
    OperationCapabilityRequirements,
    capability_inventory_binding_digest,
    operation_capability_requirements_digest,
)
from govengine.conformance import (  # noqa: E402
    CONFORMANCE_CASE_SCHEMA_VERSION,
    CONFORMANCE_MANIFEST_SCHEMA_VERSION,
)
from govengine.governance import (  # noqa: E402
    GovernanceRequest,
    execution_facts_digest,
    governance_subject_digest,
    requested_scope_digest,
)
from govengine.governance_decision import (  # noqa: E402
    GovernanceAuthorization,
    GovernanceDecision,
    _governance_decision_body_digest,
)
from govengine.governance_decision_signing import sign_governance_decision  # noqa: E402
from govengine.policy import (  # noqa: E402
    PolicyCompiler,
    PolicyEngine,
    RuntimeControlProjection,
    policy_pack_digest,
    policy_verdict_digest,
)
from govengine.receipt_conformance import (  # noqa: E402
    build_runtime_receipt_binding,
    evaluate_receipt_conformance,
    receipt_conformance_result_digest,
)
from govengine.scope_policy import (  # noqa: E402
    ScopePolicyBinding,
    evaluate_scope_policy,
    scope_decision_digest,
    scope_policy_binding_digest,
)
from govengine.signing import DemoDigestSigner  # noqa: E402


CORPUS_ROOT = ROOT / 'govengine' / 'conformance' / 'v1'
FORBIDDEN_OUTPUT_KEYS = [
    'credential',
    'password',
    'raw_output',
    'raw_target',
    'secret',
    'target_url',
    'token',
]
NOW = datetime(2026, 7, 15, 12, 5, tzinfo=timezone.utc)
PERMIT_DIGEST = 'sha256:' + 'c' * 64
OUTPUT_DIGEST = 'sha256:' + 'd' * 64


def _compiled_policy(*, effect: str = 'approval_required') -> Any:
    result = PolicyCompiler().compile(
        {
            'schema_version': 'v1',
            'policy_id': 'production-mutation',
            'version': '1.0.0',
            'issuer_ref': 'organization:example',
            'policy_epoch': 42,
            'validity': {
                'not_before': '2026-07-15T12:00:00Z',
                'expires_at': '2026-07-15T13:00:00Z',
            },
            'supersedes': [],
            'rules': [
                {
                    'rule_id': 'govern-mutation',
                    'effect': effect,
                    'conditions': [
                        {
                            'path': 'action.mode',
                            'operator': 'eq',
                            'value': 'mutation',
                        }
                    ],
                    'reason_code': (
                        'mutation_requires_approval'
                        if effect == 'approval_required'
                        else 'mutation_denied'
                    ),
                    'obligations': [
                        {'obligation_id': 'receipt', 'kind': 'receipt'}
                    ],
                    'constraints': [
                        {
                            'constraint_id': 'bounded-output',
                            'kind': 'output_limit',
                            'value': 4096,
                        }
                    ],
                }
            ],
        }
    )
    if not result.ok or result.policy_pack is None:
        raise AssertionError(result.reason_code)
    return result.policy_pack


def _scope_policy(
    *,
    policy_pack_digest_value: str,
    network_allowed: bool = True,
) -> dict[str, Any]:
    return ScopePolicyBinding.from_mapping(
        {
            'schema_version': 'v1',
            'binding_id': 'scope-policy-1',
            'policy_pack_digest': policy_pack_digest_value,
            'policy_epoch': 42,
            'source_ref': 'policy-pack:production-mutation@1.0.0',
            'attestation_ref': 'catalog-attestation:scope-42',
            'allowed_target_namespaces': ['service.inventory'],
            'network_allowed': network_allowed,
            'allowed_schemes': ['https'] if network_allowed else [],
            'allowed_ports': [443] if network_allowed else [],
            'allowed_address_classes': ['public'] if network_allowed else [],
            'redirect_policy': 'same_origin' if network_allowed else 'deny',
            'private_networks_allowed': False,
        }
    ).as_dict()


def _requested_scope(*, with_destination: bool = True) -> dict[str, Any]:
    payload: dict[str, Any] = {
        'target_namespace': 'service.inventory',
        'environment': 'production',
    }
    if with_destination:
        payload['requested_destination'] = {
            'scheme': 'https',
            'effective_port': 443,
            'address_class': 'public',
            'origin_binding_digest': 'sha256:' + '4' * 64,
        }
    return payload


def _requirements() -> dict[str, Any]:
    return OperationCapabilityRequirements.from_mapping(
        {
            'schema_version': 'v1',
            'requirements_id': 'requirements-1',
            'operation_id': 'op-123',
            'step_id': 'step-4',
            'execution_spec_digest': 'sha256:' + '1' * 64,
            'required_backend_class': 'http_api',
            'side_effect_class': 'mutation',
            'required_capabilities': [
                'connector.inventory.update',
                'network.tls.required',
                'receipt.terminal',
            ],
        }
    ).as_dict()


def _inventory() -> dict[str, Any]:
    return CapabilityInventoryBinding.from_mapping(
        {
            'schema_version': 'v1',
            'inventory_id': 'runtime-inventory-42',
            'runtime_instance_id': 'rexecop-1',
            'runtime_version': '0.3.0rc2',
            'inventory_epoch': 42,
            'source_ref': 'runtime-registry:rexecop-1',
            'attestation_ref': 'runtime-inventory-attestation:42',
            'backend_classes': ['http_api'],
            'side_effect_classes': ['read_only', 'mutation'],
            'capabilities': [
                'connector.inventory.update',
                'network.tls.required',
                'receipt.terminal',
            ],
        }
    ).as_dict()


def _governance_request(*, with_approval: bool = False) -> dict[str, Any]:
    policy_pack = _compiled_policy()
    pack_digest = policy_pack_digest(policy_pack)
    execution_facts = {
        'schema_version': 'v0.1',
        'request_id': 'gov-tx-123',
        'subject_ref': 'governance:op-123:step-4:attempt-2',
        'principal': {'kind': 'operator'},
        'action': {'mode': 'mutation'},
        'resource': {'criticality': 'low'},
        'context': {'environment': 'production'},
        'evidence_refs': [],
        'metadata': {},
    }
    requested_scope = _requested_scope()
    scope_policy = _scope_policy(policy_pack_digest_value=pack_digest)
    requirements = _requirements()
    inventory = _inventory()
    request: dict[str, Any] = {
        'schema_version': 'v1',
        'transaction_id': 'gov-tx-123',
        'operation_id': 'op-123',
        'step_id': 'step-4',
        'attempt_id': 'attempt-2',
        'policy_pack': policy_pack.as_dict(),
        'policy_pack_digest': pack_digest,
        'policy_epoch': 42,
        'execution_facts': execution_facts,
        'execution_facts_digest': execution_facts_digest(execution_facts),
        'execution_spec_digest': 'sha256:' + '1' * 64,
        'payload_digest': 'sha256:' + '2' * 64,
        'requested_scope': requested_scope,
        'requested_scope_digest': requested_scope_digest(requested_scope),
        'scope_policy_binding': scope_policy,
        'scope_policy_binding_digest': scope_policy_binding_digest(scope_policy),
        'capability_requirements': requirements,
        'capability_requirements_digest': (
            operation_capability_requirements_digest(requirements)
        ),
        'capability_inventory': inventory,
        'capability_inventory_digest': capability_inventory_binding_digest(
            inventory
        ),
        'side_effect_class': 'mutation',
        'runtime_instance_id': 'rexecop-1',
        'lease_id': 'lease-55',
        'lease_epoch': 9,
        'fencing_token_digest': 'sha256:' + '3' * 64,
    }
    if with_approval:
        subject = GovernanceRequest.from_mapping(request)
        approval = ApprovalAttestation.from_mapping(
            {
                'schema_version': 'v1',
                'approval_id': 'approval-123',
                'subject_digest': governance_subject_digest(subject),
                'operation_id': request['operation_id'],
                'step_id': request['step_id'],
                'attempt_id': request['attempt_id'],
                'execution_spec_digest': request['execution_spec_digest'],
                'execution_facts_digest': request['execution_facts_digest'],
                'target_scope_digest': request['requested_scope_digest'],
                'policy_pack_digest': request['policy_pack_digest'],
                'policy_epoch': request['policy_epoch'],
                'approved_side_effect_class': request['side_effect_class'],
                'approver_ref': 'operator:alice',
                'approver_role': 'infrastructure-admin',
                'trust_domain': 'organization:example',
                'issued_at': '2026-07-15T12:00:00Z',
                'not_before': '2026-07-15T12:00:00Z',
                'expires_at': '2026-07-15T12:15:00Z',
                'revocation_ref': 'approval-revocations:v1',
                'signature_ref': 'sigstore:bundle-123',
            }
        )
        request['approval_attestation'] = approval.as_dict()
        request['approval_attestation_digest'] = approval_attestation_digest(
            approval
        )
    return request


def _approval_payload(
    *,
    request: Mapping[str, Any] | None = None,
    revoked: bool = False,
    now: str = '2026-07-15T12:05:00+00:00',
) -> dict[str, Any]:
    return {
        'governance_request': dict(request or _governance_request(with_approval=True)),
        'trust_policy': {
            'policy_id': 'production-approvers',
            'trusted_roles': ['infrastructure-admin'],
            'trusted_domains': ['organization:example'],
            'trusted_approver_refs': ['operator:alice'],
            'require_signature_ref': True,
        },
        'revoked': revoked,
        'now': now,
    }


def _activation_binding(
    request: Mapping[str, Any],
    *,
    status: str = 'active',
    not_before: str = '2026-07-15T12:00:00Z',
    expires_at: str = '2026-07-15T13:00:00Z',
) -> dict[str, Any]:
    policy_pack = request['policy_pack']
    return {
        'schema_version': 'v1',
        'binding_id': 'activation:production-mutation:42',
        'policy_id': policy_pack['policy_id'],
        'policy_version': policy_pack['version'],
        'policy_pack_digest': request['policy_pack_digest'],
        'policy_epoch': request['policy_epoch'],
        'issuer_ref': policy_pack['issuer_ref'],
        'trust_ref': 'policy-trust:organization:example',
        'status': status,
        'not_before': not_before,
        'expires_at': expires_at,
    }


def _decision() -> GovernanceDecision:
    grant = GovernanceAuthorization(
        authorization_id='gov-auth:decision-1',
        operation_id='op-1',
        step_id='step-1',
        attempt_id='attempt-1',
        runtime_instance_id='runtime-1',
        lease_id='sha256:' + 'a' * 64,
        lease_epoch=7,
        fencing_token_digest='sha256:' + 'b' * 64,
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
    **overrides: Any,
) -> dict[str, Any]:
    if decision.authorization is None:
        raise AssertionError('decision_without_authorization')
    grant = decision.authorization
    values: dict[str, Any] = {
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
    return build_runtime_receipt_binding(**values).as_dict()


def _runtime_decision_input(
    *,
    facts_patch: Mapping[str, Any] | None = None,
    repeat: int = 1,
) -> dict[str, Any]:
    decision = _decision()
    if decision.authorization is None:
        raise AssertionError('decision_without_authorization')
    facts = {
        key: value
        for key, value in decision.authorization.as_dict().items()
        if key
        in {
            'operation_id',
            'step_id',
            'attempt_id',
            'runtime_instance_id',
            'lease_id',
            'lease_epoch',
            'fencing_token_digest',
            'execution_spec_digest',
            'payload_digest',
            'requested_scope_digest',
            'capability_inventory_digest',
            'inventory_epoch',
        }
    }
    facts.update(facts_patch or {})
    signed = sign_governance_decision(
        decision,
        signer=DemoDigestSigner(signer_id='conformance-decision-signer'),
        payload_ref='artifact://conformance/decision-1',
    )
    return {
        'governance_decision': decision.as_dict(),
        'signed_artifact': signed.as_dict(),
        'runtime_facts': facts,
        'repeat': repeat,
    }


def _case(
    *,
    case_id: str,
    owner: str,
    operation: str,
    input_payload: Mapping[str, Any],
    govengine: tuple[str, str],
    rexecop: tuple[str, str] | None = None,
    binding_digests: Mapping[str, str] | str = 'not_applicable',
) -> dict[str, Any]:
    return {
        'schema_version': CONFORMANCE_CASE_SCHEMA_VERSION,
        'case_id': case_id,
        'owner': owner,
        'operation': operation,
        'input': dict(input_payload),
        'expected': {
            'govengine': {
                'status': govengine[0],
                'reason_code': govengine[1],
            },
            'rexecop': {
                'status': (rexecop or govengine)[0],
                'reason_code': (rexecop or govengine)[1],
            },
        },
        'binding_digests': (
            dict(binding_digests)
            if isinstance(binding_digests, Mapping)
            else binding_digests
        ),
        'max_schema_version': 'v1',
        'forbidden_output_keys': FORBIDDEN_OUTPUT_KEYS,
    }


def _cases() -> dict[str, dict[str, Any]]:
    cases: dict[str, dict[str, Any]] = {}

    no_network_scope = _requested_scope(with_destination=False)
    no_network_policy = _scope_policy(
        policy_pack_digest_value='sha256:' + 'e' * 64,
        network_allowed=False,
    )
    no_network_decision = evaluate_scope_policy(no_network_scope, no_network_policy)
    cases['valid/readonly-no-network.json'] = _case(
        case_id='readonly-no-network',
        owner='govengine',
        operation='evaluate_scope',
        input_payload={
            'requested_scope': no_network_scope,
            'scope_policy_binding': no_network_policy,
        },
        govengine=('allowed', 'scope_allowed'),
        binding_digests={
            'scope_decision_digest': scope_decision_digest(no_network_decision)
        },
    )

    http_scope = _requested_scope()
    http_policy = _scope_policy(policy_pack_digest_value='sha256:' + 'e' * 64)
    http_decision = evaluate_scope_policy(http_scope, http_policy)
    cases['valid/readonly-http-policy-authorized.json'] = _case(
        case_id='readonly-http-policy-authorized',
        owner='govengine',
        operation='evaluate_scope',
        input_payload={
            'requested_scope': http_scope,
            'scope_policy_binding': http_policy,
        },
        govengine=('allowed', 'scope_allowed'),
        binding_digests={
            'scope_decision_digest': scope_decision_digest(http_decision)
        },
    )

    policy = _compiled_policy()
    request = {
        'request_id': 'conformance-approval-required',
        'subject_ref': 'artifact://conformance/mutation',
        'action': {'mode': 'mutation'},
        'resource': {'criticality': 'low'},
        'evidence_refs': ['admission:opaque-reference'],
    }
    verdict = PolicyEngine().evaluate(request, policy)
    policy_bindings = {
        'policy_pack_digest': policy_pack_digest(policy),
        'policy_verdict_digest': policy_verdict_digest(verdict),
    }
    cases['valid/approval-required.json'] = _case(
        case_id='approval-required',
        owner='govengine',
        operation='evaluate_policy',
        input_payload={'policy_pack': policy.as_dict(), 'request': request},
        govengine=('approval_required', 'mutation_requires_approval'),
        binding_digests=policy_bindings,
    )

    cases['valid/approved-attempt-bound.json'] = _case(
        case_id='approved-attempt-bound',
        owner='rexecop',
        operation='consume_decision',
        input_payload=_runtime_decision_input(),
        govengine=('not_applicable', 'not_applicable'),
        rexecop=('allowed', 'governance_decision_claimed'),
    )

    decision = _decision()
    receipt = _receipt(decision)
    receipt_result = evaluate_receipt_conformance(
        decision,
        receipt,
        expected_runtime_permit_digest=PERMIT_DIGEST,
    )
    cases['valid/receipt-conformant.json'] = _case(
        case_id='receipt-conformant',
        owner='govengine',
        operation='evaluate_receipt',
        input_payload={
            'governance_decision': decision.as_dict(),
            'runtime_receipt_binding': receipt,
            'expected_runtime_permit_digest': PERMIT_DIGEST,
        },
        govengine=('conformant', 'receipt_conforms'),
        binding_digests={
            'receipt_conformance_result_digest': (
                receipt_conformance_result_digest(receipt_result)
            )
        },
    )

    unknown = decision.as_dict()
    unknown['status'] = 'unexpected'
    cases['invalid/unknown-enum-fail-open.json'] = _case(
        case_id='unknown-enum-fail-open',
        owner='govengine',
        operation='validate_governance_decision',
        input_payload={'governance_decision': unknown},
        govengine=('rejected', 'unknown_governance_decision_status'),
    )
    cases['invalid/nan-number.json'] = _case(
        case_id='nan-number',
        owner='govengine',
        operation='parse_json',
        input_payload={'source': '{"value": NaN}'},
        govengine=('rejected', 'json_boundary_non_finite_number'),
    )
    cases['invalid/duplicate-json-key.json'] = _case(
        case_id='duplicate-json-key',
        owner='govengine',
        operation='parse_json',
        input_payload={'source': '{"value": 1, "value": 2}'},
        govengine=('rejected', 'json_boundary_duplicate_key'),
    )
    cases['invalid/non-ascii-binding.json'] = _case(
        case_id='non-ascii-binding',
        owner='govengine',
        operation='validate_governance_boundary',
        input_payload={'kind': 'ascii_identifier', 'value': 'operacja-ż'},
        govengine=('rejected', 'invalid_governance_identifier'),
    )

    naive_activation = _activation_binding(
        _governance_request(),
        not_before='2026-07-15T12:00:00',
    )
    cases['invalid/timezone-naive-timestamp.json'] = _case(
        case_id='timezone-naive-timestamp',
        owner='govengine',
        operation='validate_policy_activation',
        input_payload={'policy_activation_binding': naive_activation},
        govengine=('rejected', 'invalid_policy_activation_not_before'),
    )

    forbidden = _governance_request()
    forbidden['execution_facts'] = {'items': [{'password': 'inline-secret'}]}
    cases['invalid/forbidden-key-inside-list.json'] = _case(
        case_id='forbidden-key-inside-list',
        owner='govengine',
        operation='validate_governance_request',
        input_payload={'governance_request': forbidden},
        govengine=('rejected', 'forbidden_governance_input'),
    )

    descriptor = _governance_request()
    descriptor['capability_inventory']['capabilities'].append('unexpected.capability')
    cases['invalid/capability-descriptor-digest-mismatch.json'] = _case(
        case_id='capability-descriptor-digest-mismatch',
        owner='govengine',
        operation='validate_governance_request',
        input_payload={'governance_request': descriptor},
        govengine=('rejected', 'capability_inventory_digest_mismatch'),
    )
    facts_drift = _governance_request()
    facts_drift['execution_facts']['action']['mode'] = 'read'
    cases['invalid/execution-facts-digest-mismatch.json'] = _case(
        case_id='execution-facts-digest-mismatch',
        owner='govengine',
        operation='validate_governance_request',
        input_payload={'governance_request': facts_drift},
        govengine=('rejected', 'execution_facts_digest_mismatch'),
    )
    opaque = _governance_request()
    opaque['approval_evidence_ref'] = 'opaque:approval'
    cases['invalid/opaque-approval-ref.json'] = _case(
        case_id='opaque-approval-ref',
        owner='govengine',
        operation='validate_governance_request',
        input_payload={'governance_request': opaque},
        govengine=('rejected', 'unknown_governance_request_field'),
    )
    cases['invalid/admission-used-as-approval.json'] = _case(
        case_id='admission-used-as-approval',
        owner='govengine',
        operation='evaluate_policy',
        input_payload={'policy_pack': policy.as_dict(), 'request': request},
        govengine=('approval_required', 'mutation_requires_approval'),
        binding_digests=policy_bindings,
    )

    for filename, field, value, reason in (
        (
            'approval-different-spec.json',
            'execution_spec_digest',
            'sha256:' + 'f' * 64,
            'approval_execution_spec_digest_mismatch',
        ),
        (
            'approval-different-target.json',
            'target_scope_digest',
            'sha256:' + 'f' * 64,
            'approval_target_scope_digest_mismatch',
        ),
        (
            'approval-different-attempt.json',
            'attempt_id',
            'attempt-other',
            'approval_attempt_id_mismatch',
        ),
    ):
        approval_request = _governance_request(with_approval=True)
        approval = dict(approval_request['approval_attestation'])
        approval[field] = value
        checked_approval = ApprovalAttestation.from_mapping(approval)
        approval_request['approval_attestation'] = checked_approval.as_dict()
        approval_request['approval_attestation_digest'] = (
            approval_attestation_digest(checked_approval)
        )
        cases[f'invalid/{filename}'] = _case(
            case_id=filename.removesuffix('.json'),
            owner='govengine',
            operation='validate_approval',
            input_payload=_approval_payload(request=approval_request),
            govengine=('rejected', reason),
        )

    cases['invalid/approval-expired.json'] = _case(
        case_id='approval-expired',
        owner='govengine',
        operation='validate_approval',
        input_payload=_approval_payload(now='2026-07-15T12:15:00+00:00'),
        govengine=('rejected', 'approval_expired'),
    )
    cases['invalid/approval-revoked.json'] = _case(
        case_id='approval-revoked',
        owner='govengine',
        operation='validate_approval',
        input_payload=_approval_payload(revoked=True),
        govengine=('rejected', 'approval_revoked'),
    )
    cases['invalid/approval-not-yet-valid.json'] = _case(
        case_id='approval-not-yet-valid',
        owner='govengine',
        operation='validate_approval',
        input_payload=_approval_payload(now='2026-07-15T11:59:00+00:00'),
        govengine=('rejected', 'approval_not_yet_valid'),
    )

    for status, reason_code in (
        ('superseded', 'policy_superseded'),
        ('revoked', 'policy_revoked'),
        ('expired', 'policy_expired'),
    ):
        activation_request = _governance_request()
        cases[f'invalid/activation-{status}.json'] = _case(
            case_id=f'activation-{status}',
            owner='govengine',
            operation='evaluate_governance',
            input_payload={
                'governance_request': activation_request,
                'policy_activation_binding': _activation_binding(
                    activation_request,
                    status=status,
                ),
                'evaluated_at': '2026-07-15T12:05:00+00:00',
            },
            govengine=('rejected', reason_code),
        )

    epoch_drift = _governance_request()
    epoch_drift['scope_policy_binding']['policy_epoch'] = 43
    epoch_drift['scope_policy_binding_digest'] = scope_policy_binding_digest(
        epoch_drift['scope_policy_binding']
    )
    cases['invalid/policy-epoch-drift.json'] = _case(
        case_id='policy-epoch-drift',
        owner='govengine',
        operation='validate_governance_request',
        input_payload={'governance_request': epoch_drift},
        govengine=('rejected', 'scope_policy_epoch_mismatch'),
    )
    self_authorized = _governance_request()
    self_authorized['requested_scope']['allowed_schemes'] = ['https']
    cases['invalid/self-authorized-destination.json'] = _case(
        case_id='self-authorized-destination',
        owner='govengine',
        operation='validate_governance_request',
        input_payload={'governance_request': self_authorized},
        govengine=('rejected', 'self_authorized_scope_policy'),
    )

    empty_requirements = _requirements()
    empty_requirements['required_capabilities'] = []
    cases['invalid/backend-derived-requirements.json'] = _case(
        case_id='backend-derived-requirements',
        owner='govengine',
        operation='evaluate_capability',
        input_payload={
            'requirements': empty_requirements,
            'inventory': _inventory(),
        },
        govengine=('rejected', 'operation_capability_requirements_empty'),
    )
    host_claim = _inventory()
    host_claim['plugin_registered'] = True
    cases['invalid/host-claimed-plugin.json'] = _case(
        case_id='host-claimed-plugin',
        owner='govengine',
        operation='evaluate_capability',
        input_payload={'requirements': _requirements(), 'inventory': host_claim},
        govengine=('rejected', 'self_attested_capability_support'),
    )
    inventory_drift = _governance_request()
    inventory_drift['capability_inventory']['inventory_epoch'] = 43
    cases['invalid/inventory-drift.json'] = _case(
        case_id='inventory-drift',
        owner='govengine',
        operation='validate_governance_request',
        input_payload={'governance_request': inventory_drift},
        govengine=('rejected', 'capability_inventory_digest_mismatch'),
    )

    for filename, facts_patch in (
        ('wrong-runtime-instance.json', {'runtime_instance_id': 'runtime-other'}),
        ('stale-lease-epoch.json', {'lease_epoch': 8}),
        (
            'wrong-fencing-token.json',
            {'fencing_token_digest': 'sha256:' + 'f' * 64},
        ),
        ('wrong-attempt-id.json', {'attempt_id': 'attempt-other'}),
    ):
        cases[f'invalid/{filename}'] = _case(
            case_id=filename.removesuffix('.json'),
            owner='rexecop',
            operation='consume_decision',
            input_payload=_runtime_decision_input(facts_patch=facts_patch),
            govengine=('not_applicable', 'not_applicable'),
            rexecop=('rejected', 'governance_decision_binding_drift'),
        )
    cases['invalid/reused-decision-nonce.json'] = _case(
        case_id='reused-decision-nonce',
        owner='rexecop',
        operation='consume_decision',
        input_payload=_runtime_decision_input(repeat=2),
        govengine=('not_applicable', 'not_applicable'),
        rexecop=('rejected', 'governance_decision_reused'),
    )

    tampered_decision = decision.as_dict()
    tampered_decision['request_digest'] = 'sha256:' + 'f' * 64
    cases['invalid/signed-decision-body-tamper.json'] = _case(
        case_id='signed-decision-body-tamper',
        owner='govengine',
        operation='validate_governance_decision',
        input_payload={'governance_decision': tampered_decision},
        govengine=('rejected', 'governance_decision_digest_mismatch'),
    )

    conflicting_policy = policy.as_dict()
    conflicting_rule = dict(conflicting_policy['rules'][0])
    conflicting_rule['rule_id'] = 'deny-mutation'
    conflicting_rule['effect'] = 'deny'
    conflicting_rule['reason_code'] = 'mutation_denied'
    conflicting_policy['rules'].append(conflicting_rule)
    cases['invalid/conflicting-policy-rules.json'] = _case(
        case_id='conflicting-policy-rules',
        owner='govengine',
        operation='compile_policy',
        input_payload={'policy_pack': conflicting_policy},
        govengine=('rejected', 'conflicting_policy_rules'),
    )

    receipt_cases = (
        (
            'receipt-wrong-decision.json',
            _receipt(decision, decision_digest='sha256:' + 'f' * 64),
            PERMIT_DIGEST,
            'receipt_decision_digest_mismatch',
        ),
        (
            'receipt-wrong-runtime-permit.json',
            receipt,
            'sha256:' + 'f' * 64,
            'receipt_runtime_permit_digest_mismatch',
        ),
        (
            'receipt-missing-output-digest.json',
            _receipt(decision, output_digests={}),
            PERMIT_DIGEST,
            'required_output_digest_missing',
        ),
        (
            'receipt-output-over-limit.json',
            _receipt(decision, output_bytes=4097),
            PERMIT_DIGEST,
            'receipt_output_limit_exceeded',
        ),
    )
    for filename, drifted_receipt, permit, reason in receipt_cases:
        cases[f'invalid/{filename}'] = _case(
            case_id=filename.removesuffix('.json'),
            owner='govengine',
            operation='evaluate_receipt',
            input_payload={
                'governance_decision': decision.as_dict(),
                'runtime_receipt_binding': drifted_receipt,
                'expected_runtime_permit_digest': permit,
            },
            govengine=('nonconformant', reason),
        )
    overclaim = copy.deepcopy(receipt)
    overclaim['claimed_authority'] = 'mutation_ready'
    cases['invalid/receipt-overclaim.json'] = _case(
        case_id='receipt-overclaim',
        owner='govengine',
        operation='evaluate_receipt',
        input_payload={
            'governance_decision': decision.as_dict(),
            'runtime_receipt_binding': overclaim,
            'expected_runtime_permit_digest': PERMIT_DIGEST,
        },
        govengine=('rejected', 'unknown_runtime_receipt_binding_field'),
    )
    return cases


def corpus_files() -> dict[Path, str]:
    cases = _cases()
    files = {
        CORPUS_ROOT / relative: json.dumps(
            case,
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        + '\n'
        for relative, case in cases.items()
    }
    manifest = {
        'schema_version': CONFORMANCE_MANIFEST_SCHEMA_VERSION,
        'corpus_version': 'v1',
        'case_count': len(cases),
        'cases': sorted(cases),
        'runners': ['govengine', 'rexecop'],
        'non_claims': [
            'Corpus success does not prove a non-Python implementation exists.',
            'RExecOp remains the reference runtime consumer.',
            'A malicious in-process host remains inside the trusted computing base.',
        ],
    }
    files[CORPUS_ROOT / 'manifest.json'] = (
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + '\n'
    )
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    expected = corpus_files()
    if args.check:
        drift = [
            str(path.relative_to(ROOT))
            for path, content in expected.items()
            if not path.exists() or path.read_text(encoding='utf-8') != content
        ]
        actual = {
            path
            for path in CORPUS_ROOT.rglob('*.json')
            if path not in expected
        }
        drift.extend(str(path.relative_to(ROOT)) for path in sorted(actual))
        if drift:
            raise SystemExit(f"conformance_corpus_drift:{','.join(sorted(drift))}")
        print(f'conformance_corpus_current:cases={len(expected) - 1}')
        return 0
    for path, content in expected.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
    print(f'conformance_corpus_generated:cases={len(expected) - 1}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
