from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from govengine.api import GovApiError, require_mapping
from govengine.deconfliction import ArtifactChangeOrder
from govengine.execution.supervision import GovSupervisionPlan, validate_supervision_plan
from govengine.planning import GovPlanIntentContract, GovTaskContract, validate_plan_intent_contract
from govengine.profiles import (
    DomainProfile,
    ProfileConformanceReport,
    ravenclaw_security_profile,
    tecrax_infra_ops_profile,
    validate_profile_conformance,
)
from govengine.review import GovReviewResult, validate_review_result
from govengine.runtime_shell import GovControlAction, GovRuntimeSnapshot, validate_runtime_snapshot


GOVERNANCE_VOCABULARY_TERMS = (
    'objective',
    'policy_constraints',
    'task_plan',
    'runner_bounds',
    'runtime_snapshot',
    'review_result',
    'change_order',
)

FORBIDDEN_PROOF_METADATA_KEYS = (
    'raw_intent',
    'prompt',
    'credential',
    'credentials',
    'secret',
    'token',
    'password',
    'api_key',
    'command',
    'commands',
    'subprocess',
    'shell',
    'live_execution',
    'live_backend',
    'carrier_adapter',
    'carrier_payload',
    'transport_payload',
    'runtime_storage',
    'storage_path',
    'scheduler',
    'schedule',
    'target',
    'target_url',
    'url',
    'pki',
    'kms',
    'key_store',
)


@dataclass(frozen=True)
class GovernanceVocabularyEntry:
    term: str
    govengine_contract: str
    surface: str
    contract_role: str
    architecture_note: str = ''
    non_claims: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out['non_claims'] = list(self.non_claims)
        return out


@dataclass(frozen=True)
class RuntimeContractProof:
    proof_id: str
    profile: DomainProfile
    profile_conformance: ProfileConformanceReport
    intent: GovPlanIntentContract
    policy_constraints: Mapping[str, Any]
    supervision_plan: GovSupervisionPlan
    runtime_snapshot: GovRuntimeSnapshot
    review_result: GovReviewResult
    change_order: ArtifactChangeOrder = field(default_factory=ArtifactChangeOrder)
    evidence_refs: tuple[str, ...] = ()
    vocabulary: tuple[GovernanceVocabularyEntry, ...] = field(default_factory=tuple)
    non_claims: tuple[str, ...] = (
        'Proof does not grant live execution authority.',
        'Proof does not implement carrier adapters.',
        'Proof does not make GovEngine own domain semantics.',
        'Proof does not add a new OODA surface.',
    )
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            'proof_id': self.proof_id,
            'profile': self.profile.as_dict(),
            'profile_conformance': self.profile_conformance.as_dict(),
            'intent': self.intent.as_dict(),
            'policy_constraints': dict(self.policy_constraints),
            'supervision_plan': self.supervision_plan.as_dict(),
            'runtime_snapshot': self.runtime_snapshot.as_dict(),
            'review_result': self.review_result.as_dict(),
            'change_order': self.change_order.as_dict(),
            'evidence_refs': list(self.evidence_refs),
            'vocabulary': [entry.as_dict() for entry in self.vocabulary],
            'non_claims': list(self.non_claims),
            'metadata': dict(self.metadata),
        }


def governance_contract_vocabulary() -> tuple[GovernanceVocabularyEntry, ...]:
    return (
        GovernanceVocabularyEntry(
            term='objective',
            govengine_contract='GovPlanIntentContract.goal',
            surface='planning_contracts_core',
            contract_role='operator/domain objective contract',
            architecture_note='Inspired by objective/control separation, expressed as neutral operator objective.',
            non_claims=('Does not add hierarchy ownership.',),
        ),
        GovernanceVocabularyEntry(
            term='policy_constraints',
            govengine_contract='GovTaskContract.constraints',
            surface='planning_contracts_core',
            contract_role='policy, scope, and aggression constraints',
            architecture_note='Inspired by explicit operating limits, expressed as host-owned policy constraints.',
            non_claims=('Does not authorize target testing or live operations.',),
        ),
        GovernanceVocabularyEntry(
            term='task_plan',
            govengine_contract='GovPlanIntentContract.task_contracts',
            surface='planning_contracts_core',
            contract_role='task/plan contract',
            architecture_note='Inspired by structured task decomposition, expressed as neutral planner-to-runtime handoff.',
            non_claims=('Does not implement a planner.',),
        ),
        GovernanceVocabularyEntry(
            term='runner_bounds',
            govengine_contract='GovSupervisionPlan',
            surface='controlled_execution_core',
            contract_role='ticket/runner bounds',
            architecture_note='Inspired by bounded control design, expressed as dry-run/default-deny runner constraints.',
            non_claims=('Does not grant live backend ownership.',),
        ),
        GovernanceVocabularyEntry(
            term='runtime_snapshot',
            govengine_contract='GovRuntimeSnapshot',
            surface='controlled_execution_core',
            contract_role='runtime, queue, and control snapshot',
            architecture_note='Inspired by operational status reporting, expressed as storage-neutral host snapshot.',
            non_claims=('Does not own runtime storage, queues, or schedulers.',),
        ),
        GovernanceVocabularyEntry(
            term='review_result',
            govengine_contract='GovReviewResult',
            surface='evidence_review_core',
            contract_role='receipt, evidence, and review result',
            architecture_note='Inspired by post-run review discipline, expressed as receipt-bounded review.',
            non_claims=('Does not own SCLite review-bundle verdicts.',),
        ),
        GovernanceVocabularyEntry(
            term='change_order',
            govengine_contract='ArtifactChangeOrder',
            surface='artifact_governance_core',
            contract_role='controlled replan/change-order',
            architecture_note='Inspired by controlled replanning, expressed as artifact change order.',
            non_claims=('Does not bypass admission, supervision, or review gates.',),
        ),
    )


def validate_governance_contract_vocabulary(
    entries: tuple[GovernanceVocabularyEntry, ...] | None = None,
) -> tuple[GovernanceVocabularyEntry, ...]:
    vocabulary = entries if entries is not None else governance_contract_vocabulary()
    terms = tuple(entry.term for entry in vocabulary)
    if terms != GOVERNANCE_VOCABULARY_TERMS:
        raise GovApiError('invalid_governance_contract_vocabulary')
    joined = ' '.join(entry.term for entry in vocabulary)
    if 'OODA' in joined or 'ooda' in joined:
        raise GovApiError('ooda_not_a_new_governance_term')
    return vocabulary


def validate_runtime_contract_proof(value: RuntimeContractProof | Mapping[str, Any]) -> RuntimeContractProof:
    proof = value if isinstance(value, RuntimeContractProof) else _proof_from_mapping(value)
    if not proof.proof_id:
        raise GovApiError('missing_contract_proof_id')
    profile_report = validate_profile_conformance(proof.profile)
    intent = validate_plan_intent_contract(proof.intent)
    supervision = validate_supervision_plan(proof.supervision_plan)
    runtime = validate_runtime_snapshot(proof.runtime_snapshot)
    review = validate_review_result(proof.review_result)
    vocabulary = validate_governance_contract_vocabulary(proof.vocabulary or governance_contract_vocabulary())
    _reject_forbidden_metadata(proof.policy_constraints)
    _reject_forbidden_metadata(proof.metadata)
    if intent.profile != proof.profile.name:
        raise GovApiError('proof_profile_intent_mismatch')
    if runtime.profile != proof.profile.name:
        raise GovApiError('proof_profile_runtime_mismatch')
    if supervision.live_backend_enabled or not supervision.dry_run:
        raise GovApiError('proof_live_execution_not_allowed')
    if not proof.evidence_refs:
        raise GovApiError('missing_contract_proof_evidence_ref')
    if not review.subject_ref:
        raise GovApiError('missing_contract_proof_review_subject')
    return RuntimeContractProof(
        proof_id=proof.proof_id,
        profile=proof.profile,
        profile_conformance=profile_report,
        intent=intent,
        policy_constraints=dict(proof.policy_constraints),
        supervision_plan=supervision,
        runtime_snapshot=runtime,
        review_result=review,
        change_order=proof.change_order,
        evidence_refs=proof.evidence_refs,
        vocabulary=vocabulary,
        non_claims=proof.non_claims,
        metadata=dict(proof.metadata),
    )


def ravenclaw_contract_proof() -> RuntimeContractProof:
    profile = ravenclaw_security_profile()
    task = GovTaskContract(
        contract_id='ravenclaw-security-fixture-task',
        task_family='recon',
        objective='Review a public-safe security workflow fixture.',
        capability='public_safe_security_research',
        target_ref='fixture:web_app:demo',
        target_kind='web_app',
        evidence_goal='receipt_bounded_security_claims',
        constraints={'policy_scope': 'authorized_fixture', 'aggression': 'dry_run_only'},
        metadata={'fixture': 'ravenclaw_security_profile'},
    )
    intent = GovPlanIntentContract(
        intent_id='ravenclaw-security-fixture-intent',
        profile=profile.name,
        planner_id='fixture_profile_planner',
        goal='Demonstrate governed security-research profile handoff without live target testing.',
        task_contracts=(task,),
        non_claims=('Does not authorize live target testing.',),
    )
    return validate_runtime_contract_proof(RuntimeContractProof(
        proof_id='ravenclaw-security-contract-proof',
        profile=profile,
        profile_conformance=validate_profile_conformance(profile),
        intent=intent,
        policy_constraints={'authorization': 'fixture_only', 'aggression': 'dry_run_only'},
        supervision_plan=GovSupervisionPlan(
            plan_id='ravenclaw-security-fixture-supervision',
            request_id=task.contract_id,
            runner_profile='dry_run_security_fixture',
            dry_run=True,
            live_backend_enabled=False,
        ),
        runtime_snapshot=GovRuntimeSnapshot(
            snapshot_id='ravenclaw-security-fixture-snapshot',
            run_id='ravenclaw-security-fixture-run',
            state='running_dry_run',
            control_actions=(
                GovControlAction(
                    action_id='ravenclaw-security-record-only',
                    run_id='ravenclaw-security-fixture-run',
                    action='record_only',
                    profile=profile.name,
                ),
            ),
            profile=profile.name,
            non_claims=('Snapshot is host-provided and storage-neutral.',),
        ),
        review_result=GovReviewResult(
            review_id='ravenclaw-security-fixture-review',
            subject_ref=intent.intent_id,
            verdict='passed',
            qualification_refs=('ravenclaw-security-fixture-qualification',),
        ),
        evidence_refs=('sclite:review_bundle:ravenclaw-security-fixture',),
        vocabulary=governance_contract_vocabulary(),
        metadata={'runtime_family': 'security_research', 'proof_scope': 'public_safe_fixture'},
    ))


def tecrax_contract_proof() -> RuntimeContractProof:
    profile = tecrax_infra_ops_profile()
    task = GovTaskContract(
        contract_id='tecrax-infra-fixture-task',
        task_family='dry_run_change',
        objective='Review an infrastructure change plan against a local fixture.',
        capability='dry_run_infra_change_review',
        target_ref='fixture:service:demo',
        target_kind='service',
        evidence_goal='fixture_receipt_required',
        constraints={'change_scope': 'local_fixture', 'aggression': 'dry_run_only'},
        metadata={'fixture': 'tecrax_infra_ops_profile'},
    )
    intent = GovPlanIntentContract(
        intent_id='tecrax-infra-fixture-intent',
        profile=profile.name,
        planner_id='fixture_profile_planner',
        goal='Demonstrate governed infrastructure-ops profile handoff without live infrastructure control.',
        task_contracts=(task,),
        non_claims=('Does not connect to infrastructure.',),
    )
    return validate_runtime_contract_proof(RuntimeContractProof(
        proof_id='tecrax-infra-contract-proof',
        profile=profile,
        profile_conformance=validate_profile_conformance(profile),
        intent=intent,
        policy_constraints={'authorization': 'fixture_only', 'change_scope': 'local_fixture'},
        supervision_plan=GovSupervisionPlan(
            plan_id='tecrax-infra-fixture-supervision',
            request_id=task.contract_id,
            runner_profile='local_fixture_only',
            dry_run=True,
            live_backend_enabled=False,
        ),
        runtime_snapshot=GovRuntimeSnapshot(
            snapshot_id='tecrax-infra-fixture-snapshot',
            run_id='tecrax-infra-fixture-run',
            state='running_dry_run',
            control_actions=(
                GovControlAction(
                    action_id='tecrax-infra-record-only',
                    run_id='tecrax-infra-fixture-run',
                    action='record_only',
                    profile=profile.name,
                ),
            ),
            profile=profile.name,
            non_claims=('Snapshot is host-provided and storage-neutral.',),
        ),
        review_result=GovReviewResult(
            review_id='tecrax-infra-fixture-review',
            subject_ref=intent.intent_id,
            verdict='passed',
            qualification_refs=('tecrax-infra-fixture-qualification',),
        ),
        change_order=ArtifactChangeOrder(
            required_actions=('operator_review_before_any_live_change',),
        ),
        evidence_refs=('sclite:review_bundle:tecrax-infra-fixture',),
        vocabulary=governance_contract_vocabulary(),
        metadata={'runtime_family': 'infra_ops', 'proof_scope': 'local_fixture_only'},
    ))


def _proof_from_mapping(value: Mapping[str, Any]) -> RuntimeContractProof:
    raw = require_mapping(value, reason_code='invalid_runtime_contract_proof')
    profile_raw = raw.get('profile')
    if isinstance(profile_raw, DomainProfile):
        profile = profile_raw
    elif isinstance(profile_raw, Mapping):
        from govengine.profiles import validate_domain_profile

        profile = validate_domain_profile(profile_raw)
    else:
        raise GovApiError('missing_contract_proof_profile')
    return RuntimeContractProof(
        proof_id=str(raw.get('proof_id') or raw.get('id') or '').strip(),
        profile=profile,
        profile_conformance=validate_profile_conformance(profile),
        intent=GovPlanIntentContract.from_mapping(
            require_mapping(raw.get('intent') or {}, reason_code='missing_contract_proof_intent')
        ),
        policy_constraints=_metadata(raw.get('policy_constraints')),
        supervision_plan=GovSupervisionPlan.from_mapping(
            require_mapping(raw.get('supervision_plan') or {}, reason_code='missing_contract_proof_supervision')
        ),
        runtime_snapshot=GovRuntimeSnapshot.from_mapping(
            require_mapping(raw.get('runtime_snapshot') or {}, reason_code='missing_contract_proof_runtime')
        ),
        review_result=GovReviewResult.from_mapping(
            require_mapping(raw.get('review_result') or {}, reason_code='missing_contract_proof_review')
        ),
        evidence_refs=_tuple(raw.get('evidence_refs') or ()),
        vocabulary=governance_contract_vocabulary(),
        metadata=_metadata(raw.get('metadata')),
    )


def _metadata(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    raw = require_mapping(value, reason_code='invalid_contract_proof_metadata')
    return {str(key): item for key, item in raw.items()}


def _tuple(values: Any) -> tuple[str, ...]:
    if isinstance(values, str):
        return (values,)
    try:
        return tuple(str(value) for value in values)
    except TypeError as exc:
        raise GovApiError('invalid_contract_proof_sequence') from exc


def _reject_forbidden_metadata(value: Mapping[str, Any]) -> None:
    lowered = {str(key).lower() for key in value.keys()}
    for forbidden in FORBIDDEN_PROOF_METADATA_KEYS:
        if forbidden in lowered:
            raise GovApiError(f'forbidden_contract_proof_metadata:{forbidden}')
