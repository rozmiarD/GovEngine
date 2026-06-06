from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ADMISSION = ROOT / 'docs' / 'RUNTIME_ADMISSION.md'
README = ROOT / 'README.md'
API_BOUNDARY = ROOT / 'docs' / 'API_BOUNDARY.md'
ADMISSION_POLICY = ROOT / 'docs' / 'ADMISSION_POLICY.md'


def test_runtime_admission_design_names_required_inputs_and_outputs() -> None:
    text = RUNTIME_ADMISSION.read_text(encoding='utf-8')
    for marker in (
        'RuntimeAdmissionResult',
        'GovernedExecutionAdmission',
        'prepared_execution_contract',
        'policy_decision',
        'execution_ticket',
        'trust_decision',
        'sclite_guarded_strict',
        'replay_freshness',
        'runner_profile',
        'receipt_obligation',
        'artifact_refs',
        'status',
        'allowed',
        'reason_code',
        'blockers',
        'required_next_actions',
    ):
        assert marker in text


def test_runtime_admission_design_preserves_host_and_sclite_boundaries() -> None:
    text = RUNTIME_ADMISSION.read_text(encoding='utf-8')
    normalized = ' '.join(text.split())
    for marker in (
        'Intent is not execution authority',
        'SCLite owns schemas',
        'duplicate SCLite canonicalization',
        'review-bundle authority',
        'Hosts own profile/domain policy meaning',
        'production key storage',
        'PKI/KMS/CA',
        'raw evidence storage',
        'live execution',
        'backends',
        'must not claim production runtime readiness',
    ):
        assert marker in normalized


def test_runtime_admission_design_is_linked_from_public_docs() -> None:
    for path in (README, API_BOUNDARY, ADMISSION_POLICY):
        text = path.read_text(encoding='utf-8')
        assert 'RUNTIME_ADMISSION.md' in text
