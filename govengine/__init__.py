"""GovEngine package-in-place seam for Ravenclaw extraction.

This package exposes neutral context, policy, runner, and safety-control
contracts without importing optional contract-lifecycle dependencies at package
import time.
"""

__version__ = '0.1.4'

from .api import GovApiError, GovApiResult
from .context import GovEngineContext, GovEnginePaths, ravenclaw_context
from .core import (
    ArtifactDescriptor,
    ArtifactEnvelope,
    ArtifactState,
    ExecutionPrerequisites,
    GovernanceContext,
    ReasonCode,
    TransitionDecision,
)
from .deconfliction import ArtifactChangeOrder, ArtifactConflict, ConflictDetector
from .execution.gate import DryRunRunner, ExecutionGate, ExecutionGateInput, RunnerProfile
from .execution_backend import CommandResult, GovExecutionBackend
from .lifecycle import ArtifactLifecycleController, TransitionGate, TransitionPolicy
from .ooda import GovObservation, GovOodaController, GovOodaDecision, GovOrientation
from .roles import GovRoleAdapters
from .scope import FunctionalScopePort, GovScopePort
from .signing import SignatureEnvelope, SigningPolicy, TrustPolicy, VerificationResult
from .state_index import ArtifactStateIndex
from .state_store import GovStateStore
from .surfaces import GovSurface, public_surface_index, security_profile_surface

__all__ = [
    'CommandResult',
    'GovApiError',
    'GovApiResult',
    'GovEngineContext',
    'GovEnginePaths',
    'ArtifactChangeOrder',
    'ArtifactConflict',
    'ArtifactDescriptor',
    'ArtifactEnvelope',
    'ArtifactLifecycleController',
    'ArtifactState',
    'ArtifactStateIndex',
    'ConflictDetector',
    'ExecutionGate',
    'ExecutionGateInput',
    'ExecutionPrerequisites',
    'DryRunRunner',
    'GovernanceContext',
    'GovExecutionBackend',
    'GovObservation',
    'GovOodaController',
    'GovOodaDecision',
    'GovOrientation',
    'GovRoleAdapters',
    'GovSurface',
    'FunctionalScopePort',
    'ReasonCode',
    'RunnerProfile',
    'GovScopePort',
    'SignatureEnvelope',
    'SigningPolicy',
    'GovSCLiteLifecycleVerifier',
    'GovStateStore',
    'TransitionDecision',
    'TransitionGate',
    'TransitionPolicy',
    'TrustPolicy',
    'VerificationResult',
    'public_surface_index',
    'ravenclaw_context',
    'security_profile_surface',
    'verify_lifecycle_manifest',
]


def __getattr__(name: str):
    if name in {'GovSCLiteLifecycleVerifier', 'verify_lifecycle_manifest'}:
        from .sclite_contracts import GovSCLiteLifecycleVerifier, verify_lifecycle_manifest

        return {
            'GovSCLiteLifecycleVerifier': GovSCLiteLifecycleVerifier,
            'verify_lifecycle_manifest': verify_lifecycle_manifest,
        }[name]
    raise AttributeError(name)


from .action_schema import *  # noqa: F401,F403,E402
