"""GovEngine package-in-place seam for Ravenclaw extraction.

This package exposes neutral context, policy, runner, and safety-control
contracts without importing optional contract-lifecycle dependencies at package
import time.
"""

__version__ = '0.1.1'

from .api import GovApiError, GovApiResult
from .context import GovEngineContext, GovEnginePaths, ravenclaw_context
from .execution_backend import CommandResult, GovExecutionBackend
from .ooda import GovObservation, GovOodaController, GovOodaDecision, GovOrientation
from .roles import GovRoleAdapters
from .scope import FunctionalScopePort, GovScopePort
from .state_store import GovStateStore

__all__ = [
    'CommandResult',
    'GovApiError',
    'GovApiResult',
    'GovEngineContext',
    'GovEnginePaths',
    'GovExecutionBackend',
    'GovObservation',
    'GovOodaController',
    'GovOodaDecision',
    'GovOrientation',
    'GovRoleAdapters',
    'FunctionalScopePort',
    'GovScopePort',
    'GovSCLiteLifecycleVerifier',
    'GovStateStore',
    'ravenclaw_context',
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
