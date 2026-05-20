from __future__ import annotations

from dataclasses import asdict, dataclass, field
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
    if _receipt_rank(status) < _receipt_rank(checked_requirement.min_receipt_status):
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


def _receipt_rank(status: str) -> int:
    return {
        'blocked': 0,
        'failed': 1,
        'interrupted': 1,
        'dry-run': 2,
        'succeeded': 3,
    }.get(status, 0)


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
