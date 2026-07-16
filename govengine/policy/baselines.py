from __future__ import annotations

from copy import deepcopy
import json
from typing import Any

from govengine.api import GovApiError


BASELINE_POLICY_NAMES = (
    'readonly',
    'mutating-approval',
    'destructive-deny',
    'bounded-output',
    'governed-runtime',
)


_BASELINES: dict[str, dict[str, Any]] = {
    'readonly': {
        'policy_id': 'govengine-readonly-baseline',
        'version': 'v0.1',
        'rules': [
            {
                'rule_id': 'allow-read-with-receipt',
                'effect': 'allow_with_obligations',
                'conditions': {'action.mode': 'read'},
                'reason_code': 'read_allowed_with_receipt',
                'obligations': [{'obligation_id': 'receipt-required', 'kind': 'receipt'}],
                'constraints': [
                    {'constraint_id': 'read-only', 'kind': 'read_only_required', 'value': True},
                    {'constraint_id': 'no-shell', 'kind': 'no_raw_shell', 'value': True},
                ],
            },
            {
                'rule_id': 'allow-observe-with-receipt',
                'effect': 'allow_with_obligations',
                'conditions': {'action.mode': 'observe'},
                'reason_code': 'observe_allowed_with_receipt',
                'obligations': [{'obligation_id': 'receipt-required', 'kind': 'receipt'}],
                'constraints': [
                    {'constraint_id': 'read-only', 'kind': 'read_only_required', 'value': True},
                    {'constraint_id': 'no-shell', 'kind': 'no_raw_shell', 'value': True},
                ],
            },
        ],
        'metadata': {
            'source': 'govengine.policy.baselines',
            'boundary': 'governance_only_no_execution',
        },
    },
    'mutating-approval': {
        'policy_id': 'govengine-mutating-approval-baseline',
        'version': 'v0.1',
        'rules': [
            {
                'rule_id': 'require-approval-for-mutating',
                'effect': 'approval_required',
                'conditions': {'action.mode': 'mutating'},
                'reason_code': 'mutating_action_requires_approval',
                'risk_class': 'high',
                'risk_score': 0.8,
                'constraints': [
                    {
                        'constraint_id': 'mutation-approval',
                        'kind': 'mutation_requires_approval',
                        'value': True,
                    },
                ],
            },
            {
                'rule_id': 'require-approval-for-apply',
                'effect': 'approval_required',
                'conditions': {'action.mode': 'apply'},
                'reason_code': 'apply_action_requires_approval',
                'risk_class': 'high',
                'risk_score': 0.8,
                'constraints': [
                    {
                        'constraint_id': 'mutation-approval',
                        'kind': 'mutation_requires_approval',
                        'value': True,
                    },
                ],
            },
        ],
        'metadata': {
            'source': 'govengine.policy.baselines',
            'boundary': 'operator_approval_evidence_required',
        },
    },
    'destructive-deny': {
        'policy_id': 'govengine-destructive-deny-baseline',
        'version': 'v0.1',
        'rules': [
            {
                'rule_id': 'deny-destructive-action',
                'effect': 'deny',
                'conditions': {'action.destructive': True},
                'reason_code': 'destructive_action_denied',
                'risk_class': 'critical',
                'risk_score': 1.0,
            },
            {
                'rule_id': 'deny-unsafe-execution-shape',
                'effect': 'deny',
                'conditions': {'action.unsafe_execution_shape': True},
                'reason_code': 'unsafe_execution_shape',
                'risk_class': 'critical',
                'risk_score': 1.0,
            },
        ],
        'metadata': {
            'source': 'govengine.policy.baselines',
            'boundary': 'fail_closed_no_runtime_authority',
        },
    },
    'bounded-output': {
        'policy_id': 'govengine-bounded-output-baseline',
        'version': 'v0.1',
        'rules': [
            {
                'rule_id': 'allow-read-with-bounded-output',
                'effect': 'allow_with_obligations',
                'conditions': {'action.mode': 'read'},
                'reason_code': 'read_allowed_with_bounded_output',
                'obligations': [{'obligation_id': 'receipt-required', 'kind': 'receipt'}],
                'constraints': [
                    {'constraint_id': 'bounded-output', 'kind': 'output_limit', 'value': 65536},
                    {'constraint_id': 'digest-output', 'kind': 'output_digest_required', 'value': True},
                    {'constraint_id': 'no-shell', 'kind': 'no_raw_shell', 'value': True},
                    {
                        'constraint_id': 'network-egress',
                        'kind': 'allowed_network_egress',
                        'value': [
                            'local_subprocess',
                            'no_network',
                            'outbound_http',
                            'outbound_ssh',
                        ],
                    },
                ],
            },
        ],
        'metadata': {
            'source': 'govengine.policy.baselines',
            'boundary': 'bounded_receipt_refs_not_raw_evidence_storage',
        },
    },
}


def available_baseline_policy_names() -> tuple[str, ...]:
    return BASELINE_POLICY_NAMES


def baseline_policy_pack(
    name: str,
    *,
    policy_id: str = '',
    version: str = '',
) -> dict[str, Any]:
    normalized = str(name or '').strip()
    if normalized == 'governed-runtime':
        pack = _governed_runtime_baseline()
    else:
        template = _BASELINES.get(normalized)
        if template is None:
            raise GovApiError(f'unknown_policy_baseline:{normalized or "missing"}')
        pack = deepcopy(template)
    if policy_id:
        pack['policy_id'] = str(policy_id)
    if version:
        pack['version'] = str(version)
    return pack


def _governed_runtime_baseline() -> dict[str, Any]:
    rules: list[dict[str, Any]] = []
    seen: set[str] = set()
    predicates: dict[str, dict[str, Any]] = {}
    for name in ('destructive-deny', 'readonly', 'bounded-output', 'mutating-approval'):
        for rule in _BASELINES[name]['rules']:
            rule_id = str(rule['rule_id'])
            if rule_id in seen:
                continue
            copied = deepcopy(rule)
            predicate = json.dumps(
                copied.get('conditions') or {},
                sort_keys=True,
                separators=(',', ':'),
            )
            existing = predicates.get(predicate)
            if existing is not None and existing.get('effect') == copied.get('effect'):
                _merge_rule_controls(existing, copied)
                seen.add(rule_id)
                continue
            rules.append(copied)
            predicates[predicate] = copied
            seen.add(rule_id)
    return {
        'policy_id': 'govengine-governed-runtime-baseline',
        'version': 'v0.1',
        'rules': rules,
        'metadata': {
            'source': 'govengine.policy.baselines',
            'boundary': 'govengine_governance_validation_enforcement_only',
            'truth_layer': 'SCLite',
            'execution_layer': 'RExecOp_or_host_runtime',
        },
    }


def _merge_rule_controls(target: dict[str, Any], source: dict[str, Any]) -> None:
    for field_name, id_key in (
        ('obligations', 'obligation_id'),
        ('constraints', 'constraint_id'),
    ):
        target_items = list(target.get(field_name) or [])
        by_id = {str(item[id_key]): item for item in target_items}
        for item in source.get(field_name) or []:
            item_id = str(item[id_key])
            previous = by_id.get(item_id)
            if previous is not None and previous != item:
                raise GovApiError('conflicting_policy_controls')
            if previous is None:
                copied = deepcopy(item)
                target_items.append(copied)
                by_id[item_id] = copied
        target[field_name] = target_items
