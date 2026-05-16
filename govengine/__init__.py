"""GovEngine package-in-place seam for Ravenclaw extraction.

This package exposes neutral context, policy, runner, and safety-control
contracts without importing optional contract-lifecycle dependencies at package
import time.
"""

__version__ = '0.1.7'

from .api import GovApiError, GovApiResult
from .boundary import (
    BoundaryReport,
    DomainProfileConformance,
    DomainProfileContract,
    KernelBoundary,
    boundary_surface_index,
    domain_profile_conformance,
    kernel_boundary_contract,
    kernel_boundary_report,
    known_profile_contracts,
    ravenclaw_profile_contract,
    validate_domain_profile_contract,
    validate_domain_profile_conformance,
)
from .context import GovEngineContext, GovEnginePaths, ravenclaw_context
from .control import ControlDecision, apply_control_decision, validate_control_decision
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
from .events import EventEnvelope, GovEvent, validate_event_envelope, validate_gov_event
from .execution.gate import DryRunRunner, ExecutionGate, ExecutionGateInput, RunnerProfile
from .execution_backend import CommandResult, GovExecutionBackend
from .lifecycle import ArtifactLifecycleController, TransitionGate, TransitionPolicy
from .ooda import GovObservation, GovOodaController, GovOodaDecision, GovOrientation
from .orchestration import (
    OrchestrationStep,
    OrchestratorBoundary,
    orchestrator_boundary_contract,
    validate_orchestration_step,
)
from .roles import GovRoleAdapters
from .scope import FunctionalScopePort, GovScopePort
from .signing import DemoDigestSigner, DemoDigestVerifier, SignatureEnvelope, SigningPolicy, TrustPolicy, VerificationResult, demo_sign_and_verify
from .state_index import ArtifactStateIndex
from .state_machine import (
    GovRunState,
    StateTransition,
    apply_state_transition,
    validate_run_state,
    validate_state_transition,
)
from .state_store import GovStateStore
from .security_profile import (
    SecurityProfileGroup,
    assert_security_profile_boundary,
    import_security_profile_module,
    security_profile_groups,
    security_profile_index,
    security_profile_module_names,
)
from .surfaces import GovSurface, public_surface_index, security_profile_surface

__all__ = [
    'CommandResult',
    'BoundaryReport',
    'ControlDecision',
    'DomainProfileConformance',
    'DomainProfileContract',
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
    'EventEnvelope',
    'DryRunRunner',
    'DemoDigestSigner',
    'DemoDigestVerifier',
    'GovernanceContext',
    'GovExecutionBackend',
    'GovEvent',
    'GovObservation',
    'GovOodaController',
    'GovOodaDecision',
    'GovOrientation',
    'GovRoleAdapters',
    'GovRunState',
    'GovSurface',
    'KernelBoundary',
    'OrchestrationStep',
    'OrchestratorBoundary',
    'SecurityProfileGroup',
    'FunctionalScopePort',
    'ReasonCode',
    'RunnerProfile',
    'GovScopePort',
    'SignatureEnvelope',
    'SigningPolicy',
    'StateTransition',
    'GovSCLiteLifecycleVerifier',
    'GovStateStore',
    'review_bundle_state',
    'review_bundle_transition_decision',
    'review_sclite_bundle',
    'TransitionDecision',
    'TransitionGate',
    'TransitionPolicy',
    'TrustPolicy',
    'VerificationResult',
    'apply_control_decision',
    'demo_sign_and_verify',
    'apply_state_transition',
    'assert_security_profile_boundary',
    'boundary_surface_index',
    'domain_profile_conformance',
    'import_security_profile_module',
    'kernel_boundary_contract',
    'kernel_boundary_report',
    'known_profile_contracts',
    'orchestrator_boundary_contract',
    'public_surface_index',
    'ravenclaw_context',
    'ravenclaw_profile_contract',
    'security_profile_groups',
    'security_profile_index',
    'security_profile_module_names',
    'security_profile_surface',
    'validate_domain_profile_contract',
    'validate_domain_profile_conformance',
    'validate_control_decision',
    'validate_event_envelope',
    'validate_gov_event',
    'validate_orchestration_step',
    'validate_run_state',
    'validate_state_transition',
    'verify_lifecycle_manifest',
]


def __getattr__(name: str):
    if name in {
        'GovSCLiteLifecycleVerifier',
        'review_bundle_state',
        'review_bundle_transition_decision',
        'review_sclite_bundle',
        'verify_lifecycle_manifest',
    }:
        from .sclite_contracts import (
            GovSCLiteLifecycleVerifier,
            review_bundle_state,
            review_bundle_transition_decision,
            review_sclite_bundle,
            verify_lifecycle_manifest,
        )

        return {
            'GovSCLiteLifecycleVerifier': GovSCLiteLifecycleVerifier,
            'review_bundle_state': review_bundle_state,
            'review_bundle_transition_decision': review_bundle_transition_decision,
            'review_sclite_bundle': review_sclite_bundle,
            'verify_lifecycle_manifest': verify_lifecycle_manifest,
        }[name]
    raise AttributeError(name)


from .action_schema import *  # noqa: F401,F403,E402
