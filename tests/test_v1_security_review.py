from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_v1_security_review import validate_v1_security_review


def test_v1_security_review_record_is_structurally_valid_and_pending() -> None:
    report = validate_v1_security_review()

    assert report == {
        'status': 'pending_independent_review',
        'independent': False,
        'findings': 0,
        'open_p0': 0,
        'open_p1': 0,
    }


def test_release_gate_requires_real_independent_review() -> None:
    with pytest.raises(
        AssertionError,
        match='independent_v1_security_review_required',
    ):
        validate_v1_security_review(require_independent=True)


def test_completed_independent_review_passes_release_gate(tmp_path: Path) -> None:
    review = {
        'schema_version': 'govengine.v1_contract_security_review.v1',
        'status': 'independent_reviewed',
        'reviewer': {
            'identity': 'reviewer@example.invalid',
            'organization_or_reference': 'external-review-2026-07',
            'independent_of_implementation': True,
        },
        'reviewed_commit': 'a' * 40,
        'completed_at': '2026-07-16T12:00:00Z',
        'scope': [f'scope-{index}' for index in range(9)],
        'findings': [
            {
                'finding_id': 'GE-REVIEW-001',
                'severity': 'p2',
                'summary': 'Non-blocking hardening recommendation.',
                'disposition': 'accepted_non_blocking',
            }
        ],
        'open_p0': 0,
        'open_p1': 0,
        'notes': 'Independent review completed.',
    }
    path = tmp_path / 'review.json'
    path.write_text(json.dumps(review), encoding='utf-8')

    report = validate_v1_security_review(path, require_independent=True)

    assert report == {
        'status': 'independent_reviewed',
        'independent': True,
        'findings': 1,
        'open_p0': 0,
        'open_p1': 0,
    }


def test_duplicate_finding_ids_are_rejected(tmp_path: Path) -> None:
    review = json.loads(
        Path('docs/security-review/v1-contract-review.json').read_text(
            encoding='utf-8'
        )
    )
    finding = {
        'finding_id': 'GE-REVIEW-001',
        'severity': 'p2',
        'summary': 'Example.',
        'disposition': 'fixed',
    }
    review['findings'] = [finding, finding]
    path = tmp_path / 'review.json'
    path.write_text(json.dumps(review), encoding='utf-8')

    with pytest.raises(
        AssertionError,
        match='security_review_finding_id_invalid',
    ):
        validate_v1_security_review(path)
