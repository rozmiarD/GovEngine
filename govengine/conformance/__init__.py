from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import importlib.resources
from pathlib import Path
from typing import Any, Iterable, Mapping

from govengine._json_boundary import load_bounded_json
from govengine.api import GovApiError, require_mapping
from govengine.approvals import (
    ApprovalRevocationPort,
    ApprovalTrustPolicy,
    approval_attestation_digest,
    validate_approval_attestation,
)
from govengine.capabilities import (
    capability_compatibility_decision_digest,
    evaluate_capability_compatibility,
)
from govengine.governance import (
    governance_request_digest,
    validate_governance_request,
)
from govengine.governance_decision import GovernanceDecision, validate_governance_decision
from govengine.policy import (
    PolicyCompiler,
    PolicyEngine,
    policy_pack_digest,
    policy_verdict_digest,
)
from govengine.receipt_conformance import (
    evaluate_receipt_conformance,
    receipt_conformance_result_digest,
)
from govengine.scope_policy import evaluate_scope_policy, scope_decision_digest


CONFORMANCE_CASE_SCHEMA_VERSION = 'govengine.conformance_case.v1'
CONFORMANCE_MANIFEST_SCHEMA_VERSION = 'govengine.conformance_manifest.v1'
CONFORMANCE_RUNNERS = ('govengine', 'rexecop')
_FORBIDDEN_OUTPUT_KEYS = frozenset(
    {
        'password',
        'secret',
        'token',
        'credential',
        'raw_output',
        'raw_target',
        'target_url',
    }
)


@dataclass(frozen=True)
class ConformanceOutcome:
    status: str
    reason_code: str
    binding_digests: Mapping[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            'status': self.status,
            'reason_code': self.reason_code,
            'binding_digests': dict(self.binding_digests),
        }


class _Revocations(ApprovalRevocationPort):
    def __init__(self, *, revoked: bool) -> None:
        self.revoked = revoked

    def is_revoked(
        self,
        approval_id: str,
        *,
        approval_digest: str,
        revocation_ref: str,
    ) -> bool:
        return self.revoked


def conformance_root() -> Path:
    return Path(str(importlib.resources.files('govengine').joinpath('conformance', 'v1')))


def load_conformance_manifest(root: Path | None = None) -> Mapping[str, Any]:
    base = root or conformance_root()
    manifest = load_bounded_json(
        (base / 'manifest.json').read_bytes(),
        max_bytes=256_000,
    )
    checked = require_mapping(
        manifest,
        reason_code='invalid_conformance_manifest',
    )
    if checked.get('schema_version') != CONFORMANCE_MANIFEST_SCHEMA_VERSION:
        raise GovApiError('unknown_conformance_manifest_schema_version')
    return checked


def iter_conformance_cases(root: Path | None = None) -> tuple[Mapping[str, Any], ...]:
    base = root or conformance_root()
    manifest = load_conformance_manifest(base)
    raw_cases = manifest.get('cases')
    if not isinstance(raw_cases, list) or not raw_cases:
        raise GovApiError('conformance_manifest_without_cases')
    cases: list[Mapping[str, Any]] = []
    seen: set[str] = set()
    for relative in raw_cases:
        if not isinstance(relative, str) or not relative.endswith('.json'):
            raise GovApiError('invalid_conformance_case_path')
        resolved = (base / relative).resolve()
        if base.resolve() not in resolved.parents:
            raise GovApiError('conformance_case_path_escape')
        value = load_bounded_json(resolved.read_bytes(), max_bytes=512_000)
        case = validate_conformance_case(value)
        case_id = str(case['case_id'])
        if case_id in seen:
            raise GovApiError('duplicate_conformance_case_id')
        seen.add(case_id)
        cases.append(case)
    return tuple(cases)


def validate_conformance_case(value: Any) -> Mapping[str, Any]:
    case = require_mapping(value, reason_code='invalid_conformance_case')
    required = {
        'schema_version',
        'case_id',
        'owner',
        'operation',
        'input',
        'expected',
        'binding_digests',
        'max_schema_version',
        'forbidden_output_keys',
    }
    if set(case) != required:
        raise GovApiError('invalid_conformance_case_fields')
    if case.get('schema_version') != CONFORMANCE_CASE_SCHEMA_VERSION:
        raise GovApiError('unknown_conformance_case_schema_version')
    if case.get('owner') not in CONFORMANCE_RUNNERS:
        raise GovApiError('unknown_conformance_case_owner')
    if case.get('max_schema_version') != 'v1':
        raise GovApiError('invalid_conformance_case_max_schema_version')
    case_id = case.get('case_id')
    operation = case.get('operation')
    if not isinstance(case_id, str) or not case_id:
        raise GovApiError('missing_conformance_case_id')
    if not isinstance(operation, str) or not operation:
        raise GovApiError('missing_conformance_case_operation')
    require_mapping(case.get('input'), reason_code='invalid_conformance_case_input')
    expected = require_mapping(
        case.get('expected'),
        reason_code='invalid_conformance_case_expected',
    )
    if set(expected) != set(CONFORMANCE_RUNNERS):
        raise GovApiError('invalid_conformance_case_runner_expectations')
    for runner in CONFORMANCE_RUNNERS:
        outcome = require_mapping(
            expected[runner],
            reason_code='invalid_conformance_case_expected_outcome',
        )
        if set(outcome) != {'status', 'reason_code'}:
            raise GovApiError('invalid_conformance_case_expected_outcome')
        if not all(isinstance(outcome[key], str) and outcome[key] for key in outcome):
            raise GovApiError('invalid_conformance_case_expected_outcome')
    binding_digests = case.get('binding_digests')
    if binding_digests != 'not_applicable':
        bindings = require_mapping(
            binding_digests,
            reason_code='invalid_conformance_case_binding_digests',
        )
        if any(
            not isinstance(key, str)
            or not isinstance(digest, str)
            or not digest.startswith('sha256:')
            for key, digest in bindings.items()
        ):
            raise GovApiError('invalid_conformance_case_binding_digests')
    forbidden = case.get('forbidden_output_keys')
    if not isinstance(forbidden, list) or set(forbidden) != _FORBIDDEN_OUTPUT_KEYS:
        raise GovApiError('invalid_conformance_case_forbidden_output_keys')
    return case


def run_govengine_conformance_case(case: Mapping[str, Any]) -> ConformanceOutcome:
    checked = validate_conformance_case(case)
    expected = require_mapping(
        require_mapping(
            checked['expected'],
            reason_code='invalid_conformance_case_expected',
        )['govengine'],
        reason_code='invalid_conformance_case_expected_outcome',
    )
    if expected['status'] == 'not_applicable':
        return ConformanceOutcome('not_applicable', 'not_applicable')
    operation = str(checked['operation'])
    payload = require_mapping(
        checked['input'],
        reason_code='invalid_conformance_case_input',
    )
    try:
        outcome = _run_operation(operation, payload)
    except GovApiError as exc:
        outcome = ConformanceOutcome('rejected', exc.reason_code)
    _assert_public_outcome(outcome, checked['forbidden_output_keys'])
    return outcome


def assert_conformance_outcome(
    case: Mapping[str, Any],
    outcome: ConformanceOutcome,
    *,
    runner: str,
) -> None:
    checked = validate_conformance_case(case)
    if runner not in CONFORMANCE_RUNNERS:
        raise GovApiError('unknown_conformance_runner')
    expected = require_mapping(
        require_mapping(
            checked['expected'],
            reason_code='invalid_conformance_case_expected',
        )[runner],
        reason_code='invalid_conformance_case_expected_outcome',
    )
    if (outcome.status, outcome.reason_code) != (
        expected['status'],
        expected['reason_code'],
    ):
        raise AssertionError(
            f"conformance_outcome_mismatch:{checked['case_id']}:{runner}:"
            f"{outcome.status}:{outcome.reason_code}"
        )
    binding_digests = checked['binding_digests']
    if binding_digests != 'not_applicable' and dict(outcome.binding_digests) != dict(
        require_mapping(
            binding_digests,
            reason_code='invalid_conformance_case_binding_digests',
        )
    ):
        raise AssertionError(
            f"conformance_binding_digest_mismatch:{checked['case_id']}:{runner}"
        )


def _run_operation(operation: str, payload: Mapping[str, Any]) -> ConformanceOutcome:
    if operation == 'parse_json':
        source = payload.get('source')
        if not isinstance(source, str):
            raise GovApiError('invalid_conformance_json_source')
        load_bounded_json(source, max_bytes=64_000)
        return ConformanceOutcome('accepted', 'json_valid')
    if operation == 'compile_policy':
        result = PolicyCompiler().compile(
            require_mapping(payload.get('policy_pack'), reason_code='invalid_policy_pack')
        )
        if not result.ok or result.policy_pack is None:
            return ConformanceOutcome('rejected', result.reason_code)
        return ConformanceOutcome(
            'accepted',
            'compiled',
            {'policy_pack_digest': policy_pack_digest(result.policy_pack)},
        )
    if operation == 'evaluate_policy':
        result = PolicyCompiler().compile(
            require_mapping(payload.get('policy_pack'), reason_code='invalid_policy_pack')
        )
        if not result.ok or result.policy_pack is None:
            return ConformanceOutcome('rejected', result.reason_code)
        verdict = PolicyEngine().evaluate(
            require_mapping(payload.get('request'), reason_code='invalid_policy_request'),
            result.policy_pack,
        )
        status = {
            'allow': 'allowed',
            'allow_with_obligations': 'allowed',
            'approval_required': 'approval_required',
            'deny': 'denied',
        }[verdict.decision]
        return ConformanceOutcome(
            status,
            verdict.reason_code,
            {
                'policy_pack_digest': policy_pack_digest(result.policy_pack),
                'policy_verdict_digest': policy_verdict_digest(verdict),
            },
        )
    if operation == 'validate_governance_request':
        request = validate_governance_request(
            require_mapping(
                payload.get('governance_request'),
                reason_code='invalid_governance_request',
            )
        )
        return ConformanceOutcome(
            'accepted',
            'governance_request_valid',
            {'governance_request_digest': governance_request_digest(request)},
        )
    if operation == 'validate_approval':
        request = validate_governance_request(
            require_mapping(
                payload.get('governance_request'),
                reason_code='invalid_governance_request',
            )
        )
        trust_payload = require_mapping(
            payload.get('trust_policy'),
            reason_code='invalid_approval_trust_policy',
        )
        trust = ApprovalTrustPolicy(
            policy_id=str(trust_payload.get('policy_id') or ''),
            trusted_roles=tuple(_string_items(trust_payload.get('trusted_roles'))),
            trusted_domains=tuple(_string_items(trust_payload.get('trusted_domains'))),
            trusted_approver_refs=tuple(
                _string_items(trust_payload.get('trusted_approver_refs', []))
            ),
            require_signature_ref=trust_payload.get('require_signature_ref') is True,
        )
        now = payload.get('now')
        if not isinstance(now, str):
            raise GovApiError('invalid_conformance_approval_time')
        approval = validate_approval_attestation(
            request.approval_attestation,
            request=request,
            trust_policy=trust,
            revocation_port=_Revocations(revoked=payload.get('revoked') is True),
            now=datetime.fromisoformat(now),
        )
        return ConformanceOutcome(
            'accepted',
            'approval_valid',
            {'approval_attestation_digest': approval_attestation_digest(approval)},
        )
    if operation == 'evaluate_scope':
        scope_decision = evaluate_scope_policy(
            require_mapping(
                payload.get('requested_scope'),
                reason_code='invalid_requested_scope',
            ),
            require_mapping(
                payload.get('scope_policy_binding'),
                reason_code='invalid_scope_policy_binding',
            ),
        )
        return ConformanceOutcome(
            'allowed' if scope_decision.allowed else 'denied',
            scope_decision.reason_code,
            {'scope_decision_digest': scope_decision_digest(scope_decision)},
        )
    if operation == 'evaluate_capability':
        capability_decision = evaluate_capability_compatibility(
            require_mapping(
                payload.get('requirements'),
                reason_code='invalid_operation_capability_requirements',
            ),
            require_mapping(
                payload.get('inventory'),
                reason_code='invalid_capability_inventory_binding',
            ),
        )
        return ConformanceOutcome(
            'allowed' if capability_decision.compatible else 'denied',
            capability_decision.reason_code,
            {
                'capability_compatibility_digest': (
                    capability_compatibility_decision_digest(capability_decision)
                )
            },
        )
    if operation == 'validate_governance_decision':
        governance_decision = validate_governance_decision(
            GovernanceDecision.from_mapping(
                require_mapping(
                    payload.get('governance_decision'),
                    reason_code='invalid_governance_decision',
                )
            )
        )
        return ConformanceOutcome(
            'accepted',
            'governance_decision_valid',
            {'governance_decision_digest': governance_decision.decision_digest},
        )
    if operation == 'evaluate_receipt':
        receipt_decision = GovernanceDecision.from_mapping(
            require_mapping(
                payload.get('governance_decision'),
                reason_code='invalid_governance_decision',
            )
        )
        receipt = require_mapping(
            payload.get('runtime_receipt_binding'),
            reason_code='invalid_runtime_receipt_binding',
        )
        permit = payload.get('expected_runtime_permit_digest')
        if not isinstance(permit, str):
            raise GovApiError('invalid_expected_runtime_permit_digest')
        receipt_result = evaluate_receipt_conformance(
            receipt_decision,
            receipt,
            expected_runtime_permit_digest=permit,
        )
        return ConformanceOutcome(
            'conformant' if receipt_result.conformant else 'nonconformant',
            receipt_result.reason_code,
            {
                'receipt_conformance_result_digest': (
                    receipt_conformance_result_digest(receipt_result)
                )
            },
        )
    if operation == 'consume_decision':
        return ConformanceOutcome('not_applicable', 'not_applicable')
    raise GovApiError('unknown_conformance_operation')


def _assert_public_outcome(outcome: ConformanceOutcome, forbidden: Any) -> None:
    forbidden_keys = set(_string_items(forbidden))
    payload = outcome.as_dict()

    def walk(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, nested in value.items():
                if key in forbidden_keys:
                    raise AssertionError(f'conformance_forbidden_output_key:{key}')
                walk(nested)
        elif isinstance(value, list):
            for nested in value:
                walk(nested)

    walk(payload)


def _string_items(value: Any) -> Iterable[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise GovApiError('invalid_conformance_case_forbidden_output_keys')
    return value
