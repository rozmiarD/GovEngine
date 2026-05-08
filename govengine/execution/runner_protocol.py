from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Protocol, Sequence

from govengine.api import GovApiError
from govengine.execution.approved_spec import approved_execution_steps


@dataclass(frozen=True)
class GovRunnerStep:
    """A normalized, carrier-neutral execution step."""

    index: int
    tool: str
    args: tuple[str, ...] = ()
    stdin: str = ""

    def as_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["args"] = list(self.args)
        return out


@dataclass(frozen=True)
class GovRunnerRequest:
    """The bounded request a host runner may execute or dry-run."""

    request_id: str
    source: str
    steps: tuple[GovRunnerStep, ...]
    approved_execution_spec: Mapping[str, Any] = field(default_factory=dict)
    execution_ticket_gate: Mapping[str, Any] = field(default_factory=dict)
    dry_run: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "source": self.source,
            "steps": [step.as_dict() for step in self.steps],
            "approved_execution_spec": dict(self.approved_execution_spec),
            "execution_ticket_gate": dict(self.execution_ticket_gate),
            "dry_run": self.dry_run,
        }


@dataclass(frozen=True)
class GovRunnerStepResult:
    index: int
    status: str
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""
    reason_code: str = "ok"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GovRunnerReceipt:
    status: str
    request_id: str
    source: str
    step_results: tuple[GovRunnerStepResult, ...] = ()
    reason_code: str = "ok"
    control_decisions: tuple[Mapping[str, Any], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "request_id": self.request_id,
            "source": self.source,
            "reason_code": self.reason_code,
            "step_results": [result.as_dict() for result in self.step_results],
            "control_decisions": [dict(decision) for decision in self.control_decisions],
        }


class GovRunner(Protocol):
    """Host-provided runner port.

    GovEngine prepares and validates the request shape. The host owns concrete
    IO/subprocess behavior and must honor returned control decisions.
    """

    def run(self, request: GovRunnerRequest) -> GovRunnerReceipt:
        ...


def normalize_runner_steps(raw_steps: Sequence[Mapping[str, Any]]) -> tuple[GovRunnerStep, ...]:
    steps: list[GovRunnerStep] = []
    for idx, raw_step in enumerate(raw_steps):
        if not isinstance(raw_step, Mapping):
            raise GovApiError("invalid_runner_step", f"index={idx}")
        tool = str(raw_step.get("tool") or "").strip()
        if not tool:
            raise GovApiError("missing_runner_step_tool", f"index={idx}")
        raw_args = raw_step.get("args") or []
        if not isinstance(raw_args, Sequence) or isinstance(raw_args, (str, bytes)):
            raise GovApiError("invalid_runner_step_args", f"index={idx}")
        steps.append(GovRunnerStep(
            index=idx,
            tool=tool,
            args=tuple(str(arg) for arg in raw_args),
            stdin=str(raw_step.get("stdin") or ""),
        ))
    if not steps:
        raise GovApiError("missing_runner_steps")
    return tuple(steps)


def runner_request_from_approved_spec(
    approved_execution_spec: Mapping[str, Any],
    *,
    request_id: str = "approved-spec-request",
    execution_ticket_gate: Mapping[str, Any] | None = None,
    dry_run: bool = True,
) -> GovRunnerRequest:
    raw_steps = approved_execution_steps(dict(approved_execution_spec))
    return GovRunnerRequest(
        request_id=str(request_id or "approved-spec-request"),
        source="approved_execution_spec",
        steps=normalize_runner_steps(raw_steps),
        approved_execution_spec=dict(approved_execution_spec),
        execution_ticket_gate=dict(execution_ticket_gate or {"status": "not_required"}),
        dry_run=bool(dry_run),
    )


def dry_run_runner_receipt(request: GovRunnerRequest) -> GovRunnerReceipt:
    return GovRunnerReceipt(
        status="dry-run",
        request_id=request.request_id,
        source=request.source,
        step_results=tuple(
            GovRunnerStepResult(index=step.index, status="dry-run", reason_code="dry_run_requested")
            for step in request.steps
        ),
        reason_code="dry_run_requested",
    )
