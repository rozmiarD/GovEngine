from __future__ import annotations

import importlib.resources

from govengine.conformance import (
    assert_conformance_outcome,
    iter_conformance_cases,
    load_conformance_manifest,
    run_govengine_conformance_case,
)


def test_language_neutral_conformance_corpus_passes_govengine_runner() -> None:
    cases = iter_conformance_cases()

    assert len(cases) == 41
    assert len({case['case_id'] for case in cases}) == len(cases)
    for case in cases:
        assert_conformance_outcome(
            case,
            run_govengine_conformance_case(case),
            runner='govengine',
        )


def test_conformance_corpus_manifest_and_cases_are_wheel_shipped() -> None:
    root = importlib.resources.files('govengine').joinpath('conformance', 'v1')
    manifest = load_conformance_manifest()

    assert manifest['case_count'] == 41
    assert len(manifest['cases']) == 41
    assert all(root.joinpath(relative).is_file() for relative in manifest['cases'])


def test_shared_negative_gap_cases_have_explicit_owner_and_reason_code() -> None:
    cases = {case['case_id']: case for case in iter_conformance_cases()}
    expected = {
        'non-ascii-binding': 'invalid_governance_identifier',
        'timezone-naive-timestamp': 'invalid_policy_activation_not_before',
        'approval-not-yet-valid': 'approval_not_yet_valid',
        'activation-superseded': 'policy_superseded',
        'activation-revoked': 'policy_revoked',
        'activation-expired': 'policy_expired',
        'signed-decision-body-tamper': 'governance_decision_digest_mismatch',
        'conflicting-policy-rules': 'conflicting_policy_rules',
    }

    for case_id, reason_code in expected.items():
        case = cases[case_id]
        assert case['owner'] == 'govengine'
        assert case['binding_digests'] == 'not_applicable'
        assert case['expected']['govengine'] == {
            'status': 'rejected',
            'reason_code': reason_code,
        }
