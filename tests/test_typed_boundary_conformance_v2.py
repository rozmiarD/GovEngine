from __future__ import annotations

from pathlib import Path

from govengine.conformance import (
    assert_conformance_outcome,
    iter_conformance_cases,
    load_conformance_manifest,
    run_govengine_conformance_case,
)


_V2_ROOT = Path(__file__).parent / 'conformance' / 'v2'


def test_additive_v2_negative_boundary_corpus_returns_stable_reason_codes() -> None:
    manifest = load_conformance_manifest(_V2_ROOT)
    cases = iter_conformance_cases(_V2_ROOT)

    assert manifest['corpus_version'] == 'v2-additive'
    assert manifest['case_count'] == 5
    assert len(cases) == 5
    assert any('wheel-shipped v1 corpus' in claim for claim in manifest['non_claims'])

    for case in cases:
        outcome = run_govengine_conformance_case(case)
        assert_conformance_outcome(case, outcome, runner='govengine')
        assert outcome.status == 'rejected'
