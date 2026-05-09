from __future__ import annotations

from govengine.contracts.analysis import build_analysis_contract
from govengine.contracts.evidence_policy import can_be_confirmed
from govengine.contracts.signal import build_signal_contract, signal_contract_signal_positive


def test_weak_actionable_signal_bridge_marks_signal_positive_but_not_high_signal() -> None:
    contract = build_signal_contract(
        engine_status='success',
        auditor_decision='approve',
        success_eval_status='partial',
        qual={'verdict': 'none', 'confidence': 0.0, 'false_positive_guards_passed': True},
        signal_assessment={
            'heuristic_promising': False,
            'signal_positive': True,
            'workflow_promotable': False,
            'adaptation_positive': False,
            'host_promise_positive': False,
            'qualification_threshold': 'probable',
        },
        runtime_decision={'requested_action': '', 'selected_primary_action': ''},
        summary_text='Redirect baseline',
        reason_code='engine_success',
        control_cmp={'performed': False, 'control_delta_observed': False, 'reason': 'tool_not_supported'},
        metrics_obj={'code': 307},
        success_semantics={},
        weak_signal_positive_bridge_enabled=True,
    )

    assert contract['schema_version'] == 'p5-v1'
    assert contract['finding_signal']['status'] == 'weak'
    assert contract['legacy_bridges']['weak_actionable_signal'] is True
    assert contract['legacy_bridges']['signal_positive'] is True
    assert contract['legacy_bridges']['high_signal'] is False
    assert signal_contract_signal_positive(contract) is True
    assert contract['adaptation_feedback']['status'] == 'positive'
    assert contract['adaptation_feedback']['planner_reconsult_worthy'] is True


def test_signal_contract_carries_governance_blocked_qualification_disposition() -> None:
    contract = build_signal_contract(
        engine_status='blocked',
        auditor_decision='owner_approval_required',
        success_eval_status='not_met',
        qual={'verdict': 'weak_signal', 'confidence': 0.29, 'disposition': 'governance_blocked'},
        signal_assessment={'qualification_threshold': 'probable', 'workflow_promotable': False, 'signal_positive': True},
        runtime_decision={},
        summary_text='Blocked by policy before confirmatory execution',
        reason_code='auditor_owner_approval_required',
        control_cmp={},
        metrics_obj={'code': 403},
        success_semantics={},
    )

    assert contract['workflow_promotion']['qualification_disposition'] == 'governance_blocked'
    assert contract['finding_signal']['evidence_class'] == 'blocked_evidence'
    assert 'qualification_disposition:governance_blocked' in contract['finding_signal']['evidence']


def test_confirmed_requires_repro_and_controls() -> None:
    qualification = {
        'verdict': 'confirmed',
        'false_positive_guards_passed': True,
        'observed_artifacts': {
            'control_comparison_performed': True,
            'control_delta_observed': True,
            'protocol': {'repro_pass': True},
        },
    }

    assert can_be_confirmed(qualification) is True


def test_confirmed_blocked_without_repro() -> None:
    qualification = {
        'verdict': 'confirmed',
        'false_positive_guards_passed': True,
        'observed_artifacts': {
            'control_comparison_performed': True,
            'control_delta_observed': True,
            'protocol': {'repro_pass': False},
        },
    }

    assert can_be_confirmed(qualification) is False



def test_confirmed_rejects_malformed_observed_artifacts() -> None:
    assert can_be_confirmed({'verdict': 'confirmed', 'false_positive_guards_passed': True, 'observed_artifacts': []}) is False


def test_signal_contract_handles_nonnumeric_http_code() -> None:
    contract = build_signal_contract(
        engine_status='success',
        auditor_decision='approve',
        success_eval_status='partial',
        qual={'verdict': 'weak_signal'},
        signal_assessment={'signal_positive': True},
        runtime_decision={},
        metrics_obj={'code': 'not-a-code'},
    )

    assert contract['legacy_bridges']['interesting_http_signal'] is False

def test_build_analysis_contract_maps_success_semantics() -> None:
    contract = build_analysis_contract(
        result={
            'brain': {
                'action_type': 'differential_probe',
                'hypothesis': 'authz delta exists',
                'expected_signal': 'status/header delta',
                'evidence_goal': 'confirm authz asymmetry',
                'planner_alignment': 'aligned',
                'redundancy_risk': 'low',
            },
            'engine_compiler': {
                'semantic_loss_detected': False,
                'compiler_strategy': 'differential_lowering',
                'compiler_variant_count': 2,
            },
            'success_criteria': {
                'typed_family_eval': 'authz_boundary',
                'gap': 'need_clear_allow_deny_or_boundary_evidence',
                'evidence': ['engine_ok'],
                'success_model': 'differential_or_stateful_signal',
                'expected_signal_type': 'behavior_delta',
                'evidence_goal_type': 'controlled_comparison',
                'required_evidence_hits': ['http_status'],
            },
        },
        task_ctx={
            'task_family': 'authz',
            'success_semantics': {
                'success_model': 'differential_or_stateful_signal',
                'expected_signal_type': 'behavior_delta',
                'evidence_goal_type': 'controlled_comparison',
            },
        },
        success_eval_status='partial',
        engine_status='ok',
    )

    assert contract['action_type'] == 'differential_probe'
    assert contract['expected_signal_observed'] == 'partial'
    assert contract['evidence_goal_met'] == 'partial'
    assert contract['hypothesis_support'] == 'inconclusive'
    assert contract['semantic_execution_fit'] == 'exact'
    assert contract['semantic_loss_class'] == 'none'
    assert contract['semantic_loss_policy_response'] == 'proceed'
    assert contract['approved_under_degradation'] is False
    assert contract['typed_family_eval'] == 'authz_boundary'
    assert contract['success_gap'] == 'need_clear_allow_deny_or_boundary_evidence'
    assert contract['success_evidence'] == ['engine_ok']
