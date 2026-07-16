from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = ROOT / '.github' / 'workflows'
FULL_SHA = re.compile(r'^[0-9a-f]{40}$')
USES = re.compile(r'^\s*-\s+uses:\s+([^@\s]+)@([^\s#]+)', re.MULTILINE)


def validate_workflow_security() -> dict[str, int]:
    workflows = sorted(WORKFLOW_ROOT.glob('*.yml'))
    if not workflows:
        raise AssertionError('workflow_security_missing_workflows')
    action_count = 0
    for path in workflows:
        text = path.read_text(encoding='utf-8')
        for action, reference in USES.findall(text):
            action_count += 1
            if not FULL_SHA.fullmatch(reference):
                raise AssertionError(
                    f'workflow_action_not_pinned:{path.name}:{action}@{reference}'
                )

    security = (WORKFLOW_ROOT / 'security.yml').read_text(encoding='utf-8')
    for marker in (
        'python -m pip_audit --strict .',
        'github/codeql-action/init@',
        'github/codeql-action/analyze@',
        'security-events: write',
    ):
        if marker not in security:
            raise AssertionError(f'workflow_security_missing:{marker}')

    publish = (WORKFLOW_ROOT / 'publish.yml').read_text(encoding='utf-8')
    for marker in (
        'workflow_dispatch:',
        'environment:',
        'name: pypi',
        'id-token: write',
        'attestations: write',
        'actions/attest-build-provenance@',
        'pypa/gh-action-pypi-publish@',
        'python scripts/validate_rc_window.py',
        'if [[ "$PACKAGE_VERSION" == *rc* ]]',
        'python scripts/validate_rc_window.py --require-completed',
        'python scripts/validate_release_readiness.py',
        'python scripts/validate_v1_security_review.py --require-independent',
        'test "$GITHUB_REF_TYPE" = "tag"',
        'tag_version_mismatch',
    ):
        if marker not in publish:
            raise AssertionError(f'workflow_publish_missing:{marker}')
    if 'password:' in publish or 'api-token:' in publish or 'skip-existing:' in publish:
        raise AssertionError('workflow_publish_long_lived_or_unsafe_upload_setting')
    return {
        'workflows': len(workflows),
        'actions': action_count,
    }


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser().parse_args(argv)
    report = validate_workflow_security()
    print(
        'workflow_security_ok:'
        f"workflows={report['workflows']}:actions={report['actions']}"
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
