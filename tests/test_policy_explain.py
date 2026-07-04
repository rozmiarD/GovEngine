from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from govengine import PolicyCompiler, explain_policy_evaluation

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "govengine_policy.py"


def _pack(*, unsupported: bool = False):
    obligations = [{"obligation_id": "receipt", "kind": "receipt_required"}]
    constraints = [{"constraint_id": "output", "kind": "output_limit", "value": 4096}]
    if unsupported:
        obligations.append({"obligation_id": "vendor", "kind": "vendor_specific"})
        constraints.append({"constraint_id": "region", "kind": "vendor_region", "value": "x"})
    result = PolicyCompiler().compile(
        {
            "policy_id": "explain-policy",
            "version": "v1",
            "rules": [
                {
                    "rule_id": "deny-unsafe-mode",
                    "effect": "deny",
                    "priority": 10,
                    "conditions": {"action.mode": "unsafe"},
                    "reason_code": "unsafe_mode_denied",
                    "risk_class": "critical",
                    "risk_score": 1.0,
                },
                {
                    "rule_id": "allow-read",
                    "effect": "allow",
                    "priority": 20,
                    "conditions": {"action.mode": "read"},
                    "reason_code": "read_allowed",
                    "risk_class": "low",
                    "risk_score": 0.1,
                },
                {
                    "rule_id": "allow-bounded-write",
                    "effect": "allow_with_obligations",
                    "priority": 30,
                    "conditions": {"action.mode": "bounded_write"},
                    "reason_code": "bounded_write_allowed",
                    "obligations": obligations,
                    "constraints": constraints,
                    "risk_class": "medium",
                    "risk_score": 0.5,
                },
            ],
        }
    )
    assert result.policy_pack is not None
    return result.policy_pack


def _request(mode: str, *, criticality: str = "low") -> dict[str, object]:
    return {
        "request_id": f"request-{mode}",
        "subject_ref": f"artifact://task/{mode}",
        "action": {"mode": mode},
        "resource": {"criticality": criticality},
    }


def test_policy_explain_allow_matched_rule_is_redacted() -> None:
    explanation = explain_policy_evaluation(_request("read"), _pack()).as_dict()

    assert explanation["status"] == "explained"
    assert explanation["decision"] == "allow"
    assert explanation["evaluation_path"] == "matched_rule"
    assert explanation["matched_rule"]["rule_id"] == "allow-read"
    assert explanation["matched_rule"]["conditions"] == [
        {"key": "action.mode", "matched": True, "redacted": True}
    ]
    assert explanation["projected_controls"]["receipt_required"] is True
    assert "expected" not in json.dumps(explanation["rule_evaluations"])
    assert "actual" not in json.dumps(explanation["rule_evaluations"])


def test_policy_explain_deny_matched_rule_is_blocked() -> None:
    explanation = explain_policy_evaluation(_request("unsafe"), _pack()).as_dict()

    assert explanation["status"] == "blocked"
    assert explanation["decision"] == "deny"
    assert explanation["reason_code"] == "unsafe_mode_denied"
    assert explanation["matched_rule"]["rule_id"] == "deny-unsafe-mode"
    assert explanation["blockers"] == ["unsafe_mode_denied"]


def test_policy_explain_no_matching_rule() -> None:
    explanation = explain_policy_evaluation(_request("observe"), _pack()).as_dict()

    assert explanation["status"] == "blocked"
    assert explanation["decision"] == "deny"
    assert explanation["evaluation_path"] == "no_match"
    assert explanation["matched_rule"] == {}
    assert explanation["blockers"] == ["no_matching_policy_rule"]


def test_policy_explain_approval_required_invariant() -> None:
    explanation = explain_policy_evaluation(
        _request("mutating", criticality="critical"),
        _pack(),
    ).as_dict()

    assert explanation["status"] == "blocked"
    assert explanation["decision"] == "approval_required"
    assert explanation["evaluation_path"] == "invariant"
    assert explanation["invariant"]["reason_code"] == "critical_mutating_action_requires_approval"
    assert explanation["blockers"] == [
        "operator_approval_required",
        "critical_mutating_action_requires_approval",
    ]


def test_policy_explain_allow_with_obligations_and_projected_controls() -> None:
    explanation = explain_policy_evaluation(_request("bounded_write"), _pack()).as_dict()

    assert explanation["status"] == "explained"
    assert explanation["decision"] == "allow_with_obligations"
    assert explanation["matched_rule"]["rule_id"] == "allow-bounded-write"
    assert explanation["obligations"] == [
        {"obligation_id": "receipt", "kind": "receipt_required", "supported": True}
    ]
    assert explanation["constraints"] == [
        {"constraint_id": "output", "kind": "output_limit", "supported": True}
    ]
    assert explanation["projected_controls"]["max_output_bytes"] == 4096
    assert explanation["enforcement_plan"]["status"] == "ready"


def test_policy_explain_unsupported_controls_fail_closed() -> None:
    explanation = explain_policy_evaluation(
        _request("bounded_write"),
        _pack(unsupported=True),
    ).as_dict()

    assert explanation["status"] == "blocked"
    assert explanation["decision"] == "allow_with_obligations"
    assert "unsupported_policy_obligation:vendor_specific" in explanation["unsupported_controls"]
    assert "unsupported_policy_constraint:vendor_region" in explanation["unsupported_controls"]
    assert explanation["enforcement_plan"]["status"] == "blocked"
    assert explanation["blockers"] == ["unsupported_policy_obligation:vendor_specific"]


def test_policy_cli_explain_outputs_stable_json(tmp_path: Path) -> None:
    policy_path = tmp_path / "policy.json"
    request_path = tmp_path / "request.json"
    policy_path.write_text(json.dumps(_pack().as_dict()), encoding="utf-8")
    request_path.write_text(json.dumps(_request("read")), encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "explain",
            str(policy_path),
            str(request_path),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(proc.stdout)
    assert payload["schema_version"] == "v0.1"
    assert payload["status"] == "explained"
    assert payload["decision"] == "allow"
    assert payload["matched_rule"]["rule_id"] == "allow-read"
    assert payload["non_claims"] == [
        "Does not execute work.",
        "Does not approve operators or run approval workflow.",
        "Does not verify SCLite artifacts or host enforcement.",
        "Does not expose raw request payload values.",
    ]


def test_policy_cli_simulate_alias_outputs_same_json(tmp_path: Path) -> None:
    policy_path = tmp_path / "policy.json"
    request_path = tmp_path / "request.json"
    policy_path.write_text(json.dumps(_pack().as_dict()), encoding="utf-8")
    request_path.write_text(json.dumps(_request("read")), encoding="utf-8")

    explain = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "explain",
            str(policy_path),
            str(request_path),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    simulate = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "simulate",
            str(policy_path),
            str(request_path),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert json.loads(simulate.stdout) == json.loads(explain.stdout)
