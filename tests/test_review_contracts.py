from __future__ import annotations

import pytest

from govengine import (
    GovEvidenceClaim,
    GovEvidenceRequirement,
    GovReviewResult,
    qualify_evidence_claim,
    validate_evidence_claim,
    validate_evidence_requirement,
    validate_review_result,
)
from govengine.api import GovApiError


def test_evidence_claim_qualifies_against_receipt_bounds() -> None:
    requirement = validate_evidence_requirement({
        'requirement_id': 'req-1',
        'subject_ref': 'sha256:subject',
        'min_receipt_status': 'dry-run',
    })
    claim = validate_evidence_claim({
        'claim_id': 'claim-1',
        'subject_ref': 'sha256:subject',
        'claim_type': 'execution_truth',
        'receipt_refs': ['receipt-1'],
        'evidence_refs': ['evidence-1'],
    })
    qualification = qualify_evidence_claim(claim, requirement, receipt_status='dry-run')

    assert isinstance(requirement, GovEvidenceRequirement)
    assert isinstance(claim, GovEvidenceClaim)
    assert qualification.result == 'supported'
    assert qualification.reason_code == 'receipt_bounds_support_claim'


def test_live_claim_is_rejected_when_receipt_is_only_dry_run() -> None:
    qualification = qualify_evidence_claim(
        {
            'claim_id': 'claim-live',
            'subject_ref': 'sha256:subject',
            'claim_type': 'live_vulnerability',
            'receipt_refs': ['receipt-1'],
        },
        {
            'requirement_id': 'req-live',
            'subject_ref': 'sha256:subject',
            'min_receipt_status': 'dry-run',
        },
        receipt_status='dry-run',
    )

    assert qualification.result == 'rejected'
    assert qualification.reason_code == 'live_claim_not_supported_by_receipt'


def test_evidence_claim_requires_receipt_refs_and_rejects_raw_output_metadata() -> None:
    with pytest.raises(GovApiError, match='missing_evidence_claim_receipt_ref'):
        validate_evidence_claim({'claim_id': 'claim-1', 'subject_ref': 'sha256:subject'})

    for key in ('target', 'stdout', 'stderr', 'prompt', 'command'):
        with pytest.raises(GovApiError, match=f'forbidden_review_metadata:{key}'):
            validate_evidence_claim({
                'claim_id': f'claim-{key}',
                'subject_ref': 'sha256:subject',
                'receipt_refs': ['receipt-1'],
                'metadata': {key: 'not allowed'},
            })


def test_review_result_is_shape_only() -> None:
    review = validate_review_result({
        'review_id': 'review-1',
        'subject_ref': 'sha256:subject',
        'verdict': 'needs_review',
        'qualification_refs': ['claim-1:qualification'],
        'metadata': {'source': 'host_review'},
    })

    assert isinstance(review, GovReviewResult)
    assert review.as_dict()['qualification_refs'] == ['claim-1:qualification']
