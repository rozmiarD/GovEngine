from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hmac import compare_digest
from typing import Any, Mapping

from govengine.api import GovApiError, require_mapping


REVIEW_VERDICTS = ('passed', 'failed', 'needs_review')
QUALIFICATION_RESULTS = ('supported', 'unsupported', 'needs_review', 'rejected')
RECEIPT_STATUSES = ('succeeded', 'dry-run', 'blocked', 'failed', 'interrupted')

FORBIDDEN_REVIEW_METADATA_KEYS = (
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
    'stdout',
    'stderr',
    'raw_output',
    'shell',
    'subprocess',
    'live_backend',
    'runtime_storage',
    'storage_path',
    'carrier_payload',
    'transport_payload',
    'target',
    'target_url',
    'url',
)


@dataclass(frozen=True)
class GovEvidenceRequirement:
    requirement_id: str
    subject_ref: str
    evidence_kind: str = 'execution_receipt'
    min_receipt_status: str = 'dry-run'
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'GovEvidenceRequirement':
        raw = require_mapping(value, reason_code='invalid_evidence_requirement')
        requirement_id = str(raw.get('requirement_id') or raw.get('id') or '').strip()
        if not requirement_id:
            raise GovApiError('missing_evidence_requirement_id')
        subject_ref = str(raw.get('subject_ref') or '').strip()
        if not subject_ref:
            raise GovApiError('missing_evidence_requirement_subject_ref')
        item = cls(
            requirement_id=requirement_id,
            subject_ref=subject_ref,
            evidence_kind=str(raw.get('evidence_kind') or 'execution_receipt').strip() or 'execution_receipt',
            min_receipt_status=_enum(raw.get('min_receipt_status'), RECEIPT_STATUSES, 'dry-run'),
            metadata=_metadata(raw.get('metadata')),
        )
        validate_evidence_requirement(item)
        return item

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out['metadata'] = dict(self.metadata)
        return out


@dataclass(frozen=True)
class GovEvidenceClaim:
    claim_id: str
    subject_ref: str
    claim_type: str = 'execution_truth'
    statement: str = ''
    receipt_refs: tuple[str, ...] = field(default_factory=tuple)
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'GovEvidenceClaim':
        raw = require_mapping(value, reason_code='invalid_evidence_claim')
        claim_id = str(raw.get('claim_id') or raw.get('id') or '').strip()
        if not claim_id:
            raise GovApiError('missing_evidence_claim_id')
        subject_ref = str(raw.get('subject_ref') or '').strip()
        if not subject_ref:
            raise GovApiError('missing_evidence_claim_subject_ref')
        item = cls(
            claim_id=claim_id,
            subject_ref=subject_ref,
            claim_type=str(raw.get('claim_type') or 'execution_truth').strip() or 'execution_truth',
            statement=str(raw.get('statement') or '').strip(),
            receipt_refs=_tuple(raw.get('receipt_refs') or ()),
            evidence_refs=_tuple(raw.get('evidence_refs') or ()),
            metadata=_metadata(raw.get('metadata')),
        )
        validate_evidence_claim(item)
        return item

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out['receipt_refs'] = list(self.receipt_refs)
        out['evidence_refs'] = list(self.evidence_refs)
        out['metadata'] = dict(self.metadata)
        return out


@dataclass(frozen=True)
class GovEvidenceQualification:
    qualification_id: str
    claim_id: str
    requirement_id: str
    result: str = 'needs_review'
    reason_code: str = 'needs_review'
    receipt_status: str = 'dry-run'
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'GovEvidenceQualification':
        raw = require_mapping(value, reason_code='invalid_evidence_qualification')
        qualification_id = str(raw.get('qualification_id') or raw.get('id') or '').strip()
        if not qualification_id:
            raise GovApiError('missing_evidence_qualification_id')
        item = cls(
            qualification_id=qualification_id,
            claim_id=str(raw.get('claim_id') or '').strip(),
            requirement_id=str(raw.get('requirement_id') or '').strip(),
            result=_enum(raw.get('result'), QUALIFICATION_RESULTS, 'needs_review'),
            reason_code=str(raw.get('reason_code') or 'needs_review').strip() or 'needs_review',
            receipt_status=_enum(raw.get('receipt_status'), RECEIPT_STATUSES, 'dry-run'),
            metadata=_metadata(raw.get('metadata')),
        )
        validate_evidence_qualification(item)
        return item

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out['metadata'] = dict(self.metadata)
        return out


@dataclass(frozen=True)
class GovReviewResult:
    review_id: str
    subject_ref: str
    verdict: str = 'needs_review'
    qualification_refs: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'GovReviewResult':
        raw = require_mapping(value, reason_code='invalid_review_result')
        review_id = str(raw.get('review_id') or raw.get('id') or '').strip()
        if not review_id:
            raise GovApiError('missing_review_result_id')
        subject_ref = str(raw.get('subject_ref') or '').strip()
        if not subject_ref:
            raise GovApiError('missing_review_subject_ref')
        item = cls(
            review_id=review_id,
            subject_ref=subject_ref,
            verdict=_enum(raw.get('verdict'), REVIEW_VERDICTS, 'needs_review'),
            qualification_refs=_tuple(raw.get('qualification_refs') or ()),
            metadata=_metadata(raw.get('metadata')),
        )
        validate_review_result(item)
        return item

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out['qualification_refs'] = list(self.qualification_refs)
        out['metadata'] = dict(self.metadata)
        return out


def validate_evidence_requirement(value: Mapping[str, Any] | GovEvidenceRequirement) -> GovEvidenceRequirement:
    item = value if isinstance(value, GovEvidenceRequirement) else GovEvidenceRequirement.from_mapping(value)
    _reject_forbidden_metadata(item.metadata)
    return item


def validate_evidence_claim(value: Mapping[str, Any] | GovEvidenceClaim) -> GovEvidenceClaim:
    item = value if isinstance(value, GovEvidenceClaim) else GovEvidenceClaim.from_mapping(value)
    if not item.receipt_refs:
        raise GovApiError('missing_evidence_claim_receipt_ref')
    _reject_forbidden_metadata(item.metadata)
    return item


def validate_evidence_qualification(value: Mapping[str, Any] | GovEvidenceQualification) -> GovEvidenceQualification:
    item = value if isinstance(value, GovEvidenceQualification) else GovEvidenceQualification.from_mapping(value)
    if not item.claim_id:
        raise GovApiError('missing_evidence_qualification_claim_id')
    if not item.requirement_id:
        raise GovApiError('missing_evidence_qualification_requirement_id')
    _reject_forbidden_metadata(item.metadata)
    return item


def validate_review_result(value: Mapping[str, Any] | GovReviewResult) -> GovReviewResult:
    item = value if isinstance(value, GovReviewResult) else GovReviewResult.from_mapping(value)
    _reject_forbidden_metadata(item.metadata)
    return item


def qualify_evidence_claim(
    claim: GovEvidenceClaim | Mapping[str, Any],
    requirement: GovEvidenceRequirement | Mapping[str, Any],
    *,
    receipt_status: str,
    qualification_id: str = '',
) -> GovEvidenceQualification:
    checked_claim = validate_evidence_claim(claim)
    checked_requirement = validate_evidence_requirement(requirement)
    status = _enum(receipt_status, RECEIPT_STATUSES, 'dry-run')
    if not _claim_supports_evidence_kind(checked_claim, checked_requirement.evidence_kind):
        result = 'unsupported'
        reason = 'evidence_kind_mismatch'
    elif _receipt_rank(status) < _receipt_rank(checked_requirement.min_receipt_status):
        result = 'unsupported'
        reason = 'receipt_status_below_requirement'
    elif checked_claim.claim_type == 'live_vulnerability' and status != 'succeeded':
        result = 'rejected'
        reason = 'live_claim_not_supported_by_receipt'
    else:
        result = 'supported'
        reason = 'receipt_bounds_support_claim'
    return validate_evidence_qualification(GovEvidenceQualification(
        qualification_id=qualification_id or f'{checked_claim.claim_id}:qualification',
        claim_id=checked_claim.claim_id,
        requirement_id=checked_requirement.requirement_id,
        result=result,
        reason_code=reason,
        receipt_status=status,
        metadata={'source': 'govengine_review_qualification'},
    ))


def validate_evidence_review_chain(
    claim: GovEvidenceClaim | Mapping[str, Any],
    requirement: GovEvidenceRequirement | Mapping[str, Any],
    *,
    receipt_id: str,
    receipt_status: str,
    admission_id: str = '',
    admission_digest: str = '',
    receipt_digest: str = '',
    qualification: GovEvidenceQualification | Mapping[str, Any] | None = None,
    review: GovReviewResult | Mapping[str, Any] | None = None,
) -> GovEvidenceQualification:
    """Verify the bounded admission -> receipt -> evidence -> review chain.

    This helper checks neutral references only. It does not store raw evidence,
    evaluate SCLite review bundles, or turn a receipt into execution authority.
    """

    checked_claim = validate_evidence_claim(claim)
    checked_requirement = validate_evidence_requirement(requirement)
    expected_receipt_id = str(receipt_id or '').strip()
    if not expected_receipt_id:
        raise GovApiError('missing_evidence_review_receipt_id')
    if expected_receipt_id not in checked_claim.receipt_refs:
        raise GovApiError('evidence_receipt_ref_mismatch')
    if checked_claim.subject_ref != checked_requirement.subject_ref:
        raise GovApiError('evidence_subject_ref_mismatch')
    if not _claim_matches_admission(checked_claim, admission_id=admission_id, admission_digest=admission_digest):
        raise GovApiError('evidence_admission_ref_mismatch')
    expected_receipt_digest = str(receipt_digest or '').strip()
    if expected_receipt_digest:
        claim_receipt_digest = str(checked_claim.metadata.get('receipt_digest') or '').strip()
        if not compare_digest(claim_receipt_digest, expected_receipt_digest):
            raise GovApiError('evidence_receipt_digest_mismatch')

    qualified = (
        validate_evidence_qualification(qualification)
        if qualification is not None
        else qualify_evidence_claim(checked_claim, checked_requirement, receipt_status=receipt_status)
    )
    if qualified.claim_id != checked_claim.claim_id:
        raise GovApiError('evidence_qualification_claim_mismatch')
    if qualified.requirement_id != checked_requirement.requirement_id:
        raise GovApiError('evidence_qualification_requirement_mismatch')
    if qualified.receipt_status != _enum(receipt_status, RECEIPT_STATUSES, 'dry-run'):
        raise GovApiError('evidence_qualification_receipt_status_mismatch')
    if qualified.result != 'supported':
        raise GovApiError(f'evidence_claim_not_supported:{qualified.reason_code}')

    if review is not None:
        checked_review = validate_review_result(review)
        if checked_review.subject_ref != checked_requirement.subject_ref:
            raise GovApiError('review_result_subject_ref_mismatch')
        if qualified.qualification_id not in checked_review.qualification_refs:
            raise GovApiError('review_result_qualification_ref_mismatch')
    return qualified


def evidence_claim_public_summary(value: GovEvidenceClaim | Mapping[str, Any]) -> dict[str, Any]:
    """Return a public-safe evidence claim summary without raw evidence."""

    item = validate_evidence_claim(value)
    return {
        'claim_id': item.claim_id,
        'subject_ref': item.subject_ref,
        'claim_type': item.claim_type,
        'receipt_ref_count': len(item.receipt_refs),
        'evidence_ref_count': len(item.evidence_refs),
    }


def review_result_public_summary(value: GovReviewResult | Mapping[str, Any]) -> dict[str, Any]:
    """Return a public-safe review result summary without raw review payloads."""

    item = validate_review_result(value)
    return {
        'review_id': item.review_id,
        'subject_ref': item.subject_ref,
        'verdict': item.verdict,
        'qualification_ref_count': len(item.qualification_refs),
    }


def _receipt_rank(status: str) -> int:
    return {
        'blocked': 0,
        'failed': 1,
        'interrupted': 1,
        'dry-run': 2,
        'succeeded': 3,
    }.get(status, 0)


def _claim_matches_admission(
    claim: GovEvidenceClaim,
    *,
    admission_id: str,
    admission_digest: str,
) -> bool:
    expected = {str(value or '').strip() for value in (admission_id, admission_digest) if str(value or '').strip()}
    if not expected:
        return True
    observed = {
        claim.subject_ref,
        str(claim.metadata.get('admission_id') or '').strip(),
        str(claim.metadata.get('admission_digest') or '').strip(),
    }
    return bool(expected & observed)


def _claim_supports_evidence_kind(claim: GovEvidenceClaim, required_kind: str) -> bool:
    kind = str(required_kind or 'execution_receipt').strip().lower() or 'execution_receipt'
    if kind == 'execution_receipt':
        return bool(claim.receipt_refs)
    observed = {str(claim.claim_type or '').strip().lower()}
    metadata_kind = claim.metadata.get('evidence_kind')
    if isinstance(metadata_kind, str):
        observed.add(metadata_kind.strip().lower())
    metadata_kinds = claim.metadata.get('evidence_kinds')
    if isinstance(metadata_kinds, str):
        observed.add(metadata_kinds.strip().lower())
    elif isinstance(metadata_kinds, (list, tuple, set)):
        observed.update(str(value).strip().lower() for value in metadata_kinds)
    return kind in observed


def _enum(value: Any, allowed: tuple[str, ...], default: str) -> str:
    normalized = str(value or '').strip().lower() or default
    return normalized if normalized in allowed else default


def _tuple(values: Any) -> tuple[str, ...]:
    if isinstance(values, str):
        return (values,)
    try:
        return tuple(str(value) for value in values)
    except TypeError as exc:
        raise GovApiError('invalid_review_sequence') from exc


def _metadata(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise GovApiError('invalid_review_metadata')
    data = dict(value)
    _reject_forbidden_metadata(data)
    return data


def _reject_forbidden_metadata(value: Mapping[str, Any]) -> None:
    reason = _find_forbidden_key(value)
    if reason:
        raise GovApiError(f'forbidden_review_metadata:{reason}')


def _find_forbidden_key(value: Any) -> str:
    if isinstance(value, Mapping):
        forbidden = set(FORBIDDEN_REVIEW_METADATA_KEYS)
        for key, item in value.items():
            normalized = str(key).lower()
            if normalized in forbidden:
                return normalized
            nested = _find_forbidden_key(item)
            if nested:
                return nested
    elif isinstance(value, (list, tuple)):
        for item in value:
            nested = _find_forbidden_key(item)
            if nested:
                return nested
    return ''
