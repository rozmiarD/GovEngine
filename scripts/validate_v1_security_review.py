from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = ROOT / 'docs' / 'security-review' / 'v1-contract-review.json'
REVIEW_PACKAGE_PATH = ROOT / 'docs' / 'security-review' / 'v1-review-package.md'
REVIEW_BASELINE_COMMIT = 'bd7ac496006bd8447f6722fb346e0033815aac64'
FULL_SHA = re.compile(r'^[0-9a-f]{40}$')
STATUSES = {'pending_independent_review', 'independent_reviewed'}
SEVERITIES = {'p0', 'p1', 'p2', 'p3', 'informational'}
DISPOSITIONS = {'open', 'fixed', 'accepted_non_blocking', 'not_applicable'}


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AssertionError(f'security_review_duplicate_key:{key}')
        result[key] = value
    return result


def _mapping(value: Any, reason: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AssertionError(reason)
    return value


def validate_v1_security_review(
    path: Path = REVIEW_PATH,
    *,
    require_independent: bool = False,
) -> dict[str, Any]:
    review_package = REVIEW_PACKAGE_PATH.read_text(encoding='utf-8')
    for marker in (
        REVIEW_BASELINE_COMMIT,
        '78676f0d6ecd46011553ce2106dbf4fae5594885',
        '2470373c6384c284ab48df7ce763f0938797d155',
        '0c737c821451489af17e5e1d5a0db0fdd51ee01f',
        'scripts/validate_g6_release_candidate_gate.py',
        'SCLite ownership/freeze and absence of new SCLite contracts',
    ):
        if marker not in review_package:
            raise AssertionError(f'security_review_package_missing:{marker}')
    record = json.loads(
        path.read_text(encoding='utf-8'),
        object_pairs_hook=_strict_object,
        parse_constant=lambda value: (_ for _ in ()).throw(
            AssertionError(f'security_review_non_finite:{value}')
        ),
    )
    checked = _mapping(record, 'security_review_not_mapping')
    required = {
        'schema_version',
        'status',
        'reviewer',
        'reviewed_commit',
        'completed_at',
        'scope',
        'findings',
        'open_p0',
        'open_p1',
        'notes',
    }
    if set(checked) != required:
        raise AssertionError('security_review_fields_drift')
    if checked['schema_version'] != 'govengine.v1_contract_security_review.v1':
        raise AssertionError('security_review_schema_mismatch')
    status = checked['status']
    if status not in STATUSES:
        raise AssertionError('security_review_status_invalid')
    reviewer = _mapping(checked['reviewer'], 'security_review_reviewer_invalid')
    if set(reviewer) != {
        'identity',
        'organization_or_reference',
        'independent_of_implementation',
    }:
        raise AssertionError('security_review_reviewer_fields_drift')
    scope = checked['scope']
    if (
        not isinstance(scope, list)
        or len(scope) < 9
        or any(not isinstance(item, str) or not item for item in scope)
        or len(scope) != len(set(scope))
    ):
        raise AssertionError('security_review_scope_invalid')
    findings = checked['findings']
    if not isinstance(findings, list):
        raise AssertionError('security_review_findings_invalid')
    finding_ids: set[str] = set()
    open_p0 = 0
    open_p1 = 0
    for finding in findings:
        item = _mapping(finding, 'security_review_finding_invalid')
        if set(item) != {'finding_id', 'severity', 'summary', 'disposition'}:
            raise AssertionError('security_review_finding_fields_drift')
        finding_id = item['finding_id']
        if (
            not isinstance(finding_id, str)
            or not finding_id
            or len(finding_id) > 80
            or finding_id in finding_ids
        ):
            raise AssertionError('security_review_finding_id_invalid')
        finding_ids.add(finding_id)
        if not isinstance(item['summary'], str) or not item['summary'].strip():
            raise AssertionError('security_review_finding_summary_invalid')
        if item['severity'] not in SEVERITIES:
            raise AssertionError('security_review_finding_severity_invalid')
        if item['disposition'] not in DISPOSITIONS:
            raise AssertionError('security_review_finding_disposition_invalid')
        if item['disposition'] == 'open' and item['severity'] == 'p0':
            open_p0 += 1
        if item['disposition'] == 'open' and item['severity'] == 'p1':
            open_p1 += 1
    if checked['open_p0'] != open_p0 or checked['open_p1'] != open_p1:
        raise AssertionError('security_review_open_count_drift')
    if not isinstance(checked['notes'], str):
        raise AssertionError('security_review_notes_invalid')

    independent = (
        status == 'independent_reviewed'
        and reviewer.get('independent_of_implementation') is True
        and isinstance(reviewer.get('identity'), str)
        and bool(str(reviewer.get('identity')).strip())
        and isinstance(reviewer.get('organization_or_reference'), str)
        and bool(str(reviewer.get('organization_or_reference')).strip())
        and isinstance(checked['reviewed_commit'], str)
        and bool(FULL_SHA.fullmatch(checked['reviewed_commit']))
        and checked['reviewed_commit'] == REVIEW_BASELINE_COMMIT
        and _aware_timestamp(checked['completed_at'])
        and open_p0 == 0
        and open_p1 == 0
    )
    if require_independent and not independent:
        raise AssertionError('independent_v1_security_review_required')
    return {
        'status': status,
        'independent': independent,
        'findings': len(findings),
        'open_p0': open_p0,
        'open_p1': open_p1,
    }


def _aware_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--review', type=Path, default=REVIEW_PATH)
    parser.add_argument('--require-independent', action='store_true')
    args = parser.parse_args(argv)
    report = validate_v1_security_review(
        args.review,
        require_independent=args.require_independent,
    )
    print(
        'v1_security_review_ok:'
        f"status={report['status']}:independent={str(report['independent']).lower()}:"
        f"findings={report['findings']}:open_p0={report['open_p0']}:"
        f"open_p1={report['open_p1']}"
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
