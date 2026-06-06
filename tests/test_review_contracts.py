from __future__ import annotations

import pytest

from govengine import (
    GovEvidenceClaim,
    GovEvidenceRequirement,
    GovReviewResult,
    qualify_evidence_claim,
    validate_evidence_claim,
    validate_evidence_requirement,
    validate_evidence_review_chain,
    validate_review_result,
)
from govengine.api import GovApiError


ADMISSION_DIGEST = 'sha256:' + 'a' * 64
RECEIPT_DIGEST = 'sha256:' + 'b' * 64


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


def test_evidence_review_chain_validates_admission_receipt_and_review_refs() -> None:
    qualification = validate_evidence_review_chain(
        {
            'claim_id': 'claim-chain',
            'subject_ref': ADMISSION_DIGEST,
            'claim_type': 'execution_truth',
            'receipt_refs': ['receipt-1'],
            'evidence_refs': ['evidence-1'],
            'metadata': {
                'admission_id': 'admission-1',
                'admission_digest': ADMISSION_DIGEST,
                'receipt_digest': RECEIPT_DIGEST,
            },
        },
        {
            'requirement_id': 'req-chain',
            'subject_ref': ADMISSION_DIGEST,
            'min_receipt_status': 'dry-run',
        },
        receipt_id='receipt-1',
        receipt_digest=RECEIPT_DIGEST,
        receipt_status='dry-run',
        admission_id='admission-1',
        admission_digest=ADMISSION_DIGEST,
        review={
            'review_id': 'review-chain',
            'subject_ref': ADMISSION_DIGEST,
            'verdict': 'passed',
            'qualification_refs': ['claim-chain:qualification'],
        },
    )

    assert qualification.result == 'supported'
    assert qualification.reason_code == 'receipt_bounds_support_claim'


def test_evidence_review_chain_rejects_missing_or_wrong_receipt_ref() -> None:
    requirement = {'requirement_id': 'req-chain', 'subject_ref': ADMISSION_DIGEST}

    with pytest.raises(GovApiError, match='missing_evidence_claim_receipt_ref'):
        validate_evidence_review_chain(
            {'claim_id': 'claim-no-receipt', 'subject_ref': ADMISSION_DIGEST},
            requirement,
            receipt_id='receipt-1',
            receipt_status='dry-run',
        )

    with pytest.raises(GovApiError, match='evidence_receipt_ref_mismatch'):
        validate_evidence_review_chain(
            {
                'claim_id': 'claim-wrong-receipt',
                'subject_ref': ADMISSION_DIGEST,
                'receipt_refs': ['other-receipt'],
            },
            requirement,
            receipt_id='receipt-1',
            receipt_status='dry-run',
        )


def test_evidence_review_chain_rejects_wrong_admission_or_receipt_digest() -> None:
    claim = {
        'claim_id': 'claim-chain',
        'subject_ref': ADMISSION_DIGEST,
        'receipt_refs': ['receipt-1'],
        'metadata': {'admission_digest': ADMISSION_DIGEST, 'receipt_digest': RECEIPT_DIGEST},
    }
    requirement = {'requirement_id': 'req-chain', 'subject_ref': ADMISSION_DIGEST}

    with pytest.raises(GovApiError, match='evidence_admission_ref_mismatch'):
        validate_evidence_review_chain(
            claim,
            requirement,
            receipt_id='receipt-1',
            receipt_status='dry-run',
            admission_digest='sha256:' + 'c' * 64,
        )

    with pytest.raises(GovApiError, match='evidence_receipt_digest_mismatch'):
        validate_evidence_review_chain(
            claim,
            requirement,
            receipt_id='receipt-1',
            receipt_digest='sha256:' + 'd' * 64,
            receipt_status='dry-run',
        )


def test_evidence_review_chain_rejects_overclaim_and_review_ref_mismatch() -> None:
    live_claim = {
        'claim_id': 'claim-live',
        'subject_ref': ADMISSION_DIGEST,
        'claim_type': 'live_vulnerability',
        'receipt_refs': ['receipt-1'],
    }
    requirement = {'requirement_id': 'req-chain', 'subject_ref': ADMISSION_DIGEST}

    with pytest.raises(GovApiError, match='evidence_claim_not_supported:live_claim_not_supported_by_receipt'):
        validate_evidence_review_chain(
            live_claim,
            requirement,
            receipt_id='receipt-1',
            receipt_status='dry-run',
        )

    with pytest.raises(GovApiError, match='review_result_qualification_ref_mismatch'):
        validate_evidence_review_chain(
            {
                'claim_id': 'claim-chain',
                'subject_ref': ADMISSION_DIGEST,
                'receipt_refs': ['receipt-1'],
            },
            requirement,
            receipt_id='receipt-1',
            receipt_status='dry-run',
            review={
                'review_id': 'review-chain',
                'subject_ref': ADMISSION_DIGEST,
                'qualification_refs': ['other-qualification'],
            },
        )
