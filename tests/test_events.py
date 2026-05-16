from __future__ import annotations

import pytest

from govengine import EventEnvelope, GovEvent, validate_event_envelope, validate_gov_event
from govengine.api import GovApiError


def test_gov_event_is_json_safe_metadata_record() -> None:
    event = validate_gov_event({
        'event_type': 'runner_receipt_recorded',
        'subject': 'receipt-1',
        'profile': 'ravenclaw',
        'refs': ['ticket-1', 'decision-1'],
        'payload': {'receipt_status': 'dry-run', 'reason_code': 'ok'},
    })

    assert isinstance(event, GovEvent)
    assert event.as_dict() == {
        'event_type': 'runner_receipt_recorded',
        'subject': 'receipt-1',
        'status': 'recorded',
        'profile': 'ravenclaw',
        'refs': ['ticket-1', 'decision-1'],
        'payload': {'receipt_status': 'dry-run', 'reason_code': 'ok'},
    }


def test_event_envelope_is_transport_neutral() -> None:
    envelope = validate_event_envelope({
        'event': {
            'event_type': 'profile_handoff_requested',
            'subject': 'handoff-1',
            'payload': {'target_profile': 'ravenclaw'},
        },
        'source': 'host_runtime',
        'correlation_id': 'corr-1',
        'sequence': 3,
        'metadata': {'trace_ref': 'trace-1'},
    })

    assert isinstance(envelope, EventEnvelope)
    assert envelope.as_dict()['event']['event_type'] == 'profile_handoff_requested'
    assert envelope.as_dict()['correlation_id'] == 'corr-1'
    assert envelope.as_dict()['sequence'] == 3


def test_gov_event_rejects_unknown_event_type() -> None:
    with pytest.raises(GovApiError, match='unknown_event_type:scheduled_job_started'):
        validate_gov_event({
            'event_type': 'scheduled_job_started',
            'subject': 'job-1',
        })


def test_gov_event_rejects_raw_prompt_payload() -> None:
    with pytest.raises(GovApiError, match='forbidden_event_payload:prompt'):
        validate_gov_event({
            'event_type': 'ooda_control_decision_recorded',
            'subject': 'decision-1',
            'payload': {'prompt': 'decide what to run next'},
        })


def test_event_envelope_rejects_credentials_and_live_commands() -> None:
    with pytest.raises(GovApiError, match='forbidden_event_payload:credential'):
        validate_event_envelope({
            'event': {
                'event_type': 'artifact_state_changed',
                'subject': 'artifact-1',
            },
            'metadata': {'nested': {'credential': 'secret-value'}},
        })

    with pytest.raises(GovApiError, match='forbidden_event_payload:command'):
        validate_gov_event({
            'event_type': 'runner_receipt_recorded',
            'subject': 'receipt-2',
            'payload': {'command': ['curl', 'https://example.com']},
        })


def test_event_envelope_rejects_delivery_or_schedule_claims() -> None:
    with pytest.raises(GovApiError, match='event_envelope_must_not_claim_delivery_or_schedule'):
        validate_event_envelope({
            'event': {
                'event_type': 'policy_decision_recorded',
                'subject': 'policy-1',
            },
            'schedule': {'kind': 'cron'},
        })
