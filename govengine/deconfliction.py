from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

from govengine.core import ArtifactState, ReasonCode


@dataclass(frozen=True)
class ArtifactConflict:
    """Portable artifact conflict/deconfliction finding."""

    role: str
    reason_code: str
    message: str
    expected_digest: str = ""
    actual_digest: str = ""
    upstream_role: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "role": self.role,
            "reason_code": self.reason_code,
            "message": self.message,
            "expected_digest": self.expected_digest,
            "actual_digest": self.actual_digest,
            "upstream_role": self.upstream_role,
        }


@dataclass(frozen=True)
class ArtifactChangeOrder:
    """Actionable summary for resolving artifact conflicts."""

    conflicts: tuple[ArtifactConflict, ...] = ()
    required_actions: tuple[str, ...] = ()
    invalidated_roles: tuple[str, ...] = ()

    @property
    def required(self) -> bool:
        return bool(self.conflicts)

    def as_dict(self) -> dict[str, object]:
        return {
            "required": self.required,
            "conflicts": [conflict.as_dict() for conflict in self.conflicts],
            "required_actions": list(self.required_actions),
            "invalidated_roles": list(self.invalidated_roles),
        }


@dataclass(frozen=True)
class ConflictDetector:
    """Detect digest/state conflicts without owning SCLite verification."""

    downstream_roles: Mapping[str, tuple[str, ...]] = field(default_factory=lambda: {
        "intent_contract": ("policy_decision", "execution_contract", "execution_ticket", "execution_receipt", "evidence_contract", "artifact_chain_manifest"),
        "policy_decision": ("execution_contract", "execution_ticket", "execution_receipt", "evidence_contract", "artifact_chain_manifest"),
        "execution_contract": ("execution_ticket", "execution_receipt", "evidence_contract", "artifact_chain_manifest"),
        "execution_ticket": ("execution_receipt", "evidence_contract", "artifact_chain_manifest"),
        "execution_receipt": ("evidence_contract", "artifact_chain_manifest"),
        "evidence_contract": ("artifact_chain_manifest",),
    })

    def detect_digest_conflicts(
        self,
        artifact_states: Sequence[ArtifactState],
        *,
        expected_digests: Mapping[str, str],
    ) -> tuple[ArtifactConflict, ...]:
        conflicts: list[ArtifactConflict] = []
        for state in artifact_states:
            role = state.descriptor.role or state.descriptor.artifact_type
            expected = str(expected_digests.get(role) or "")
            actual = state.descriptor.digest
            if expected and expected != actual:
                conflicts.append(ArtifactConflict(
                    role=role,
                    reason_code="artifact_digest_mismatch",
                    message=f"{role} digest does not match expected binding",
                    expected_digest=expected,
                    actual_digest=actual,
                ))
            for reason in state.blocked_reasons:
                conflicts.append(ArtifactConflict(
                    role=role,
                    reason_code=ReasonCode.LIFECYCLE_BLOCKED.value,
                    message=str(reason),
                    actual_digest=actual,
                ))
        return tuple(conflicts)

    def change_order_for_conflicts(self, conflicts: Sequence[ArtifactConflict]) -> ArtifactChangeOrder:
        actions: list[str] = []
        invalidated: list[str] = []
        for conflict in conflicts:
            actions.append(f"repair_artifact:{conflict.role}")
            if conflict.reason_code == "artifact_digest_mismatch":
                actions.append(f"rebuild_bindings_for:{conflict.role}")
            for downstream in self.downstream_roles.get(conflict.role, ()):
                invalidated.append(downstream)
                actions.append(f"revalidate_artifact:{downstream}")
        return ArtifactChangeOrder(
            conflicts=tuple(conflicts),
            required_actions=tuple(dict.fromkeys(actions)),
            invalidated_roles=tuple(dict.fromkeys(invalidated)),
        )

    def evaluate(
        self,
        artifact_states: Sequence[ArtifactState],
        *,
        expected_digests: Mapping[str, str] | None = None,
    ) -> ArtifactChangeOrder:
        conflicts = self.detect_digest_conflicts(artifact_states, expected_digests=expected_digests or {})
        return self.change_order_for_conflicts(conflicts)
