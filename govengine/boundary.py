from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from govengine.api import GovApiError, require_mapping
from govengine.surfaces import public_surface_index


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
    'pki_or_kms_ownership',
    'product_ux_ownership',
)

ALLOWED_PROFILE_CONSUMES = (
    'govengine_artifact_governance_core',
    'govengine_planning_contracts_core',
    'govengine_admission_policy_core',
    'govengine_evidence_review_core',
    'govengine_domain_profile_sdk',
    'govengine_controlled_execution_core',
    'govengine_security_profile_helpers',
    'sclite_lifecycle_artifacts',
    'sclite_review_bundles',
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


@dataclass(frozen=True)
class DomainProfileConformance:
    """Deterministic conformance report for one domain profile contract."""

    profile: DomainProfileContract
    status: str
    allowed_consumes: tuple[str, ...] = ALLOWED_PROFILE_CONSUMES
    unknown_consumes: tuple[str, ...] = ()
    forbidden_ownership: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.status == 'passed'

    def as_dict(self) -> dict[str, Any]:
        return {
            'profile': self.profile.as_dict(),
            'status': self.status,
            'passed': self.passed,
            'allowed_consumes': list(self.allowed_consumes),
            'unknown_consumes': list(self.unknown_consumes),
            'forbidden_ownership': list(self.forbidden_ownership),
            'checks': {
                'no_forbidden_ownership': not self.forbidden_ownership,
                'consumes_are_known': not self.unknown_consumes,
            },
            'non_claims': [
                'Conformance does not grant live execution authority.',
                'Conformance does not make GovEngine own profile domain semantics.',
            ],
        }


@dataclass(frozen=True)
class BoundaryReport:
    """Machine-readable GovEngine 0.2 boundary snapshot."""

    boundary: KernelBoundary
    profiles: tuple[DomainProfileContract, ...] = field(default_factory=tuple)
    profile_conformance: tuple[DomainProfileConformance, ...] = field(default_factory=tuple)
    surfaces: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    status: str = 'alpha_boundary_declared'
    schema_version: str = 'v0.1'

    def as_dict(self) -> dict[str, Any]:
        return {
            'artifact_type': 'govengine_boundary_report',
            'schema_version': self.schema_version,
            'status': self.status,
            'boundary': self.boundary.as_dict(),
            'profiles': [profile.as_dict() for profile in self.profiles],
            'profile_conformance': [conformance.as_dict() for conformance in self.profile_conformance],
            'surfaces': [dict(surface) for surface in self.surfaces],
            'summary': {
                'profile_count': len(self.profiles),
                'profile_conformance_passed': sum(1 for conformance in self.profile_conformance if conformance.passed),
                'surface_count': len(self.surfaces),
                'forbidden_profile_ownership_count': len(self.boundary.forbidden_profile_ownership),
            },
            'non_claims': list(self.boundary.non_claims),
        }


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
            'govengine_admission_policy_core',
            'govengine_evidence_review_core',
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


def domain_profile_conformance(
    value: Mapping[str, Any] | DomainProfileContract,
    *,
    allowed_consumes: tuple[str, ...] = ALLOWED_PROFILE_CONSUMES,
) -> DomainProfileConformance:
    contract = validate_domain_profile_contract(value)
    allowed = set(allowed_consumes)
    unknown_consumes = tuple(item for item in contract.consumes if item not in allowed)
    forbidden = tuple(item for item in contract.owns if item in set(FORBIDDEN_PROFILE_OWNERSHIP))
    return DomainProfileConformance(
        profile=contract,
        status='passed' if not unknown_consumes and not forbidden else 'failed',
        allowed_consumes=allowed_consumes,
        unknown_consumes=unknown_consumes,
        forbidden_ownership=forbidden,
    )


def validate_domain_profile_conformance(
    value: Mapping[str, Any] | DomainProfileContract,
    *,
    allowed_consumes: tuple[str, ...] = ALLOWED_PROFILE_CONSUMES,
) -> DomainProfileConformance:
    conformance = domain_profile_conformance(value, allowed_consumes=allowed_consumes)
    if conformance.forbidden_ownership:
        raise GovApiError(f'forbidden_domain_profile_ownership:{conformance.forbidden_ownership[0]}')
    if conformance.unknown_consumes:
        raise GovApiError(f'unknown_domain_profile_consume:{conformance.unknown_consumes[0]}')
    return conformance


def known_profile_contracts() -> tuple[DomainProfileContract, ...]:
    return (ravenclaw_profile_contract(),)


def boundary_surface_index() -> tuple[dict[str, Any], ...]:
    return tuple(surface.as_dict() for surface in public_surface_index())


def kernel_boundary_report(
    profiles: tuple[DomainProfileContract, ...] | None = None,
) -> BoundaryReport:
    profile_contracts = profiles if profiles is not None else known_profile_contracts()
    conformance = tuple(validate_domain_profile_conformance(profile) for profile in profile_contracts)
    return BoundaryReport(
        boundary=kernel_boundary_contract(),
        profiles=tuple(profile_contracts),
        profile_conformance=conformance,
        surfaces=boundary_surface_index(),
    )


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
