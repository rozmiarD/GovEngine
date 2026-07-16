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

    assert len(cases) == 33
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

    assert manifest['case_count'] == 33
    assert len(manifest['cases']) == 33
    assert all(root.joinpath(relative).is_file() for relative in manifest['cases'])
