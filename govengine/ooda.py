from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence

_ALLOWED_DECISIONS = {
    "continue",
    "pause",
    "abort",
    "cooldown",
    "degrade_to_dry_run",
    "require_owner_review",
    "replan_after_step",
}


@dataclass(frozen=True)
class GovObservation:
    """Normalized observation emitted before/between runner steps."""

    kind: str
    severity: str = "info"
    subject: str = ""
    detail: str = ""
    facts: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GovOrientation:
    """Policy/context interpretation of observations."""

    scope_ok: bool = True
    policy_ok: bool = True
    ticket_ok: bool = True
    spec_ok: bool = True
    host_health: str = "ok"
    output_shape: str = "expected"
    operator_control: str = "run"
    budget_state: str = "ok"
    notes: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["notes"] = list(self.notes)
        return out


@dataclass(frozen=True)
class GovOodaDecision:
    decision: str
    reason_code: str = "ok"
    detail: str = ""
    cooldown_subject: str = ""
    observations: tuple[GovObservation, ...] = ()
    orientation: GovOrientation = field(default_factory=GovOrientation)

    def __post_init__(self) -> None:
        if self.decision not in _ALLOWED_DECISIONS:
            raise ValueError(f"invalid_ooda_decision:{self.decision}")

    @property
    def interrupting(self) -> bool:
        return self.decision in {"pause", "abort", "cooldown", "degrade_to_dry_run", "require_owner_review"}

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "reason_code": self.reason_code,
            "detail": self.detail,
            "cooldown_subject": self.cooldown_subject,
            "interrupting": self.interrupting,
            "observations": [observation.as_dict() for observation in self.observations],
            "orientation": self.orientation.as_dict(),
        }


class GovOodaController:
    """Deterministic policy-first OODA safety controller.

    The controller does not run tools and does not ask an LLM for safety
    decisions. It converts normalized observations and orientation into a
    control decision that host runners/adapters can honor.
    """

    def decide(
        self,
        *,
        observations: Sequence[GovObservation | Mapping[str, Any]] = (),
        orientation: GovOrientation | Mapping[str, Any] | None = None,
    ) -> GovOodaDecision:
        normalized_observations = tuple(_normalize_observation(item) for item in observations)
        oriented = _normalize_orientation(orientation)

        if oriented.operator_control == "stop":
            return _decision("abort", "operator_stop_requested", observations=normalized_observations, orientation=oriented)
        if oriented.operator_control == "pause":
            return _decision("pause", "operator_pause_requested", observations=normalized_observations, orientation=oriented)
        if not oriented.scope_ok:
            return _decision("abort", "scope_drift_detected", observations=normalized_observations, orientation=oriented)
        if not oriented.policy_ok:
            return _decision("require_owner_review", "policy_mismatch", observations=normalized_observations, orientation=oriented)
        if not oriented.ticket_ok or not oriented.spec_ok:
            return _decision("require_owner_review", "ticket_or_spec_mismatch", observations=normalized_observations, orientation=oriented)
        if oriented.budget_state in {"exhausted", "stop_loss"}:
            return _decision("pause", f"budget_{oriented.budget_state}", observations=normalized_observations, orientation=oriented)
        if oriented.host_health in {"cooldown", "high_fail_rate", "transport_noise"}:
            subject = _first_subject(normalized_observations)
            return _decision("cooldown", f"host_health_{oriented.host_health}", cooldown_subject=subject, observations=normalized_observations, orientation=oriented)
        if oriented.output_shape in {"unexpected", "untrusted", "raw_leak_risk"}:
            return _decision("degrade_to_dry_run", f"output_shape_{oriented.output_shape}", observations=normalized_observations, orientation=oriented)

        for observation in normalized_observations:
            severity = observation.severity.lower()
            kind = observation.kind.lower()
            if severity == "critical":
                return _decision("abort", f"critical_observation:{kind}", observations=normalized_observations, orientation=oriented)
            if severity == "warning" and kind in {"scope_drift", "policy_mismatch", "ticket_mismatch"}:
                return _decision("require_owner_review", f"warning_observation:{kind}", observations=normalized_observations, orientation=oriented)
            if kind in {"transport_anomaly", "host_cooldown"}:
                return _decision("cooldown", f"observation:{kind}", cooldown_subject=observation.subject, observations=normalized_observations, orientation=oriented)
            if kind == "step_completed_with_followup":
                return _decision("replan_after_step", "followup_replan_requested", observations=normalized_observations, orientation=oriented)

        return _decision("continue", "ok", observations=normalized_observations, orientation=oriented)


def _decision(
    decision: str,
    reason_code: str,
    *,
    observations: tuple[GovObservation, ...],
    orientation: GovOrientation,
    detail: str = "",
    cooldown_subject: str = "",
) -> GovOodaDecision:
    return GovOodaDecision(
        decision=decision,
        reason_code=reason_code,
        detail=detail,
        cooldown_subject=cooldown_subject,
        observations=observations,
        orientation=orientation,
    )


def _normalize_observation(value: GovObservation | Mapping[str, Any]) -> GovObservation:
    if isinstance(value, GovObservation):
        return value
    return GovObservation(
        kind=str(value.get("kind") or "unknown"),
        severity=str(value.get("severity") or "info"),
        subject=str(value.get("subject") or ""),
        detail=str(value.get("detail") or ""),
        facts=dict(value.get("facts") or {}) if isinstance(value.get("facts"), Mapping) else {},
    )


def _normalize_orientation(value: GovOrientation | Mapping[str, Any] | None) -> GovOrientation:
    if isinstance(value, GovOrientation):
        return value
    raw = value if isinstance(value, Mapping) else {}
    notes = raw.get("notes") or ()
    return GovOrientation(
        scope_ok=bool(raw.get("scope_ok", True)),
        policy_ok=bool(raw.get("policy_ok", True)),
        ticket_ok=bool(raw.get("ticket_ok", True)),
        spec_ok=bool(raw.get("spec_ok", True)),
        host_health=str(raw.get("host_health") or "ok"),
        output_shape=str(raw.get("output_shape") or "expected"),
        operator_control=str(raw.get("operator_control") or "run"),
        budget_state=str(raw.get("budget_state") or "ok"),
        notes=tuple(str(note) for note in notes),
    )


def _first_subject(observations: tuple[GovObservation, ...]) -> str:
    for observation in observations:
        if observation.subject:
            return observation.subject
    return ""
