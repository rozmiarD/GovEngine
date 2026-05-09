from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

from govengine.core import ArtifactState
from govengine.deconfliction import ArtifactChangeOrder, ConflictDetector


@dataclass(frozen=True)
class ArtifactStateIndex:
    """Lightweight common operational picture for governed artifacts."""

    states_by_role: Mapping[str, ArtifactState] = field(default_factory=dict)
    change_order: ArtifactChangeOrder = field(default_factory=ArtifactChangeOrder)

    @classmethod
    def from_states(
        cls,
        states: Sequence[ArtifactState],
        *,
        expected_digests: Mapping[str, str] | None = None,
        detector: ConflictDetector | None = None,
    ) -> "ArtifactStateIndex":
        states_by_role = {
            state.descriptor.role or state.descriptor.artifact_type: state
            for state in states
        }
        detector = detector or ConflictDetector()
        return cls(
            states_by_role=states_by_role,
            change_order=detector.evaluate(tuple(states_by_role.values()), expected_digests=expected_digests or {}),
        )

    def missing_roles(self, required_roles: Sequence[str]) -> tuple[str, ...]:
        return tuple(role for role in required_roles if role not in self.states_by_role)

    def blocked_roles(self) -> tuple[str, ...]:
        return tuple(role for role, state in self.states_by_role.items() if state.blocked)

    def next_actions(self, required_roles: Sequence[str] = ()) -> tuple[str, ...]:
        actions: list[str] = []
        for role in self.missing_roles(required_roles):
            actions.append(f"provide_artifact:{role}")
        for role, state in self.states_by_role.items():
            if state.blocked:
                actions.extend(state.next_actions or (f"repair_artifact:{role}",))
        actions.extend(self.change_order.required_actions)
        return tuple(dict.fromkeys(actions))

    def summary(self, required_roles: Sequence[str] = ()) -> dict[str, object]:
        missing = self.missing_roles(required_roles)
        blocked = self.blocked_roles()
        return {
            "status": "blocked" if missing or blocked or self.change_order.required else "ready",
            "artifact_count": len(self.states_by_role),
            "roles": sorted(self.states_by_role.keys()),
            "missing_roles": list(missing),
            "blocked_roles": list(blocked),
            "change_order_required": self.change_order.required,
            "invalidated_roles": list(self.change_order.invalidated_roles),
            "next_actions": list(self.next_actions(required_roles)),
        }

    def as_dict(self) -> dict[str, object]:
        return {
            "states": {role: state.as_dict() for role, state in self.states_by_role.items()},
            "change_order": self.change_order.as_dict(),
        }
