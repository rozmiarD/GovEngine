from __future__ import annotations

from typing import Mapping, Any

from govengine.api import GovApiError
from govengine.core import ArtifactDescriptor
from govengine.governance_decision import (
    GovernanceDecision,
    validate_governance_decision,
)
from govengine.signing import (
    SignedArtifact,
    SignerPort,
    SigningPolicy,
    SigningRequest,
    TrustPolicy,
    VerifierPort,
    govengine_record_digest,
    signed_artifact_from_record,
    verify_signed_govengine_record,
)


SIGNED_GOVERNANCE_DECISION_RECORD_TYPE = (
    'govengine.governance_decision_signing.SignedGovernanceDecisionRecord'
)
SIGNED_GOVERNANCE_DECISION_PURPOSE = 'governance_decision_authority'


def sign_governance_decision(
    decision: GovernanceDecision,
    *,
    signer: SignerPort,
    payload_ref: str,
) -> SignedArtifact:
    """Sign the complete validated decision through a host-owned signer."""

    checked = validate_governance_decision(decision)
    resolved_payload_ref = str(payload_ref or '').strip()
    if not resolved_payload_ref:
        raise GovApiError('governance_decision_signature_payload_ref_required')
    record = checked.as_dict()
    record_digest = govengine_record_digest(
        record,
        record_type=SIGNED_GOVERNANCE_DECISION_RECORD_TYPE,
        schema_version=checked.schema_version,
    )
    descriptor = ArtifactDescriptor(
        'govengine_record',
        checked.schema_version,
        record_digest,
        role=SIGNED_GOVERNANCE_DECISION_RECORD_TYPE,
        path=resolved_payload_ref,
    )
    result = signer.sign(
        SigningRequest(
            descriptor=descriptor,
            purpose=SIGNED_GOVERNANCE_DECISION_PURPOSE,
            metadata={
                'record_type': SIGNED_GOVERNANCE_DECISION_RECORD_TYPE,
                'decision_digest': checked.decision_digest,
            },
        )
    )
    if result.status not in {'ok', 'passed', 'signed'}:
        raise GovApiError('governance_decision_signing_failed')
    return signed_artifact_from_record(
        record,
        record_type=SIGNED_GOVERNANCE_DECISION_RECORD_TYPE,
        payload_ref=resolved_payload_ref,
        signature=result.signature,
        schema_version=checked.schema_version,
        metadata={
            'purpose': SIGNED_GOVERNANCE_DECISION_PURPOSE,
            'decision_digest': checked.decision_digest,
            'transaction_id': checked.transaction_id,
        },
    )


def require_trusted_governance_decision(
    decision: GovernanceDecision,
    signed_artifact: SignedArtifact | Mapping[str, Any],
    *,
    verifier: VerifierPort,
    signing_policy: SigningPolicy,
    trust_policy: TrustPolicy,
) -> GovernanceDecision:
    """Return the decision only after signed-record and trust verification."""

    checked = validate_governance_decision(decision)
    artifact = (
        signed_artifact
        if isinstance(signed_artifact, SignedArtifact)
        else SignedArtifact.from_mapping(signed_artifact)
    )
    if artifact.record_type != SIGNED_GOVERNANCE_DECISION_RECORD_TYPE:
        raise GovApiError('governance_decision_signature_record_type_mismatch')
    if artifact.schema_version != checked.schema_version:
        raise GovApiError('governance_decision_signature_schema_mismatch')
    if artifact.metadata.get('purpose') != SIGNED_GOVERNANCE_DECISION_PURPOSE:
        raise GovApiError('governance_decision_signature_purpose_mismatch')
    if artifact.metadata.get('decision_digest') != checked.decision_digest:
        raise GovApiError('governance_decision_signature_decision_digest_mismatch')
    signature = artifact.signature
    if signing_policy.require_signature and not signature.signed:
        raise GovApiError('governance_decision_signature_required')
    if signature.mode not in signing_policy.allowed_modes:
        raise GovApiError('governance_decision_signature_mode_not_allowed')
    if (
        signing_policy.required_signer_ids
        and signature.signer_id not in signing_policy.required_signer_ids
    ):
        raise GovApiError('governance_decision_signer_not_allowed')
    verification = verify_signed_govengine_record(
        checked.as_dict(),
        artifact,
        verifier=verifier,
    )
    if not verification.trusted:
        raise GovApiError('governance_decision_signature_verification_failed')
    if verification.trust_status not in trust_policy.allowed_trust_statuses:
        raise GovApiError('governance_decision_signature_trust_denied')
    return checked
