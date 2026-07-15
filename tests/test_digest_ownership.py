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
    assert inventory['runner.execution_ticket'].mode == 'delegated'
    assert inventory['replay.root_chain'].owner == 'sclite'


def test_digest_ownership_never_recomputes_sclite_payloads() -> None:
    inventory = validate_digest_ownership_inventory()

    assert all(not (item.owner == 'sclite' and item.mode == 'recomputed') for item in inventory)
