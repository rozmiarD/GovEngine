from __future__ import annotations

import pytest

from govengine import (
    GovernanceVocabularyEntry,
    RuntimeContractProof,
    governance_contract_vocabulary,
    ravenclaw_contract_proof,
    tecrax_contract_proof,
    validate_governance_contract_vocabulary,
    validate_runtime_contract_proof,
)
from govengine.api import GovApiError
from govengine.execution.supervision import GovSupervisionPlan


def test_governance_contract_vocabulary_is_neutral_and_complete() -> None:
    vocabulary = validate_governance_contract_vocabulary()

    assert [entry.term for entry in vocabulary] == [
        'objective',
        'policy_constraints',
        'task_plan',
        'runner_bounds',
        'runtime_snapshot',
        'review_result',
        'change_order',
    ]
    joined = ' '.join(repr(entry.as_dict()) for entry in vocabulary)
    assert 'Command' not in joined
    assert 'SITREP' not in joined
    assert 'FRAGO' not in joined
    assert 'OODA' not in ' '.join(entry.term for entry in vocabulary)


@pytest.mark.parametrize('proof_factory,profile_name', [
    (ravenclaw_contract_proof, 'ravenclaw-security'),
    (tecrax_contract_proof, 'tecrax-infra-ops'),
])
def test_runtime_contract_proofs_are_public_safe_and_conformant(proof_factory, profile_name: str) -> None:
    proof = proof_factory()
    payload = proof.as_dict()

    assert isinstance(proof, RuntimeContractProof)
    assert proof.profile.name == profile_name
    assert proof.profile_conformance.status == 'passed'
    assert proof.supervision_plan.dry_run is True
    assert proof.supervision_plan.live_backend_enabled is False
    assert proof.runtime_snapshot.profile == profile_name
    assert proof.review_result.verdict == 'passed'
    assert proof.evidence_refs
    assert 'Proof does not implement carrier adapters.' in payload['non_claims']
    assert 'Proof does not add a new OODA surface.' in payload['non_claims']


def test_runtime_contract_proof_rejects_live_execution_claims() -> None:
    proof = ravenclaw_contract_proof()
    bad = RuntimeContractProof(
        proof_id='bad-live-proof',
        profile=proof.profile,
        profile_conformance=proof.profile_conformance,
        intent=proof.intent,
        policy_constraints=proof.policy_constraints,
        supervision_plan=GovSupervisionPlan(
            plan_id='bad-live-supervision',
            request_id=proof.supervision_plan.request_id,
            runner_profile='live',
            dry_run=False,
            live_backend_enabled=True,
        ),
        runtime_snapshot=proof.runtime_snapshot,
        review_result=proof.review_result,
        evidence_refs=proof.evidence_refs,
        vocabulary=proof.vocabulary,
    )

    with pytest.raises(GovApiError, match='proof_live_execution_not_allowed'):
        validate_runtime_contract_proof(bad)


def test_runtime_contract_proof_rejects_profile_mismatch() -> None:
    proof = ravenclaw_contract_proof()
    bad = RuntimeContractProof(
        proof_id='bad-profile-proof',
        profile=tecrax_contract_proof().profile,
        profile_conformance=proof.profile_conformance,
        intent=proof.intent,
        policy_constraints=proof.policy_constraints,
        supervision_plan=proof.supervision_plan,
        runtime_snapshot=proof.runtime_snapshot,
        review_result=proof.review_result,
        evidence_refs=proof.evidence_refs,
        vocabulary=proof.vocabulary,
    )

    with pytest.raises(GovApiError, match='proof_profile_intent_mismatch'):
        validate_runtime_contract_proof(bad)


def test_runtime_contract_proof_rejects_forbidden_metadata() -> None:
    proof = ravenclaw_contract_proof()
    bad = RuntimeContractProof(
        proof_id='bad-metadata-proof',
        profile=proof.profile,
        profile_conformance=proof.profile_conformance,
        intent=proof.intent,
        policy_constraints={'credential': 'not-allowed'},
        supervision_plan=proof.supervision_plan,
        runtime_snapshot=proof.runtime_snapshot,
        review_result=proof.review_result,
        evidence_refs=proof.evidence_refs,
        vocabulary=proof.vocabulary,
    )

    with pytest.raises(GovApiError, match='forbidden_contract_proof_metadata:credential'):
        validate_runtime_contract_proof(bad)


def test_governance_contract_vocabulary_rejects_new_terms() -> None:
    bad = governance_contract_vocabulary() + (
        GovernanceVocabularyEntry(
            term='extra_term',
            govengine_contract='Nope',
            surface='planning_contracts_core',
            contract_role='invalid',
        ),
    )

    with pytest.raises(GovApiError, match='invalid_governance_contract_vocabulary'):
        validate_governance_contract_vocabulary(bad)
