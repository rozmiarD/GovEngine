from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ADMISSION = ROOT / 'docs' / 'RUNTIME_ADMISSION.md'
INSPECT_ONLY_ADMISSION_WORKFLOW = ROOT / 'docs' / 'INSPECT_ONLY_ADMISSION_WORKFLOW.md'
README = ROOT / 'README.md'
API_BOUNDARY = ROOT / 'docs' / 'API_BOUNDARY.md'
ADMISSION_POLICY = ROOT / 'docs' / 'ADMISSION_POLICY.md'
VALIDATION = ROOT / 'docs' / 'VALIDATION.md'


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


def test_inspect_only_admission_workflow_design_names_required_surface() -> None:
    text = INSPECT_ONLY_ADMISSION_WORKFLOW.read_text(encoding='utf-8')

    for marker in (
        'RuntimeAdmissionResult',
        'validate_runtime_admission_result()',
        'status',
        'allowed',
        'reason_code',
        'blockers',
        'required next actions',
        'receipt obligation',
        'artifact references or digests',
        'execution: not performed',
    ):
        assert marker in text


def test_inspect_only_admission_workflow_preserves_boundaries() -> None:
    text = INSPECT_ONLY_ADMISSION_WORKFLOW.read_text(encoding='utf-8')
    normalized = ' '.join(text.split())

    for marker in (
        'Intent is not execution authority',
        'read-only',
        'must not execute live work',
        'No future flag may grant execution authority',
        'SCLite remains the authority',
        'Hosts remain the authority',
        'no live subprocess runner',
        'no runner request creation',
        'no receipt creation',
        'no replay claim mutation',
        'no audit ledger append',
        'no raw evidence loading',
    ):
        assert marker in normalized


def test_inspect_only_admission_workflow_is_linked_from_runtime_docs() -> None:
    runtime_text = RUNTIME_ADMISSION.read_text(encoding='utf-8')
    validation_text = VALIDATION.read_text(encoding='utf-8')

    assert 'INSPECT_ONLY_ADMISSION_WORKFLOW.md' in runtime_text
    assert 'inspect-only admission workflow' in validation_text
