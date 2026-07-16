from __future__ import annotations

from typing import Any, Mapping, Sequence

from govengine.api import GovApiError
from govengine.policy.compiler import PolicyCompiler


def migrate_policy_pack_v0_1_to_v1(
    policy_pack: Mapping[str, Any],
    *,
    issuer_ref: str,
    policy_epoch: int,
    not_before: str,
    expires_at: str,
    supersedes: Sequence[str] = (),
) -> dict[str, Any]:
    """Normalize one legacy equality-map pack into a typed v1 candidate.

    Trust and activation facts are mandatory caller inputs. The helper does
    not activate the result, sign it, select a trust root, or invent validity.
    """

    compiler = PolicyCompiler()
    source = compiler.compile(policy_pack)
    if not source.ok or source.policy_pack is None:
        raise GovApiError(
            'policy_migration_source_invalid',
            context={'source_reason_code': source.reason_code},
        )
    if source.policy_pack.schema_version != 'v0.1':
        raise GovApiError('policy_migration_source_schema_mismatch')

    candidate = source.policy_pack.as_dict()
    candidate.update(
        {
            'schema_version': 'v1',
            'issuer_ref': issuer_ref,
            'policy_epoch': policy_epoch,
            'validity': {
                'not_before': not_before,
                'expires_at': expires_at,
            },
            'supersedes': list(supersedes),
            'rules': [
                rule.as_dict(schema_version='v1')
                for rule in source.policy_pack.rules
            ],
        }
    )
    migrated = compiler.compile(candidate)
    if not migrated.ok or migrated.policy_pack is None:
        raise GovApiError(
            'policy_migration_target_invalid',
            context={'target_reason_code': migrated.reason_code},
        )
    return migrated.policy_pack.as_dict()
