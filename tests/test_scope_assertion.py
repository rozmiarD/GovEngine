from govengine import build_scope_assertion, build_scope_decision, scope_decision_digest


def test_scope_decision_binds_admission_subject_and_target() -> None:
    decision = build_scope_decision(
        admission={"details": {"admission_id": "adm-1"}},
        operation_id="op-1",
        target="env/host-1",
        target_host="host-1",
        in_scope=True,
    )
    assertion = build_scope_assertion(decision)

    assert decision["decision_ref"] == "govengine-scope:adm-1"
    assert assertion["status"] == "in_scope"
    assert assertion["subject"] == {"operation_id": "op-1"}
    assert assertion["target"] == {"target": "env/host-1", "target_host": "host-1"}
    assert assertion["decision_digest"] == scope_decision_digest(decision)


def test_scope_decision_digest_changes_across_target() -> None:
    first = build_scope_decision(
        admission={}, operation_id="op-1", target="env/a", target_host="a", in_scope=True
    )
    second = build_scope_decision(
        admission={}, operation_id="op-1", target="env/b", target_host="b", in_scope=True
    )

    assert scope_decision_digest(first) != scope_decision_digest(second)
