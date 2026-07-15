from __future__ import annotations

from govengine._digest_ownership import validate_digest_ownership_inventory


def test_digest_ownership_inventory_covers_critical_boundaries() -> None:
    inventory = {item.binding_id: item for item in validate_digest_ownership_inventory()}

    assert inventory['typed_execution.capability_descriptor'].mode == 'recomputed'
    assert inventory['runner.request'].mode == 'recomputed'
    assert inventory['runner.receipt'].mode == 'recomputed'
    assert inventory['runner.runtime_admission'].mode == 'recomputed'
    assert inventory['audit.record'].mode == 'recomputed'
    assert inventory['audit.ledger_entry'].mode == 'recomputed'
    assert inventory['governance_request.policy_pack'].mode == 'recomputed'
    assert inventory['governance_request.execution_facts'].mode == 'recomputed'
    assert inventory['governance_request.requested_scope'].mode == 'recomputed'
    assert inventory['governance_request.approval_attestation'].mode == 'recomputed'
    assert inventory['approval.subject'].mode == 'recomputed'
    assert inventory['governance_request.scope_policy_binding'].mode == 'recomputed'
    assert inventory['governance_request.capability_requirements'].mode == 'recomputed'
    assert inventory['governance_request.capability_inventory'].mode == 'recomputed'
    assert inventory['governance_request.execution_spec'].mode == 'reference_only'
    assert inventory['governance_request.fencing_token'].owner == 'rexecop'
    assert inventory['scope_policy.decision'].mode == 'produced'
    assert inventory['capability.compatibility_decision'].mode == 'produced'
    assert inventory['runner.execution_ticket'].mode == 'delegated'
    assert inventory['replay.root_chain'].owner == 'sclite'


def test_digest_ownership_never_recomputes_sclite_payloads() -> None:
    inventory = validate_digest_ownership_inventory()

    assert all(not (item.owner == 'sclite' and item.mode == 'recomputed') for item in inventory)
