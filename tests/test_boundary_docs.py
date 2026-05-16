from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_kernel_boundary_doc_tracks_machine_readable_contract() -> None:
    text = (ROOT / 'docs' / 'GOVENGINE_KERNEL_BOUNDARY.md').read_text(encoding='utf-8')

    assert 'govengine.boundary.kernel_boundary_report()' in text
    assert 'Owned By GovEngine' in text
    assert 'Owned By Profiles' in text
    assert 'Owned By Runtimes' in text
    assert 'Owned By SCLite' in text
    assert 'live target authorization' in text
    assert 'carrier adapter ownership' in text


def test_domain_profile_contract_doc_tracks_conformance_contract() -> None:
    text = (ROOT / 'docs' / 'DOMAIN_PROFILE_CONTRACT.md').read_text(encoding='utf-8')

    assert 'DomainProfileContract' in text
    assert 'validate_domain_profile_conformance()' in text
    assert 'govengine_controlled_execution_core' in text
    assert 'sclite_review_bundles' in text
    assert 'live_execution_authority' in text
    assert 'Tecrax' in text


def test_orchestrator_model_doc_tracks_runtime_non_claims() -> None:
    text = (ROOT / 'docs' / 'ORCHESTRATOR_MODEL.md').read_text(encoding='utf-8')

    assert 'orchestrator_boundary_contract()' in text
    assert 'validate_orchestration_step()' in text
    assert 'workflow scheduler' in text
    assert 'credential store' in text
    assert 'live executor' in text
    assert 'raw_intent' in text


def test_event_model_doc_tracks_payload_boundaries() -> None:
    text = (ROOT / 'docs' / 'EVENT_MODEL.md').read_text(encoding='utf-8')

    assert 'GovEvent' in text
    assert 'EventEnvelope' in text
    assert 'validate_event_envelope()' in text
    assert 'raw intent or prompts' in text
    assert 'credentials, secrets, tokens' in text
    assert 'live commands' in text
    assert 'carrier delivery' in text


def test_state_machine_doc_tracks_runtime_non_claims() -> None:
    text = (ROOT / 'docs' / 'STATE_MACHINE.md').read_text(encoding='utf-8')

    assert 'GovRunState' in text
    assert 'StateTransition' in text
    assert 'validate_state_transition()' in text
    assert 'runtime storage paths' in text
    assert 'queues, schedulers, or schedules' in text
    assert 'live execution' in text
    assert 'does not write to disk' in text


def test_control_model_doc_tracks_between_step_boundaries() -> None:
    text = (ROOT / 'docs' / 'CONTROL_MODEL.md').read_text(encoding='utf-8')

    assert 'ControlDecision' in text
    assert 'validate_control_decision()' in text
    assert 'apply_control_decision()' in text
    assert 'raw intent or prompts' in text
    assert 'commands, subprocesses, or shells' in text
    assert 'queues, schedulers, or schedules' in text
    assert 'does not write to disk' in text


def test_validation_doc_tracks_unreleased_0_2_boundary_line() -> None:
    text = (ROOT / 'docs' / 'VALIDATION.md').read_text(encoding='utf-8')

    assert 'current unreleased 0.2 kernel-boundary line' in text
    assert 'govengine.boundary' in text
    assert 'govengine.orchestration' in text
    assert 'govengine.events' in text
    assert 'govengine.state_machine' in text
    assert 'govengine.control' in text
    assert 'no queue, scheduler, carrier adapter, credential store' in text
    assert 'live execution authority is introduced' in text
