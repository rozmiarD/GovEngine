from __future__ import annotations

import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLISHED_VERSION = '1.0.0rc1'


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding='utf-8')


def _project_version() -> str:
    return str(tomllib.loads(_read('pyproject.toml'))['project']['version'])


def test_current_public_docs_track_package_version() -> None:
    version = _project_version()
    docs = {
        'README.md': _read('README.md'),
        'PUBLIC_STATUS.md': _read('PUBLIC_STATUS.md'),
        'docs/ROADMAP.md': _read('docs/ROADMAP.md'),
        'docs/VALIDATION.md': _read('docs/VALIDATION.md'),
    }

    assert f'govengine=={version}' in docs['docs/ROADMAP.md']
    assert f'govengine=={version}' in docs['PUBLIC_STATUS.md']
    assert f'Expected result for the current `{version}` package line' in docs['docs/VALIDATION.md']
    assert f'Current source/package version: `{version}`' in docs['README.md']
    assert f'Current package pin: `govengine=={version}`' in docs['README.md']
    assert f'python -m pip install govengine=={PUBLISHED_VERSION}' in docs['README.md']
    assert 'Current 0.12.x alpha line' not in docs['docs/ROADMAP.md']
    assert 'published `0.12` alpha line' not in docs['README.md']


def test_readme_is_human_facing_and_describes_the_unnamed_component_set() -> None:
    readme = _read('README.md')

    for marker in (
        'GovEngine is an in-process Python governance kernel designed to be integrated',
        'It does not define artifact truth or verify lifecycle and evidence',
        'This\nset has no formal product name.',
        'Together they separate domain meaning,\ngovernance, execution and proof',
        'Domain profile                 meaning, workflows, connector contracts',
        'RExecOp                        lifecycle, lease/fencing, permit, I/O',
        '+---- request / terminal facts -----> GovEngine',
        '+---- final lifecycle/evidence --------> SCLite',
        '## Canonical governance flow',
        '## What GovEngine provides',
        '## What GovEngine does not do',
        '## Quick start: evaluate a typed policy',
    ):
        assert marker in readme

    for stale in (
        'govstack',
        'The published `0.15.0` line added',
        'The `0.16.x` source line also adds',
        'The published `0.16.0` line adds',
        'public_surface_index()',
        'approved_spec_dry_run_result',
        '## Safety Boundary',
        '## Explicit Non-Claims',
        '```mermaid',
        '```plantuml',
    ):
        assert stale not in readme


def test_archive_keeps_only_compact_release_history() -> None:
    readme = _read('README.md')
    docs_index = _read('docs/README.md')

    archive_names = sorted(path.name for path in (ROOT / 'docs' / 'archive').glob('*.md'))
    assert archive_names == ['ROADMAP_VERSION_HISTORY.md']
    assert 'archive/ROADMAP_VERSION_HISTORY.md' in docs_index
    assert 'docs/archive/' not in readme
    assert 'superseded as the canonical authorization path' in _read(
        'docs/archive/ROADMAP_VERSION_HISTORY.md'
    )


def test_active_docs_track_release_candidate_and_current_stack_ownership() -> None:
    docs = {
        relative: _read(relative)
        for relative in (
            'README.md',
            'SECURITY.md',
            'docs/ADMISSION_POLICY.md',
            'docs/API_BOUNDARY.md',
            'docs/API_COMPATIBILITY.md',
            'docs/API_STABILITY_MATRIX.md',
            'docs/ARCHITECTURE.md',
            'docs/CONTROL_MODEL.md',
            'docs/DOWNSTREAM_IMPORT_MAP.md',
            'docs/GOVENGINE_KERNEL_BOUNDARY.md',
            'docs/ORCHESTRATOR_MODEL.md',
            'docs/ROADMAP.md',
            'docs/RUNTIME_SHELL.md',
            'docs/SCLITE_INTEGRATION.md',
            'docs/STATE_MACHINE.md',
            'docs/VALIDATION.md',
        )
    }
    joined = '\n'.join(docs.values())

    for stale in (
        'GovEngine is still alpha',
        'publication remains blocked by',
        'Before a 0.2 release',
        'reserved name for the future governed infrastructure-operations',
        'input candidates for the replacement flow',
        'until the canonical G2/G3 contracts exist',
        'candidate stable import boundary',
        'Ravenclaw is the full reference runtime/control plane',
        'describes the canonical runtime admission envelope',
        'The replacement G2 flow starts',
        'until the boundary freeze',
        'Current 0.2 boundary work',
        '`govengine.runtime_shell` is the 0.3',
    ):
        assert stale not in joined

    assert 'public `1.0.0rc1` package has\npassed independent contract review' in docs['SECURITY.md']
    assert 'exact 40 exports' in docs['docs/API_COMPATIBILITY.md']
    assert 'RExecOp is the current domain-neutral runtime' in docs['docs/GOVENGINE_KERNEL_BOUNDARY.md']
    assert (
        'Tecrax is a downstream profile, but\n'
        'its current source candidate is not aligned'
    ) in docs['docs/ROADMAP.md']
    assert 'module-scoped terminal-runtime-fact conformance' in docs['docs/ROADMAP.md']
    assert 'for 79 unique import paths' in docs['docs/DOWNSTREAM_IMPORT_MAP.md']
    assert 'RExecOp owns current orchestration mechanics' in docs['docs/ORCHESTRATOR_MODEL.md']
    assert 'RExecOp owns the current operation\nlifecycle' in docs['docs/STATE_MACHINE.md']
    assert 'RExecOp then projects the final' in docs['docs/SCLITE_INTEGRATION.md']
    assert 'SCLite 2.0 is frozen.' in docs['docs/SCLITE_INTEGRATION.md']


def test_docs_pin_canonical_lifecycle_vocabulary_and_legacy_alias_status() -> None:
    docs = '\n'.join((
        _read('README.md'),
        _read('docs/SCLITE_INTEGRATION.md'),
        _read('docs/API_STABILITY_MATRIX.md'),
        _read('docs/VALIDATION.md'),
    ))

    assert 'verified_chain' in docs
    assert 'verified_lifecycle' in docs
    assert 'chain_verified' in docs
    assert 'lifecycle_verified' in docs
    assert 'migration aliases' in docs or 'migration shims' in docs


def test_docs_keep_runtime_shell_projection_separate_from_state_machine() -> None:
    state_machine = _read('docs/STATE_MACHINE.md')
    runtime_shell = _read('docs/RUNTIME_SHELL.md')

    assert 'host projection state only' in state_machine
    assert 'must not be copied into' in state_machine
    assert 'projection states' in runtime_shell
    assert 'running_live' in state_machine
    assert 'running_live' in runtime_shell


def test_docs_classify_contract_proofs_as_conformance_artifacts_not_authority() -> None:
    matrix = _read('docs/API_STABILITY_MATRIX.md')
    boundary = _read('docs/API_BOUNDARY.md')

    assert 'conformance artifacts' in boundary or 'proof fixtures' in boundary
    assert 'fixture' in matrix
    assert 'not production authority' in matrix or 'not production authority' in boundary or 'Non-claims' in boundary


def test_compatibility_docs_do_not_claim_v1_authority() -> None:
    for relative in (
        'docs/ADMISSION_POLICY.md',
        'docs/DOMAIN_PROFILE_CONTRACT.md',
        'docs/EVENT_MODEL.md',
        'docs/EVIDENCE_REVIEW.md',
        'docs/INSPECT_ONLY_ADMISSION_WORKFLOW.md',
        'docs/PROFILE_GOVERNANCE.md',
        'docs/RUNNER_SUPERVISION.md',
        'docs/RUNTIME_ADMISSION.md',
    ):
        text = ' '.join(_read(relative).split()).lower()
        assert 'compatibility' in text, relative
        assert 'outside' in text and '`govengine.v1`' in text, relative


def test_security_docs_pin_canonical_flow_and_malicious_host_non_claim() -> None:
    threat_model = _read('docs/THREAT_MODEL.md')
    guarantees = _read('docs/SECURITY_GUARANTEES.md')
    integration = _read('docs/SECURITY_INTEGRATION.md')
    runtime_admission = _read('docs/RUNTIME_ADMISSION.md')
    receipt_binding = _read('docs/RECEIPT_BINDING.md')

    assert 'malicious or fully compromised in-process host' in threat_model
    assert 'Trusted computing base' in threat_model
    assert 'Cryptographic and digest binding table' in guarantees
    assert 'Explicit non-claims' in guarantees
    assert 'GovernanceRequest v1' in integration
    assert 'atomically claims decision digest and nonce' in integration
    assert 'legacy governed-runtime composition adapter' in runtime_admission
    assert 'canonical v1 attempt path' in receipt_binding
