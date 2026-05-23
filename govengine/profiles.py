from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from govengine.api import GovApiError, require_mapping
from govengine.boundary import (
    DomainProfileContract,
    validate_domain_profile_conformance,
)


FORBIDDEN_PROFILE_CLAIMS = (
    'govengine_core_modules',
    'sclite_schema_authority',
    'live_execution_authority',
    'credential_or_key_store',
    'carrier_adapter_ownership',
    'pki_or_kms_ownership',
    'product_ux_ownership',
)

DEFAULT_CONSUMES = (
    'govengine_artifact_governance_core',
    'govengine_planning_contracts_core',
    'govengine_admission_policy_core',
    'govengine_evidence_review_core',
    'govengine_domain_profile_sdk',
    'govengine_controlled_execution_core',
    'sclite_lifecycle_artifacts',
    'sclite_review_bundles',
)


@dataclass(frozen=True)
class ResourceTypeRegistry:
    names: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {'names': list(self.names)}


@dataclass(frozen=True)
class TaskFamilyRegistry:
    names: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {'names': list(self.names)}


@dataclass(frozen=True)
class PlanningStageRegistry:
    names: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {'names': list(self.names)}


@dataclass(frozen=True)
class CapabilityDeclaration:
    name: str
    task_families: tuple[str, ...] = ()
    resource_types: tuple[str, ...] = ()
    non_claims: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            'name': self.name,
            'task_families': list(self.task_families),
            'resource_types': list(self.resource_types),
            'non_claims': list(self.non_claims),
        }


@dataclass(frozen=True)
class RunnerProfileDeclaration:
    name: str
    mode: str = 'dry_run'
    live_enabled: bool = False
    non_claims: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            'name': self.name,
            'mode': self.mode,
            'live_enabled': self.live_enabled,
            'non_claims': list(self.non_claims),
        }


@dataclass(frozen=True)
class PolicyHookDeclaration:
    name: str
    hook_type: str
    non_claims: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            'name': self.name,
            'hook_type': self.hook_type,
            'non_claims': list(self.non_claims),
        }


@dataclass(frozen=True)
class EvidenceRuleDeclaration:
    name: str
    claim_types: tuple[str, ...] = ()
    receipt_bound_required: bool = True
    non_claims: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            'name': self.name,
            'claim_types': list(self.claim_types),
            'receipt_bound_required': self.receipt_bound_required,
            'non_claims': list(self.non_claims),
        }


@dataclass(frozen=True)
class DomainProfile:
    name: str
    version: str
    owner: str
    resource_types: ResourceTypeRegistry
    task_families: TaskFamilyRegistry
    planning_stages: PlanningStageRegistry
    capabilities: tuple[CapabilityDeclaration, ...] = ()
    runner_profiles: tuple[RunnerProfileDeclaration, ...] = ()
    policy_hooks: tuple[PolicyHookDeclaration, ...] = ()
    evidence_rules: tuple[EvidenceRuleDeclaration, ...] = ()
    consumes: tuple[str, ...] = DEFAULT_CONSUMES
    owns: tuple[str, ...] = ('domain_taxonomy', 'domain_policy_meaning', 'domain_evidence_expectations')
    non_claims: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            'name': self.name,
            'version': self.version,
            'owner': self.owner,
            'resource_types': self.resource_types.as_dict(),
            'task_families': self.task_families.as_dict(),
            'planning_stages': self.planning_stages.as_dict(),
            'capabilities': [item.as_dict() for item in self.capabilities],
            'runner_profiles': [item.as_dict() for item in self.runner_profiles],
            'policy_hooks': [item.as_dict() for item in self.policy_hooks],
            'evidence_rules': [item.as_dict() for item in self.evidence_rules],
            'consumes': list(self.consumes),
            'owns': list(self.owns),
            'non_claims': list(self.non_claims),
            'metadata': dict(self.metadata),
        }

    def boundary_contract(self) -> DomainProfileContract:
        return DomainProfileContract(
            name=self.name,
            version=self.version,
            owner=self.owner,
            owns=self.owns,
            consumes=self.consumes,
            non_claims=self.non_claims,
            metadata={'sdk_profile': self.as_dict()},
        )


@dataclass(frozen=True)
class ProfileConformanceReport:
    profile: DomainProfile
    status: str
    checks: Mapping[str, bool]
    failed_checks: tuple[str, ...] = ()
    boundary_report: Mapping[str, Any] = field(default_factory=dict)
    non_claims: tuple[str, ...] = (
        'Conformance does not grant live execution authority.',
        'Conformance does not make GovEngine own profile domain semantics.',
        'Conformance does not implement carrier adapters.',
    )

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out['profile'] = self.profile.as_dict()
        out['checks'] = dict(self.checks)
        out['failed_checks'] = list(self.failed_checks)
        out['boundary_report'] = dict(self.boundary_report)
        out['non_claims'] = list(self.non_claims)
        return out


def validate_domain_profile(value: Mapping[str, Any] | DomainProfile) -> DomainProfile:
    profile = value if isinstance(value, DomainProfile) else _profile_from_mapping(value)
    _validate_unique('resource_types', profile.resource_types.names)
    _validate_unique('task_families', profile.task_families.names)
    _validate_unique('planning_stages', profile.planning_stages.names)
    _validate_named_declarations('capabilities', profile.capabilities)
    _validate_named_declarations('runner_profiles', profile.runner_profiles)
    _validate_named_declarations('policy_hooks', profile.policy_hooks)
    _validate_named_declarations('evidence_rules', profile.evidence_rules)
    _reject_forbidden(profile.owns)
    for runner in profile.runner_profiles:
        if runner.live_enabled or runner.mode not in {'dry_run', 'local_fixture'}:
            raise GovApiError(f'forbidden_runner_profile:{runner.name}')
    for rule in profile.evidence_rules:
        if not rule.receipt_bound_required:
            raise GovApiError(f'unbounded_evidence_rule:{rule.name}')
    return profile


def profile_conformance_report(value: Mapping[str, Any] | DomainProfile) -> ProfileConformanceReport:
    profile = validate_domain_profile(value)
    failed: list[str] = []
    checks = {
        'resource_types_declared': bool(profile.resource_types.names),
        'task_families_declared': bool(profile.task_families.names),
        'planning_stages_declared': bool(profile.planning_stages.names),
        'runner_profiles_dry_run_only': all(
            not runner.live_enabled and runner.mode in {'dry_run', 'local_fixture'}
            for runner in profile.runner_profiles
        ),
        'evidence_rules_receipt_bounded': all(rule.receipt_bound_required for rule in profile.evidence_rules),
        'boundary_conformance_passed': False,
    }
    boundary = validate_domain_profile_conformance(profile.boundary_contract())
    checks['boundary_conformance_passed'] = boundary.passed
    failed = [name for name, passed in checks.items() if not passed]
    return ProfileConformanceReport(
        profile=profile,
        status='passed' if not failed else 'failed',
        checks=checks,
        failed_checks=tuple(failed),
        boundary_report=boundary.as_dict(),
    )


def validate_profile_conformance(value: Mapping[str, Any] | DomainProfile) -> ProfileConformanceReport:
    report = profile_conformance_report(value)
    if report.failed_checks:
        raise GovApiError(f'profile_conformance_failed:{report.failed_checks[0]}')
    return report


def ravenclaw_security_profile() -> DomainProfile:
    return DomainProfile(
        name='ravenclaw-security',
        version='0.10.2a0',
        owner='ravenclaw',
        resource_types=ResourceTypeRegistry(('host', 'url', 'endpoint', 'web_app')),
        task_families=TaskFamilyRegistry(('recon', 'authz', 'idor', 'workflow', 'content_discovery', 'tls_assessment')),
        planning_stages=PlanningStageRegistry((
            'discovery',
            'validation',
            'control_boundary_confirmation',
            'state_transition_confirmation',
            'bounded_exploit_proof',
            'report_artifact_capture',
        )),
        capabilities=(
            CapabilityDeclaration(
                name='public_safe_security_research',
                task_families=('recon', 'authz', 'workflow'),
                resource_types=('host', 'url', 'endpoint', 'web_app'),
                non_claims=('Does not authorize live target testing.',),
            ),
        ),
        runner_profiles=(RunnerProfileDeclaration(name='dry_run_security_fixture', mode='dry_run'),),
        policy_hooks=(PolicyHookDeclaration(name='scope_and_authorization_gate', hook_type='admission'),),
        evidence_rules=(
            EvidenceRuleDeclaration(
                name='receipt_bounded_security_claims',
                claim_types=('execution_truth', 'bounded_security_finding'),
            ),
        ),
        consumes=DEFAULT_CONSUMES + ('govengine_security_profile_helpers',),
        owns=('domain_taxonomy', 'domain_policy_meaning', 'domain_tool_semantics', 'domain_evidence_expectations'),
        non_claims=(
            'Does not make GovEngine own Ravenclaw finding taxonomy.',
            'Does not make GovEngine own Logdash or campaign UX.',
            'Does not grant live execution authority.',
        ),
    )


def tecrax_infra_ops_profile() -> DomainProfile:
    return DomainProfile(
        name='tecrax-infra-ops',
        version='0.10.2a0',
        owner='tecrax',
        resource_types=ResourceTypeRegistry(('server', 'service', 'container', 'firewall', 'switch', 'vm', 'backup_job')),
        task_families=TaskFamilyRegistry(('inspect', 'diagnose', 'propose_change', 'dry_run_change', 'verify_fixture', 'rollback_plan')),
        planning_stages=PlanningStageRegistry(('observe', 'diagnose', 'plan_change', 'validate_dry_run', 'approval_required', 'verify_fixture', 'rollback_plan_ready')),
        capabilities=(
            CapabilityDeclaration(
                name='dry_run_infra_change_review',
                task_families=('inspect', 'diagnose', 'propose_change', 'dry_run_change'),
                resource_types=('server', 'service', 'container', 'firewall', 'vm'),
                non_claims=('Does not connect to infrastructure.',),
            ),
        ),
        runner_profiles=(RunnerProfileDeclaration(name='local_fixture_only', mode='local_fixture'),),
        policy_hooks=(PolicyHookDeclaration(name='change_approval_required', hook_type='admission'),),
        evidence_rules=(
            EvidenceRuleDeclaration(
                name='fixture_receipt_required',
                claim_types=('dry_run_change_review', 'rollback_plan_review'),
            ),
        ),
        owns=('domain_taxonomy', 'domain_policy_meaning', 'domain_evidence_expectations'),
        non_claims=(
            'Does not make GovEngine own infrastructure credentials.',
            'Does not make GovEngine own service inventories or product UX.',
            'Does not grant live infrastructure execution authority.',
        ),
        metadata={'status': 'skeleton', 'execution_scope': 'dry_run_local_fixture_only'},
    )


def _profile_from_mapping(value: Mapping[str, Any]) -> DomainProfile:
    raw = require_mapping(value, reason_code='invalid_domain_profile')
    raw_resource_types = require_mapping(raw.get('resource_types') or {}, reason_code='invalid_resource_types')
    raw_task_families = require_mapping(raw.get('task_families') or {}, reason_code='invalid_task_families')
    raw_planning_stages = require_mapping(raw.get('planning_stages') or {}, reason_code='invalid_planning_stages')
    return DomainProfile(
        name=_required(raw, 'name'),
        version=str(raw.get('version') or 'v0.1'),
        owner=_required(raw, 'owner'),
        resource_types=ResourceTypeRegistry(_tuple(raw_resource_types.get('names') or ())),
        task_families=TaskFamilyRegistry(_tuple(raw_task_families.get('names') or ())),
        planning_stages=PlanningStageRegistry(_tuple(raw_planning_stages.get('names') or ())),
        capabilities=tuple(
            CapabilityDeclaration(
                name=_required(item, 'name'),
                task_families=_tuple(item.get('task_families') or ()),
                resource_types=_tuple(item.get('resource_types') or ()),
                non_claims=_tuple(item.get('non_claims') or ()),
            )
            for item in _mappings(raw.get('capabilities') or ())
        ),
        runner_profiles=tuple(
            RunnerProfileDeclaration(
                name=_required(item, 'name'),
                mode=str(item.get('mode') or 'dry_run'),
                live_enabled=_bool(item.get('live_enabled'), default=False),
                non_claims=_tuple(item.get('non_claims') or ()),
            )
            for item in _mappings(raw.get('runner_profiles') or ())
        ),
        policy_hooks=tuple(
            PolicyHookDeclaration(
                name=_required(item, 'name'),
                hook_type=_required(item, 'hook_type'),
                non_claims=_tuple(item.get('non_claims') or ()),
            )
            for item in _mappings(raw.get('policy_hooks') or ())
        ),
        evidence_rules=tuple(
            EvidenceRuleDeclaration(
                name=_required(item, 'name'),
                claim_types=_tuple(item.get('claim_types') or ()),
                receipt_bound_required=_bool(item.get('receipt_bound_required'), default=True),
                non_claims=_tuple(item.get('non_claims') or ()),
            )
            for item in _mappings(raw.get('evidence_rules') or ())
        ),
        consumes=_tuple(raw.get('consumes') or DEFAULT_CONSUMES),
        owns=_tuple(raw.get('owns') or ('domain_taxonomy', 'domain_policy_meaning', 'domain_evidence_expectations')),
        non_claims=_tuple(raw.get('non_claims') or ()),
        metadata=raw.get('metadata') if isinstance(raw.get('metadata'), Mapping) else {},
    )


def _tuple(values: Any) -> tuple[str, ...]:
    if isinstance(values, str):
        return (values,)
    try:
        return tuple(str(value).strip() for value in values if str(value).strip())
    except TypeError as exc:
        raise GovApiError('invalid_profile_sequence') from exc


def _mappings(values: Any) -> tuple[Mapping[str, Any], ...]:
    try:
        out = tuple(require_mapping(value, reason_code='invalid_profile_declaration') for value in values)
    except TypeError as exc:
        raise GovApiError('invalid_profile_declaration_sequence') from exc
    return out


def _required(value: Mapping[str, Any], key: str) -> str:
    text = str(value.get(key) or '').strip()
    if not text:
        raise GovApiError(f'missing_profile_{key}')
    return text


def _bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    raise GovApiError('invalid_profile_boolean')


def _validate_unique(label: str, values: tuple[str, ...]) -> None:
    if not values:
        raise GovApiError(f'missing_{label}')
    if len(values) != len(set(values)):
        raise GovApiError(f'duplicate_{label}')


def _validate_named_declarations(label: str, values: tuple[Any, ...]) -> None:
    names = tuple(str(getattr(value, 'name', '')).strip() for value in values)
    if len(names) != len(set(names)):
        raise GovApiError(f'duplicate_{label}')


def _reject_forbidden(owns: tuple[str, ...]) -> None:
    claimed = set(owns).intersection(FORBIDDEN_PROFILE_CLAIMS)
    if claimed:
        raise GovApiError(f'forbidden_profile_claim:{sorted(claimed)[0]}')
