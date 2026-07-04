from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from govengine.api import GovApiError, require_mapping
from govengine.admission import validate_admission_decision
from govengine.policy.enforcement import (
    PolicyEnforcementPlan,
    policy_enforcement_admission,
    policy_enforcement_admission_digest,
    policy_enforcement_plan_digest,
    policy_verdict_digest,
)
from govengine.policy.model import (
    POLICY_REQUEST_SCHEMA_VERSION,
    PolicyRequest,
    PolicyVerdict,
    validate_policy_request,
    validate_policy_verdict,
)
from govengine.review import GovEvidenceRequirement
from govengine.signing import govengine_record_digest

GOVERNANCE_TRACE_SCHEMA_VERSION = 'v0.1'

_TRACE_NON_CLAIMS = (
    'Does not execute work or store SCLite artifacts.',
    'Does not prove a host enforced projected controls.',
    'Binds digest references only; raw policy payloads stay host-owned.',
)


@dataclass(frozen=True)
class GovernanceTrace:
    """Digest-bound governance projection for truth-path consumers."""

    schema_version: str
    trace_id: str
    subject_ref: str
    policy_request_digest: str
    policy_verdict_digest: str
    enforcement_plan_digest: str
    admission_digest: str
    required_controls: tuple[str, ...] = ()
    evidence_requirements: tuple[Mapping[str, Any], ...] = ()
    trace_digest: str = ''
    non_claims: tuple[str, ...] = field(default_factory=lambda: _TRACE_NON_CLAIMS)

    def as_dict(self) -> dict[str, Any]:
        return {
            'schema_version': self.schema_version,
            'trace_id': self.trace_id,
            'subject_ref': self.subject_ref,
            'policy_request_digest': self.policy_request_digest,
            'policy_verdict_digest': self.policy_verdict_digest,
            'enforcement_plan_digest': self.enforcement_plan_digest,
            'admission_digest': self.admission_digest,
            'required_controls': list(self.required_controls),
            'evidence_requirements': [dict(item) for item in self.evidence_requirements],
            'trace_digest': self.trace_digest,
            'non_claims': list(self.non_claims),
        }


def policy_request_digest(request: Mapping[str, Any] | PolicyRequest) -> str:
    checked = validate_policy_request(request)
    return govengine_record_digest(
        checked,
        record_type='govengine.policy.model.PolicyRequest',
        schema_version=POLICY_REQUEST_SCHEMA_VERSION,
    )


def _evidence_requirements_from_plan(
    plan: PolicyEnforcementPlan,
) -> tuple[Mapping[str, Any], ...]:
    requirements: list[dict[str, Any]] = []
    controls = plan.controls
    if controls.receipt_required:
        requirements.append(
            GovEvidenceRequirement(
                requirement_id='receipt_required',
                subject_ref=plan.subject_ref,
                evidence_kind='execution_receipt',
                min_receipt_status='dry-run',
                metadata={'source': 'policy_enforcement_controls'},
            ).as_dict()
        )
    if controls.output_digest_required:
        requirements.append(
            GovEvidenceRequirement(
                requirement_id='output_digest_required',
                subject_ref=plan.subject_ref,
                evidence_kind='execution_receipt',
                min_receipt_status='dry-run',
                metadata={'source': 'policy_enforcement_controls'},
            ).as_dict()
        )
    return tuple(requirements)


def _required_controls_from_plan(plan: PolicyEnforcementPlan) -> tuple[str, ...]:
    controls = plan.controls
    merged = set(controls.typed_execution_control_ids) | set(controls.control_ids)
    if controls.receipt_required:
        merged.add('receipt_required')
    if controls.output_digest_required:
        merged.add('output_digest_required')
    if controls.read_only_required:
        merged.add('read_only_posture')
    if controls.no_raw_shell:
        merged.add('no_raw_shell')
    if controls.mutation_requires_approval:
        merged.add('mutation_requires_approval')
    return tuple(sorted(item for item in merged if item))


def project_governance_trace(
    *,
    policy_request: Mapping[str, Any] | PolicyRequest,
    policy_verdict: Mapping[str, Any] | PolicyVerdict,
    policy_enforcement: Mapping[str, Any],
    trace_id: str = '',
) -> GovernanceTrace:
    """Project one digest-bound governance trace from stored policy bindings."""
    checked_request = validate_policy_request(policy_request)
    checked_verdict = validate_policy_verdict(policy_verdict)
    record = require_mapping(policy_enforcement, reason_code='invalid_policy_enforcement_record')
    plan_raw = record.get('plan')
    admission_raw = record.get('admission')
    plan_digest = str(record.get('plan_digest') or '').strip()
    admission_digest = str(record.get('admission_digest') or '').strip()
    if not isinstance(plan_raw, Mapping) or not plan_digest:
        raise GovApiError('missing_policy_enforcement_plan_binding')
    if not isinstance(admission_raw, Mapping) or not admission_digest:
        raise GovApiError('missing_policy_enforcement_admission_binding')

    plan = PolicyEnforcementPlan.from_mapping(plan_raw)
    admission = validate_admission_decision(admission_raw)
    expected_admission = policy_enforcement_admission(plan)
    if admission.as_dict() != expected_admission.as_dict():
        raise GovApiError('policy_enforcement_admission_drift')
    expected_plan_digest = policy_enforcement_plan_digest(plan)
    expected_admission_digest = policy_enforcement_admission_digest(admission)
    if plan_digest != expected_plan_digest:
        raise GovApiError('policy_enforcement_plan_digest_mismatch')
    if admission_digest != expected_admission_digest:
        raise GovApiError('policy_enforcement_admission_digest_mismatch')

    request_digest = policy_request_digest(checked_request)
    verdict_digest = policy_verdict_digest(checked_verdict)
    if checked_verdict.subject_ref != checked_request.subject_ref:
        raise GovApiError('governance_trace_subject_ref_mismatch')
    if plan.subject_ref != checked_request.subject_ref:
        raise GovApiError('governance_trace_plan_subject_ref_mismatch')
    if admission.subject_ref != checked_request.subject_ref:
        raise GovApiError('governance_trace_admission_subject_ref_mismatch')

    resolved_trace_id = str(trace_id or '').strip() or f'gov-trace:{checked_request.request_id}'
    body = {
        'schema_version': GOVERNANCE_TRACE_SCHEMA_VERSION,
        'trace_id': resolved_trace_id,
        'subject_ref': checked_request.subject_ref,
        'policy_request_digest': request_digest,
        'policy_verdict_digest': verdict_digest,
        'enforcement_plan_digest': plan_digest,
        'admission_digest': admission_digest,
        'required_controls': list(_required_controls_from_plan(plan)),
        'evidence_requirements': [
            dict(item) for item in _evidence_requirements_from_plan(plan)
        ],
    }
    trace_digest = govengine_record_digest(
        body,
        record_type='govengine.governance_trace.GovernanceTrace',
        schema_version=GOVERNANCE_TRACE_SCHEMA_VERSION,
    )
    return GovernanceTrace(
        schema_version=GOVERNANCE_TRACE_SCHEMA_VERSION,
        trace_id=resolved_trace_id,
        subject_ref=checked_request.subject_ref,
        policy_request_digest=request_digest,
        policy_verdict_digest=verdict_digest,
        enforcement_plan_digest=plan_digest,
        admission_digest=admission_digest,
        required_controls=_required_controls_from_plan(plan),
        evidence_requirements=_evidence_requirements_from_plan(plan),
        trace_digest=trace_digest,
    )