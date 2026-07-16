from __future__ import annotations

from scripts.validate_workflow_security import validate_workflow_security


def test_workflows_pin_actions_and_use_oidc_release_security() -> None:
    report = validate_workflow_security()

    assert report['workflows'] == 3
    assert report['actions'] == 17
