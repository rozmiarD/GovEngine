from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from govengine.api import GovApiError, require_mapping
from govengine.execution.runner_protocol import GovRunnerReceipt, GovRunnerRequest


LEASE_STATES = ('active', 'released', 'expired', 'blocked')
CWD_POLICIES = ('none', 'repo_root', 'explicit_path')
ENV_POLICIES = ('empty', 'allowlist')
STDIN_POLICIES = ('none', 'bounded', 'forbidden')

FORBIDDEN_SUPERVISION_METADATA_KEYS = (
    'raw_intent',
    'prompt',
    'credential',
    'credentials',
    'secret',
    'token',
    'password',
    'api_key',
    'shell',
    'subprocess',
    'live_backend',
    'runtime_storage',
    'storage_path',
    'carrier_payload',
    'transport_payload',
    'scheduler',
    'schedule',
    'target',
    'target_url',
    'url',
)


@dataclass(frozen=True)
class GovRunnerLease:
    """Storage-neutral runner lease. Hosts own persistence and clocks."""

    lease_id: str
    request_id: str
    runner_profile: str = 'dry-run'
    state: str = 'active'
    expires_at: str = ''
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'GovRunnerLease':
        raw = require_mapping(value, reason_code='invalid_runner_lease')
        lease_id = str(raw.get('lease_id') or raw.get('id') or '').strip()
        if not lease_id:
            raise GovApiError('missing_runner_lease_id')
        request_id = str(raw.get('request_id') or '').strip()
        if not request_id:
            raise GovApiError('missing_runner_lease_request_id')
        item = cls(
            lease_id=lease_id,
            request_id=request_id,
            runner_profile=str(raw.get('runner_profile') or 'dry-run').strip() or 'dry-run',
            state=_enum(raw.get('state'), LEASE_STATES, 'active'),
            expires_at=str(raw.get('expires_at') or '').strip(),
            metadata=_metadata(raw.get('metadata')),
        )
        validate_runner_lease(item)
        return item

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out['metadata'] = dict(self.metadata)
        return out


@dataclass(frozen=True)
class GovSupervisionPlan:
    """Runner supervision requirements for one bounded runner request."""

    plan_id: str
    request_id: str
    runner_profile: str = 'dry-run'
    dry_run: bool = True
    live_backend_enabled: bool = False
    timeout_seconds: int = 30
    cwd_policy: str = 'none'
    env_policy: str = 'empty'
    stdin_policy: str = 'bounded'
    receipt_required: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'GovSupervisionPlan':
        raw = require_mapping(value, reason_code='invalid_supervision_plan')
        plan_id = str(raw.get('plan_id') or raw.get('id') or '').strip()
        if not plan_id:
            raise GovApiError('missing_supervision_plan_id')
        request_id = str(raw.get('request_id') or '').strip()
        if not request_id:
            raise GovApiError('missing_supervision_request_id')
        item = cls(
            plan_id=plan_id,
            request_id=request_id,
            runner_profile=str(raw.get('runner_profile') or 'dry-run').strip() or 'dry-run',
            dry_run=bool(raw.get('dry_run', True)),
            live_backend_enabled=bool(raw.get('live_backend_enabled', False)),
            timeout_seconds=_int(raw.get('timeout_seconds'), 30),
            cwd_policy=_enum(raw.get('cwd_policy'), CWD_POLICIES, 'none'),
            env_policy=_enum(raw.get('env_policy'), ENV_POLICIES, 'empty'),
            stdin_policy=_enum(raw.get('stdin_policy'), STDIN_POLICIES, 'bounded'),
            receipt_required=bool(raw.get('receipt_required', True)),
            metadata=_metadata(raw.get('metadata')),
        )
        validate_supervision_plan(item)
        return item

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out['metadata'] = dict(self.metadata)
        return out


@dataclass(frozen=True)
class GovSupervisionDecision:
    """Supervisor decision over a request/lease/receipt boundary."""

    decision_id: str
    request_id: str
    action: str = 'allow'
    reason_code: str = 'ok'
    interrupting: bool = False
    lease_id: str = ''
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'GovSupervisionDecision':
        raw = require_mapping(value, reason_code='invalid_supervision_decision')
        decision_id = str(raw.get('decision_id') or raw.get('id') or '').strip()
        if not decision_id:
            raise GovApiError('missing_supervision_decision_id')
        request_id = str(raw.get('request_id') or '').strip()
        if not request_id:
            raise GovApiError('missing_supervision_decision_request_id')
        item = cls(
            decision_id=decision_id,
            request_id=request_id,
            action=str(raw.get('action') or 'allow').strip() or 'allow',
            reason_code=str(raw.get('reason_code') or 'ok').strip() or 'ok',
            interrupting=bool(raw.get('interrupting', False)),
            lease_id=str(raw.get('lease_id') or '').strip(),
            metadata=_metadata(raw.get('metadata')),
        )
        validate_supervision_decision(item)
        return item

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out['metadata'] = dict(self.metadata)
        return out


def validate_runner_lease(value: Mapping[str, Any] | GovRunnerLease) -> GovRunnerLease:
    item = value if isinstance(value, GovRunnerLease) else GovRunnerLease.from_mapping(value)
    if item.state not in LEASE_STATES:
        raise GovApiError(f'unknown_runner_lease_state:{item.state}')
    _reject_forbidden_metadata(item.metadata)
    return item


def validate_supervision_plan(value: Mapping[str, Any] | GovSupervisionPlan) -> GovSupervisionPlan:
    item = value if isinstance(value, GovSupervisionPlan) else GovSupervisionPlan.from_mapping(value)
    if item.timeout_seconds <= 0:
        raise GovApiError('invalid_supervision_timeout')
    if item.cwd_policy not in CWD_POLICIES:
        raise GovApiError(f'unknown_cwd_policy:{item.cwd_policy}')
    if item.env_policy not in ENV_POLICIES:
        raise GovApiError(f'unknown_env_policy:{item.env_policy}')
    if item.stdin_policy not in STDIN_POLICIES:
        raise GovApiError(f'unknown_stdin_policy:{item.stdin_policy}')
    if not item.dry_run and not item.live_backend_enabled:
        raise GovApiError('live_backend_disabled')
    if not item.receipt_required:
        raise GovApiError('runner_receipt_required')
    _reject_forbidden_metadata(item.metadata)
    return item


def validate_supervision_decision(value: Mapping[str, Any] | GovSupervisionDecision) -> GovSupervisionDecision:
    item = value if isinstance(value, GovSupervisionDecision) else GovSupervisionDecision.from_mapping(value)
    _reject_forbidden_metadata(item.metadata)
    return item


def validate_supervised_runner_request(
    request: GovRunnerRequest,
    plan: GovSupervisionPlan | Mapping[str, Any],
) -> GovRunnerRequest:
    supervision = validate_supervision_plan(plan)
    if request.source != 'approved_execution_spec':
        raise GovApiError('raw_intent_runner_request_not_allowed')
    if not request.approved_execution_spec:
        raise GovApiError('missing_approved_execution_spec')
    if supervision.request_id != request.request_id:
        raise GovApiError('supervision_request_mismatch')
    if not request.dry_run and not supervision.live_backend_enabled:
        raise GovApiError('live_backend_disabled')
    return request


def validate_runner_receipt_for_request(
    request: GovRunnerRequest,
    receipt: GovRunnerReceipt | Mapping[str, Any] | None,
) -> GovRunnerReceipt:
    if receipt is None:
        raise GovApiError('missing_runner_receipt')
    item = receipt if isinstance(receipt, GovRunnerReceipt) else _receipt_from_mapping(receipt)
    if item.request_id != request.request_id:
        raise GovApiError('runner_receipt_request_mismatch')
    if item.binding.present and item.binding.request_id and item.binding.request_id != request.request_id:
        raise GovApiError('runner_receipt_binding_request_mismatch')
    requested_indices = {step.index for step in request.steps}
    result_indices = {result.index for result in item.step_results}
    if not result_indices <= requested_indices:
        raise GovApiError('runner_receipt_step_mismatch')
    return item


def supervision_plan_from_runner_request(
    request: GovRunnerRequest,
    *,
    plan_id: str = '',
    runner_profile: str = 'dry-run',
    live_backend_enabled: bool = False,
    timeout_seconds: int = 30,
    cwd_policy: str = 'none',
    env_policy: str = 'empty',
    stdin_policy: str = 'bounded',
    metadata: Mapping[str, Any] | None = None,
) -> GovSupervisionPlan:
    return validate_supervision_plan(GovSupervisionPlan(
        plan_id=plan_id or f'{request.request_id}:supervision',
        request_id=request.request_id,
        runner_profile=runner_profile,
        dry_run=request.dry_run,
        live_backend_enabled=live_backend_enabled,
        timeout_seconds=timeout_seconds,
        cwd_policy=cwd_policy,
        env_policy=env_policy,
        stdin_policy=stdin_policy,
        receipt_required=True,
        metadata=_metadata(metadata),
    ))


def runner_lease_from_request(
    request: GovRunnerRequest,
    *,
    lease_id: str = '',
    runner_profile: str = 'dry-run',
    expires_at: str = '',
    metadata: Mapping[str, Any] | None = None,
) -> GovRunnerLease:
    return validate_runner_lease(GovRunnerLease(
        lease_id=lease_id or f'{request.request_id}:lease',
        request_id=request.request_id,
        runner_profile=runner_profile,
        state='active',
        expires_at=expires_at,
        metadata=_metadata(metadata),
    ))


def _receipt_from_mapping(value: Mapping[str, Any]) -> GovRunnerReceipt:
    from govengine.execution.runner_protocol import GovRunnerStepResult

    raw = require_mapping(value, reason_code='invalid_runner_receipt')
    return GovRunnerReceipt(
        status=str(raw.get('status') or '').strip(),
        request_id=str(raw.get('request_id') or '').strip(),
        source=str(raw.get('source') or '').strip(),
        reason_code=str(raw.get('reason_code') or 'ok').strip() or 'ok',
        step_results=tuple(
            GovRunnerStepResult(
                index=_int(item.get('index'), -1),
                status=str(item.get('status') or '').strip(),
                returncode=_int(item.get('returncode'), 0),
                stdout=str(item.get('stdout') or ''),
                stderr=str(item.get('stderr') or ''),
                reason_code=str(item.get('reason_code') or 'ok').strip() or 'ok',
            )
            for item in list(raw.get('step_results') or ())
            if isinstance(item, Mapping)
        ),
        control_decisions=tuple(dict(item) for item in list(raw.get('control_decisions') or ()) if isinstance(item, Mapping)),
        binding=raw.get('binding') if isinstance(raw.get('binding'), Mapping) else {},
    )


def _enum(value: Any, allowed: tuple[str, ...], default: str) -> str:
    normalized = str(value or '').strip().lower() or default
    return normalized if normalized in allowed else default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _metadata(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise GovApiError('invalid_supervision_metadata')
    data = dict(value)
    _reject_forbidden_metadata(data)
    return data


def _reject_forbidden_metadata(value: Mapping[str, Any]) -> None:
    reason = _find_forbidden_key(value)
    if reason:
        raise GovApiError(f'forbidden_supervision_metadata:{reason}')


def _find_forbidden_key(value: Any) -> str:
    if isinstance(value, Mapping):
        forbidden = set(FORBIDDEN_SUPERVISION_METADATA_KEYS)
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
