from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROADMAP_DIR = ROOT / 'docs' / 'roadmaps'
BODY_DIR = ROADMAP_DIR / 'ge-issue-bodies'
CONTRACT = ROADMAP_DIR / 'GE-TASK-CONTRACT.md'
MANIFEST = ROADMAP_DIR / 'ge-governed-runtime-kernel-mvp-seed-manifest.json'


def test_remaining_ge_task_bodies_reference_central_contract() -> None:
    contract_text = CONTRACT.read_text(encoding='utf-8')

    assert 'GE Task Contract v1' in contract_text
    assert 'Use Signposter as the workflow control plane.' in contract_text
    assert 'PR bodies and comments must not use auto-close keywords.' in contract_text
    assert 'Return to the DAG next task after side-task completion.' in contract_text

    for number in range(31, 46):
        body = (BODY_DIR / f'GE-{number:03d}.md').read_text(encoding='utf-8')
        assert 'Task contract: GE-TASK-CONTRACT v1' in body
        assert 'Contract path: `docs/roadmaps/GE-TASK-CONTRACT.md`' in body
        assert 'Signposter status:' not in body
        assert 'Implementation guidance:' not in body
        assert len(body) < 3200


def test_seed_manifest_tracks_ge_031a_side_task_and_compact_body_sizes() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    issues = {item['key']: item for item in manifest['issues']}

    side_task = issues['GE-031A']
    assert side_task['side_task'] is True
    assert side_task['parent'] == 30
    assert side_task['return_to'] == 31
    assert side_task['github_issue'] == 75

    for number in range(31, 46):
        key = f'GE-{number:03d}'
        body = (BODY_DIR / f'{key}.md').read_text(encoding='utf-8')
        body_size = issues[key]['body_size']
        assert body_size['char_count'] == len(body)
        assert body_size['line_count'] == len(body.splitlines())
        assert body_size['char_count'] < 3200
