from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from govengine.api import GovApiError, require_mapping
from govengine.profiles import profile_conformance_report, validate_domain_profile
from govengine.signing import govengine_record_digest

PROFILE_GOVERNANCE_REQUEST_SCHEMA_VERSION = 'v0.1'
PROFILE_GOVERNANCE_PROJECTION_SCHEMA_VERSION = 'v0.1'
PROFILE_CONNECTOR_COMPATIBILITY_SCHEMA_VERSION = 'v0.1'

SUPPORTED_TRACKS = frozenset({'readonly', 'mutation', 'all'})
SUPPORTED_HOOK_TYPES = frozenset({'admission', 'evidence', 'planning', 'runner'})
ALLOWED_RUNNER_MODES = frozenset({'dry_run', 'local_fixture'})

BASELINE_POLICY_CONTROLS = (
    'receipt_required',
    'runner_dry_run_only',
    'policy_hooks_declared',
    'evidence_expectations_declared',
    'supported_tracks_declared',
    'capability_coverage',
)


@dataclass(frozen=True)
class ProfileGovernanceRequest:
    """Bounded host projection for profile governance evaluation."""

    schema_version: str
    request_id: str
    profile_name: str
    profile_version: str
    supported_tracks: tuple[str, ...] = ()
    policy_hooks: tuple[Mapping[str, Any], ...] = ()
    evidence_expectations: tuple[Mapping[str, Any], ...] = ()
    runner_posture: Mapping[str, Any] = field(default_factory=dict)
    required_capabilities: tuple[str, ...] = ()
    profile_declared_capabilities: tuple[str, ...] = ()
    available_capabilities: tuple[str, ...] = ()
    connector_backends: tuple[Mapping[str, Any], ...] = ()
    domain_profile: Mapping[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            'schema_version': self.schema_version,
            'request_id': self.request_id,
            'profile_name': self.profile_name,
            'profile_version': self.profile_version,
            'supported_tracks': list(self.supported_tracks),
            'policy_hooks': [dict(item) for item in self.policy_hooks],
            'evidence_expectations': [dict(item) for item in self.evidence_expectations],
            'runner_posture': dict(self.runner_posture),
            'required_capabilities': list(self.required_capabilities),
            'profile_declared_capabilities': list(self.profile_declared_capabilities),
            'available_capabilities': list(self.available_capabilities),
            'connector_backends': [dict(item) for item in self.connector_backends],
        }
        if self.domain_profile is not None:
            payload['domain_profile'] = dict(self.domain_profile)
        return payload


@dataclass(frozen=True)
class ProfileGovernanceProjection:
    schema_version: str
    status: str
    request_id: str
    profile_name: str
    profile_version: str
    reason_code: str
    governance_checks: tuple[Mapping[str, Any], ...] = ()
    blockers: tuple[str, ...] = ()
    supported_tracks: tuple[str, ...] = ()
    request_digest: str = ''
    projection_digest: str = ''
    domain_profile_conformance: Mapping[str, Any] | None = None
    non_claims: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        payload = {
            'schema_version': self.schema_version,
            'status': self.status,
            'request_id': self.request_id,
            'profile_name': self.profile_name,
            'profile_version': self.profile_version,
            'reason_code': self.reason_code,
            'governance_checks': [dict(item) for item in self.governance_checks],
            'blockers': list(self.blockers),
            'supported_tracks': list(self.supported_tracks),
            'request_digest': self.request_digest,
            'projection_digest': self.projection_digest,
            'non_claims': list(self.non_claims),
        }
        if self.domain_profile_conformance is not None:
            payload['domain_profile_conformance'] = dict(self.domain_profile_conformance)
        return payload


@dataclass(frozen=True)
class ProfileConnectorCompatibilityReport:
    schema_version: str
    status: str
    request_id: str
    profile_name: str
    reason_code: str
    required_capabilities: tuple[str, ...] = ()
    satisfied_capabilities: tuple[str, ...] = ()
    missing_capabilities: tuple[str, ...] = ()
    policy_controls: tuple[Mapping[str, Any], ...] = ()
    blockers: tuple[str, ...] = ()
    report_digest: str = ''
    non_claims: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            'schema_version': self.schema_version,
            'status': self.status,
            'request_id': self.request_id,
            'profile_name': self.profile_name,
            'reason_code': self.reason_code,
            'required_capabilities': list(self.required_capabilities),
            'satisfied_capabilities': list(self.satisfied_capabilities),
            'missing_capabilities': list(self.missing_capabilities),
            'policy_controls': [dict(item) for item in self.policy_controls],
            'blockers': list(self.blockers),
            'report_digest': self.report_digest,
            'non_claims': list(self.non_claims),
        }


@dataclass(frozen=True)
class ProfileGovernanceBundle:
    schema_version: str
    status: str
    request_id: str
    profile_name: str
    governance: ProfileGovernanceProjection
    compatibility: ProfileConnectorCompatibilityReport
    bundle_digest: str = ''
    non_claims: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            'schema_version': self.schema_version,
            'status': self.status,
            'request_id': self.request_id,
            'profile_name': self.profile_name,
            'governance': self.governance.as_dict(),
            'compatibility': self.compatibility.as_dict(),
            'bundle_digest': self.bundle_digest,
            'non_claims': list(self.non_claims),
        }


def validate_profile_governance_request(
    value: Mapping[str, Any] | ProfileGovernanceRequest,
) -> ProfileGovernanceRequest:
    if isinstance(value, ProfileGovernanceRequest):
        return value
    raw = require_mapping(value, reason_code='invalid_profile_governance_request')
    schema_version = str(raw.get('schema_version') or '').strip()
    if schema_version != PROFILE_GOVERNANCE_REQUEST_SCHEMA_VERSION:
        raise GovApiError(f'unsupported_profile_governance_request_version:{schema_version}')
    request_id = _required_text(raw, 'request_id')
    profile_name = _required_text(raw, 'profile_name')
    profile_version = _required_text(raw, 'profile_version')
    domain_profile = raw.get('domain_profile')
    if domain_profile is not None and not isinstance(domain_profile, Mapping):
        raise GovApiError('invalid_profile_governance_domain_profile')
    return ProfileGovernanceRequest(
        schema_version=schema_version,
        request_id=request_id,
        profile_name=profile_name,
        profile_version=profile_version,
        supported_tracks=_string_tuple(raw.get('supported_tracks') or ()),
        policy_hooks=_mapping_tuple(raw.get('policy_hooks') or ()),
        evidence_expectations=_mapping_tuple(raw.get('evidence_expectations') or ()),
        runner_posture=require_mapping(raw.get('runner_posture') or {}, reason_code='invalid_runner_posture'),
        required_capabilities=_string_tuple(raw.get('required_capabilities') or ()),
        profile_declared_capabilities=_string_tuple(
            raw.get('profile_declared_capabilities') or raw.get('required_capabilities') or ()
        ),
        available_capabilities=_string_tuple(raw.get('available_capabilities') or ()),
        connector_backends=_mapping_tuple(raw.get('connector_backends') or ()),
        domain_profile=dict(domain_profile) if isinstance(domain_profile, Mapping) else None,
    )


def project_profile_governance(
    request: Mapping[str, Any] | ProfileGovernanceRequest,
) -> ProfileGovernanceProjection:
    checked = validate_profile_governance_request(request)
    checks: list[dict[str, Any]] = []
    blockers: list[str] = []

    tracks = _check_supported_tracks(checked.supported_tracks)
    checks.append(tracks)
    if not tracks['passed']:
        blockers.append('unsupported_or_missing_supported_tracks')

    hooks = _check_policy_hooks(checked.policy_hooks)
    checks.append(hooks)
    if not hooks['passed']:
        blockers.append('invalid_policy_hooks')

    evidence = _check_evidence_expectations(checked.evidence_expectations)
    checks.append(evidence)
    if not evidence['passed']:
        blockers.append('invalid_evidence_expectations')

    runner = _check_runner_posture(checked.runner_posture)
    checks.append(runner)
    if not runner['passed']:
        blockers.append('invalid_runner_posture')

    domain_conformance: dict[str, Any] | None = None
    if checked.domain_profile is not None:
        report = profile_conformance_report(validate_domain_profile(checked.domain_profile))
        domain_conformance = {
            'status': report.status,
            'failed_checks': list(report.failed_checks),
        }
        checks.append(
            {
                'gate': 'domain_profile_conformance',
                'passed': report.status == 'passed',
                'details': domain_conformance,
            }
        )
        if report.status != 'passed':
            blockers.append('domain_profile_conformance_failed')

    status = 'passed' if not blockers else 'blocked'
    reason_code = 'profile_governance_passed' if not blockers else blockers[0]
    request_digest = profile_governance_request_digest(checked)
    body = {
        'schema_version': PROFILE_GOVERNANCE_PROJECTION_SCHEMA_VERSION,
        'status': status,
        'request_id': checked.request_id,
        'profile_name': checked.profile_name,
        'profile_version': checked.profile_version,
        'reason_code': reason_code,
        'governance_checks': checks,
        'blockers': blockers,
        'supported_tracks': list(checked.supported_tracks),
        'request_digest': request_digest,
    }
    if domain_conformance is not None:
        body['domain_profile_conformance'] = domain_conformance
    projection_digest = govengine_record_digest(
        body,
        record_type='govengine.profile_governance.ProfileGovernanceProjection',
        schema_version=PROFILE_GOVERNANCE_PROJECTION_SCHEMA_VERSION,
    )
    return ProfileGovernanceProjection(
        schema_version=PROFILE_GOVERNANCE_PROJECTION_SCHEMA_VERSION,
        status=status,
        request_id=checked.request_id,
        profile_name=checked.profile_name,
        profile_version=checked.profile_version,
        reason_code=reason_code,
        governance_checks=tuple(checks),
        blockers=tuple(blockers),
        supported_tracks=checked.supported_tracks,
        request_digest=request_digest,
        projection_digest=projection_digest,
        domain_profile_conformance=domain_conformance,
        non_claims=_GOVERNANCE_NON_CLAIMS,
    )


def evaluate_profile_connector_compatibility(
    request: Mapping[str, Any] | ProfileGovernanceRequest,
) -> ProfileConnectorCompatibilityReport:
    checked = validate_profile_governance_request(request)
    provided = _capability_index(checked.available_capabilities, checked.connector_backends)
    profile_declared = set(checked.profile_declared_capabilities)
    satisfied: list[str] = []
    missing: list[str] = []
    for capability in checked.required_capabilities:
        if capability in profile_declared or capability in provided or _matches_runtime_stack(
            capability,
            provided,
            checked.connector_backends,
        ):
            satisfied.append(capability)
        else:
            missing.append(capability)

    policy_controls = _policy_control_checks(checked, missing)
    blockers = [item['control'] for item in policy_controls if not item['passed']]
    if missing:
        blockers.append('missing_required_capabilities')
    status = 'passed' if not blockers else 'blocked'
    reason_code = 'profile_connector_compatible' if not blockers else blockers[0]
    body = {
        'schema_version': PROFILE_CONNECTOR_COMPATIBILITY_SCHEMA_VERSION,
        'status': status,
        'request_id': checked.request_id,
        'profile_name': checked.profile_name,
        'reason_code': reason_code,
        'required_capabilities': list(checked.required_capabilities),
        'satisfied_capabilities': satisfied,
        'missing_capabilities': missing,
        'policy_controls': policy_controls,
        'blockers': blockers,
    }
    report_digest = govengine_record_digest(
        body,
        record_type='govengine.profile_governance.ProfileConnectorCompatibilityReport',
        schema_version=PROFILE_CONNECTOR_COMPATIBILITY_SCHEMA_VERSION,
    )
    return ProfileConnectorCompatibilityReport(
        schema_version=PROFILE_CONNECTOR_COMPATIBILITY_SCHEMA_VERSION,
        status=status,
        request_id=checked.request_id,
        profile_name=checked.profile_name,
        reason_code=reason_code,
        required_capabilities=checked.required_capabilities,
        satisfied_capabilities=tuple(satisfied),
        missing_capabilities=tuple(missing),
        policy_controls=tuple(policy_controls),
        blockers=tuple(blockers),
        report_digest=report_digest,
        non_claims=_COMPATIBILITY_NON_CLAIMS,
    )


def explain_profile_governance(
    request: Mapping[str, Any] | ProfileGovernanceRequest,
) -> ProfileGovernanceBundle:
    checked = validate_profile_governance_request(request)
    governance = project_profile_governance(checked)
    compatibility = evaluate_profile_connector_compatibility(checked)
    blockers = list(dict.fromkeys([*governance.blockers, *compatibility.blockers]))
    status = 'passed' if not blockers else 'blocked'
    bundle_body = {
        'schema_version': PROFILE_GOVERNANCE_PROJECTION_SCHEMA_VERSION,
        'status': status,
        'request_id': checked.request_id,
        'profile_name': checked.profile_name,
        'governance_digest': governance.projection_digest,
        'compatibility_digest': compatibility.report_digest,
        'blockers': blockers,
    }
    bundle_digest = govengine_record_digest(
        bundle_body,
        record_type='govengine.profile_governance.ProfileGovernanceBundle',
        schema_version=PROFILE_GOVERNANCE_PROJECTION_SCHEMA_VERSION,
    )
    return ProfileGovernanceBundle(
        schema_version=PROFILE_GOVERNANCE_PROJECTION_SCHEMA_VERSION,
        status=status,
        request_id=checked.request_id,
        profile_name=checked.profile_name,
        governance=governance,
        compatibility=compatibility,
        bundle_digest=bundle_digest,
        non_claims=_BUNDLE_NON_CLAIMS,
    )


def profile_governance_request_digest(
    request: Mapping[str, Any] | ProfileGovernanceRequest,
) -> str:
    checked = validate_profile_governance_request(request)
    return govengine_record_digest(
        checked.as_dict(),
        record_type='govengine.profile_governance.ProfileGovernanceRequest',
        schema_version=PROFILE_GOVERNANCE_REQUEST_SCHEMA_VERSION,
    )


def _check_supported_tracks(tracks: tuple[str, ...]) -> dict[str, Any]:
    invalid = [track for track in tracks if track not in SUPPORTED_TRACKS]
    passed = bool(tracks) and not invalid
    return {
        'gate': 'supported_tracks',
        'passed': passed,
        'details': {'tracks': list(tracks), 'invalid': invalid},
    }


def _check_policy_hooks(hooks: tuple[Mapping[str, Any], ...]) -> dict[str, Any]:
    invalid: list[str] = []
    names: list[str] = []
    for hook in hooks:
        name = str(hook.get('name') or '').strip()
        hook_type = str(hook.get('hook_type') or '').strip()
        if not name or not hook_type:
            invalid.append('missing_name_or_hook_type')
            continue
        if hook_type not in SUPPORTED_HOOK_TYPES:
            invalid.append(f'unsupported_hook_type:{hook_type}')
        names.append(name)
    duplicate = len(names) != len(set(names))
    passed = bool(hooks) and not invalid and not duplicate
    return {
        'gate': 'policy_hooks',
        'passed': passed,
        'details': {'count': len(hooks), 'invalid': invalid, 'duplicate_names': duplicate},
    }


def _check_evidence_expectations(expectations: tuple[Mapping[str, Any], ...]) -> dict[str, Any]:
    invalid: list[str] = []
    for item in expectations:
        name = str(item.get('name') or '').strip()
        if not name:
            invalid.append('missing_evidence_expectation_name')
            continue
        if not bool(item.get('receipt_bound_required', True)):
            invalid.append(f'unbounded_evidence_expectation:{name}')
    passed = bool(expectations) and not invalid
    return {
        'gate': 'evidence_expectations',
        'passed': passed,
        'details': {'count': len(expectations), 'invalid': invalid},
    }


def _check_runner_posture(posture: Mapping[str, Any]) -> dict[str, Any]:
    mode = str(posture.get('mode') or '').strip()
    live_enabled = bool(posture.get('live_enabled', False))
    name = str(posture.get('name') or '').strip()
    passed = bool(name) and mode in ALLOWED_RUNNER_MODES and not live_enabled
    return {
        'gate': 'runner_posture',
        'passed': passed,
        'details': {'name': name, 'mode': mode, 'live_enabled': live_enabled},
    }


def _policy_control_checks(
    request: ProfileGovernanceRequest,
    missing_capabilities: list[str],
) -> list[dict[str, Any]]:
    controls: list[dict[str, Any]] = []
    controls.append(
        {
            'control': 'supported_tracks_declared',
            'passed': bool(request.supported_tracks),
            'details': {'tracks': list(request.supported_tracks)},
        }
    )
    controls.append(
        {
            'control': 'policy_hooks_declared',
            'passed': bool(request.policy_hooks),
            'details': {'count': len(request.policy_hooks)},
        }
    )
    controls.append(
        {
            'control': 'evidence_expectations_declared',
            'passed': bool(request.evidence_expectations),
            'details': {'count': len(request.evidence_expectations)},
        }
    )
    controls.append(
        {
            'control': 'receipt_required',
            'passed': all(
                bool(item.get('receipt_bound_required', True))
                for item in request.evidence_expectations
            ),
            'details': {'expectations': len(request.evidence_expectations)},
        }
    )
    runner = request.runner_posture
    controls.append(
        {
            'control': 'runner_dry_run_only',
            'passed': (
                str(runner.get('mode') or '') in ALLOWED_RUNNER_MODES
                and not bool(runner.get('live_enabled', False))
            ),
            'details': {
                'mode': runner.get('mode'),
                'live_enabled': runner.get('live_enabled', False),
            },
        }
    )
    controls.append(
        {
            'control': 'capability_coverage',
            'passed': not missing_capabilities,
            'details': {
                'required': len(request.required_capabilities),
                'missing': missing_capabilities,
            },
        }
    )
    return controls


def _capability_index(
    available_capabilities: tuple[str, ...],
    connector_backends: tuple[Mapping[str, Any], ...],
) -> set[str]:
    provided = set(available_capabilities)
    for backend in connector_backends:
        for capability in _string_tuple(backend.get('capability_descriptors') or ()):
            provided.add(capability)
        backend_class = str(backend.get('backend_class') or '').strip()
        if backend_class:
            provided.add(backend_class)
            provided.add(f'connector.{backend_class}')
    return provided


def _matches_runtime_stack(
    capability: str,
    provided: set[str],
    connector_backends: tuple[Mapping[str, Any], ...],
) -> bool:
    if capability in provided:
        return True
    aliases = _RUNTIME_CAPABILITY_ALIASES.get(capability, ())
    if any(alias in provided for alias in aliases):
        return True
    for backend in connector_backends:
        backend_class = str(backend.get('backend_class') or '').strip()
        if capability == backend_class:
            return True
        descriptors = set(_string_tuple(backend.get('capability_descriptors') or ()))
        if capability in descriptors:
            return True
    return False


_RUNTIME_CAPABILITY_ALIASES = {
    'http_api': ('connector.http.rest.read', 'connector.http.rest.mutate'),
    'local_shell_readonly': ('connector.shell.readonly',),
    'ssh_readonly': ('connector.ssh.readonly',),
    'host_mutation': ('connector.http.rest.mutate',),
}


def _required_text(value: Mapping[str, Any], key: str) -> str:
    text = str(value.get(key) or '').strip()
    if not text:
        raise GovApiError(f'missing_profile_governance_{key}')
    return text


def _string_tuple(values: Any) -> tuple[str, ...]:
    if isinstance(values, str):
        text = values.strip()
        return (text,) if text else ()
    try:
        return tuple(str(value).strip() for value in values if str(value).strip())
    except TypeError as exc:
        raise GovApiError('invalid_profile_governance_sequence') from exc


def _mapping_tuple(values: Any) -> tuple[dict[str, Any], ...]:
    try:
        return tuple(
            dict(require_mapping(value, reason_code='invalid_profile_governance_mapping'))
            for value in values
        )
    except TypeError as exc:
        raise GovApiError('invalid_profile_governance_mapping_sequence') from exc


_GOVERNANCE_NON_CLAIMS = (
    'Does not interpret domain semantics or profile-owned taxonomy.',
    'Does not execute connectors, subprocesses, SSH, or HTTP.',
    'Does not grant live execution authority.',
)

_COMPATIBILITY_NON_CLAIMS = (
    'Does not perform backend IO or connector certification tests.',
    'Checks only declared capability descriptors against required capabilities.',
    'Does not replace RExecOp plugin compatibility runtime probes.',
)

_BUNDLE_NON_CLAIMS = _GOVERNANCE_NON_CLAIMS + _COMPATIBILITY_NON_CLAIMS