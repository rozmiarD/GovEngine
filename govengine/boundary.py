from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from govengine.api import GovApiError, require_mapping


KERNEL_OWNERSHIP = (
    'artifact_state_transitions',
    'controlled_execution_gates',
    'runner_request_receipt_envelopes',
    'policy_trust_boundary_decisions',
    'ooda_control_decisions',
    'sclite_lifecycle_bridge',
)

PROFILE_OWNERSHIP = (
    'domain_taxonomy',
    'domain_policy_meaning',
    'domain_tool_semantics',
    'domain_evidence_expectations',
    'operator_workflow_language',
)

RUNTIME_OWNERSHIP = (
    'operator_ui',
    'concrete_tool_execution',
    'state_storage',
    'credential_handling',
    'carrier_adapter_integration',
)

SCLITE_OWNERSHIP = (
    'schemas',
    'canonicalization',
    'artifact_chain_verification',
    'review_bundle_verdicts',
)

FORBIDDEN_PROFILE_OWNERSHIP = (
    'govengine_core_modules',
    'sclite_schema_authority',
    'live_execution_authority',
    'credential_or_key_store',
    'carrier_adapter_ownership',
)


@dataclass(frozen=True)
class KernelBoundary:
    """Stable ownership map for the GovEngine kernel/profile split."""

    kernel_owns: tuple[str, ...] = KERNEL_OWNERSHIP
    profile_owns: tuple[str, ...] = PROFILE_OWNERSHIP
    runtime_owns: tuple[str, ...] = RUNTIME_OWNERSHIP
    sclite_owns: tuple[str, ...] = SCLITE_OWNERSHIP
    forbidden_profile_ownership: tuple[str, ...] = FORBIDDEN_PROFILE_OWNERSHIP
    non_claims: tuple[str, ...] = (
        'GovEngine does not own domain product UX.',
        'GovEngine does not own SCLite schema/canonicalization authority.',
        'GovEngine does not authorize live execution or target testing.',
        'GovEngine does not own OpenClaw, MCP, or A2A carrier adapters.',
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            'kernel_owns': list(self.kernel_owns),
            'profile_owns': list(self.profile_owns),
            'runtime_owns': list(self.runtime_owns),
            'sclite_owns': list(self.sclite_owns),
            'forbidden_profile_ownership': list(self.forbidden_profile_ownership),
            'non_claims': list(self.non_claims),
        }


@dataclass(frozen=True)
class DomainProfileContract:
    """Host-supplied domain profile boundary contract.

    Profiles supply domain meaning. They may consume GovEngine mechanics, but
    they must not claim ownership over GovEngine core, SCLite authority, live
    execution authorization, credentials, or carrier adapters.
    """

    name: str
    version: str = 'v0.1'
    owner: str = ''
    owns: tuple[str, ...] = field(default_factory=tuple)
    consumes: tuple[str, ...] = field(default_factory=tuple)
    non_claims: tuple[str, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'DomainProfileContract':
        raw = require_mapping(value, reason_code='invalid_domain_profile_contract')
        name = str(raw.get('name') or '').strip()
        if not name:
            raise GovApiError('missing_domain_profile_name')
        owns = _tuple(raw.get('owns') or ())
        _reject_forbidden_ownership(owns)
        consumes = _tuple(raw.get('consumes') or ())
        non_claims = _tuple(raw.get('non_claims') or ())
        metadata = raw.get('metadata') if isinstance(raw.get('metadata'), Mapping) else {}
        return cls(
            name=name,
            version=str(raw.get('version') or 'v0.1'),
            owner=str(raw.get('owner') or ''),
            owns=owns,
            consumes=consumes,
            non_claims=non_claims,
            metadata=dict(metadata),
        )

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out['owns'] = list(self.owns)
        out['consumes'] = list(self.consumes)
        out['non_claims'] = list(self.non_claims)
        out['metadata'] = dict(self.metadata)
        return out

    def assert_boundary(self) -> None:
        _reject_forbidden_ownership(self.owns)


def kernel_boundary_contract() -> KernelBoundary:
    return KernelBoundary()


def ravenclaw_profile_contract() -> DomainProfileContract:
    return DomainProfileContract(
        name='ravenclaw',
        owner='host_runtime',
        owns=(
            'security_research_domain_profile',
            'campaign_runtime_semantics',
            'logdash_operator_ui',
            'public_demo_and_snapshot_workflow',
        ),
        consumes=(
            'govengine_controlled_execution_core',
            'govengine_security_profile_helpers',
            'sclite_review_bundles',
        ),
        non_claims=(
            'Does not make GovEngine own Ravenclaw campaign UX.',
            'Does not make GovEngine own Logdash.',
            'Does not move live target authorization into GovEngine.',
        ),
    )


def validate_domain_profile_contract(value: Mapping[str, Any] | DomainProfileContract) -> DomainProfileContract:
    contract = value if isinstance(value, DomainProfileContract) else DomainProfileContract.from_mapping(value)
    contract.assert_boundary()
    return contract


def _tuple(values: Any) -> tuple[str, ...]:
    if isinstance(values, str):
        return (values,)
    try:
        return tuple(str(value) for value in values)
    except TypeError as exc:
        raise GovApiError('invalid_domain_profile_sequence') from exc


def _reject_forbidden_ownership(owns: tuple[str, ...]) -> None:
    forbidden = set(FORBIDDEN_PROFILE_OWNERSHIP)
    claimed = forbidden.intersection(owns)
    if claimed:
        raise GovApiError(f'forbidden_domain_profile_ownership:{sorted(claimed)[0]}')
