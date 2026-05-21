from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from types import ModuleType
from typing import Any, Dict, Iterable, Tuple

from .surfaces import GovSurface, security_profile_surface


@dataclass(frozen=True)
class SecurityProfileGroup:
    """Named group inside GovEngine's optional security compatibility surface.

    The security profile is a migration convenience entrypoint for hosts such as
    Ravenclaw. It does not make the grouped helpers part of the neutral
    artifact-governance core and it intentionally does not import Ravenclaw
    runtime code.
    """

    name: str
    modules: Tuple[str, ...]
    claim: str
    non_claims: Tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'modules': list(self.modules),
            'claim': self.claim,
            'non_claims': list(self.non_claims),
        }


def _tuple(values: Iterable[str]) -> Tuple[str, ...]:
    return tuple(str(value) for value in values)


_SECURITY_PROFILE_GROUPS: Tuple[SecurityProfileGroup, ...] = (
    SecurityProfileGroup(
        name='action_tooling',
        modules=_tuple((
            'govengine.action_schema',
            'govengine.action_validators',
            'govengine.action_compiler',
            'govengine.capability_recipes',
            'govengine.tool_registry',
            'govengine.semantic_loss_policy',
        )),
        claim='Security-oriented action shape, capability, tool, and semantic-loss helpers.',
        non_claims=_tuple((
            'scanner implementation',
            'live exploit capability',
            'target authorization',
        )),
    ),
    SecurityProfileGroup(
        name='policy_scope',
        modules=_tuple((
            'govengine.policy.core',
            'govengine.policy.gateway',
            'govengine.scope',
        )),
        claim='Reusable policy gateway and scope-port helpers for host-owned security workflows.',
        non_claims=_tuple((
            'host policy source-of-truth ownership',
            'bug-bounty campaign orchestration',
            'operator approval workflow ownership',
        )),
    ),
    SecurityProfileGroup(
        name='review_contracts',
        modules=_tuple((
            'govengine.contracts.signal',
            'govengine.contracts.analysis',
            'govengine.contracts.evidence_policy',
        )),
        claim='Signal, analysis, and confirmation-evidence policy contracts for reviewable outcomes.',
        non_claims=_tuple((
            'raw evidence storage',
            'Logdash projection ownership',
            'finding publication or disclosure authority',
        )),
    ),
)


def security_profile_groups() -> Tuple[SecurityProfileGroup, ...]:
    """Return the tested group map for optional compatibility helpers."""

    return _SECURITY_PROFILE_GROUPS


def security_profile_module_names() -> Tuple[str, ...]:
    """Return the complete module list for the optional compatibility surface."""

    return security_profile_surface().modules


def security_profile_index() -> Dict[str, Any]:
    """Return a JSON-safe index for the optional compatibility entrypoint."""

    surface = security_profile_surface()
    return {
        'entrypoint': 'govengine.security_profile',
        'surface': surface.as_dict(),
        'groups': [group.as_dict() for group in security_profile_groups()],
    }


def import_security_profile_module(module_name: str) -> ModuleType:
    """Import one allowed optional security-profile module by fully qualified name.

    This is deliberately allowlisted by the public surface registry. It is a host
    convenience for one-entrypoint discovery, not dynamic loading of arbitrary
    GovEngine or Ravenclaw modules.
    """

    normalized = str(module_name)
    allowed = set(security_profile_module_names())
    if normalized not in allowed:
        raise KeyError(normalized)
    return import_module(normalized)


def assert_security_profile_boundary(surface: GovSurface | None = None) -> None:
    """Raise AssertionError if the optional profile is mixed with core/adapter claims."""

    candidate = surface or security_profile_surface()
    assert candidate.name == 'security_profile_helpers'
    assert candidate.optional_profile is True
    forbidden_modules = {
        'govengine.core',
        'govengine.sclite_contracts',
        'govengine.lifecycle',
        'govengine.signing',
        'govengine.execution.gate',
        'govengine.execution.runner',
    }
    assert forbidden_modules.isdisjoint(set(candidate.modules))
    forbidden_claim_fragments = (
        'live exploit',
        'authorization to test targets',
        'OpenClaw/MCP/A2A adapter ownership',
    )
    non_claims = ' '.join(candidate.non_claims)
    for fragment in forbidden_claim_fragments:
        assert fragment in non_claims
