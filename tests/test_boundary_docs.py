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
