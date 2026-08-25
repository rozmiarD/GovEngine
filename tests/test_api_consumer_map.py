from __future__ import annotations

from pathlib import Path

import pytest

from scripts.validate_api_stability import (
    consumer_import_map,
    main as validate_api_stability_main,
    validate_api_stability,
)


def _write_consumer(root: Path, *, project: str, source: str) -> None:
    root.mkdir()
    (root / 'pyproject.toml').write_text(
        f'[project]\nname = "{project}"\nversion = "0.0.0"\n',
        encoding='utf-8',
    )
    (root / 'consumer.py').write_text(source, encoding='utf-8')


def test_consumer_import_map_classifies_root_and_deep_imports(tmp_path: Path) -> None:
    source = tmp_path / 'src' / 'consumer.py'
    source.parent.mkdir(parents=True)
    source.write_text(
        '\n'.join(
            (
                'import govengine',
                'from govengine import PolicyEngine, compose_runtime_admission_result',
                'from govengine.governance import requested_scope_digest',
            )
        ),
        encoding='utf-8',
    )

    records = consumer_import_map(tmp_path)
    by_import = {record.import_path: record for record in records}

    assert by_import['govengine.PolicyEngine'].classification == 'v1-candidate'
    assert by_import['govengine.compose_runtime_admission_result'].classification == 'adapter'
    assert by_import['govengine.governance.requested_scope_digest'].classification == 'deep-only'
    assert by_import['govengine'].classification == 'package'


def test_consumer_import_map_is_deterministic(tmp_path: Path) -> None:
    source = tmp_path / 'consumer.py'
    source.write_text('from govengine import PolicyEngine\n', encoding='utf-8')

    assert consumer_import_map(tmp_path) == consumer_import_map(tmp_path)


def test_api_validation_modes_reject_ambiguous_consumer_scope(
    tmp_path: Path,
) -> None:
    rexecop = tmp_path / 'rexecop'
    _write_consumer(
        rexecop,
        project='rexecop',
        source='from govengine import PolicyEngine\n',
    )

    with pytest.raises(
        AssertionError,
        match='api_local_mode_rejects_consumer_roots',
    ):
        validate_api_stability(mode='local', consumer_roots=(rexecop,))
    with pytest.raises(
        AssertionError,
        match='api_cross_repo_consumer_inventory_mismatch',
    ):
        validate_api_stability(mode='cross-repo', consumer_roots=(rexecop,))


def test_cross_repo_api_validation_scans_exact_direct_consumers(
    tmp_path: Path,
) -> None:
    rexecop = tmp_path / 'rexecop'
    tecrax = tmp_path / 'tecrax'
    _write_consumer(
        rexecop,
        project='rexecop',
        source='from govengine import PolicyEngine\n',
    )
    _write_consumer(
        tecrax,
        project='tecrax',
        source='from govengine import GovernanceRequest\n',
    )

    report = validate_api_stability(
        mode='cross-repo',
        consumer_roots=(tecrax, rexecop),
    )

    assert report['mode'] == 'cross-repo'
    assert report['consumer_imports'] == 2


def test_api_stability_cli_requires_explicit_cross_repo_mode(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rexecop = tmp_path / 'rexecop'
    tecrax = tmp_path / 'tecrax'
    _write_consumer(
        rexecop,
        project='rexecop',
        source='from govengine import PolicyEngine\n',
    )
    _write_consumer(
        tecrax,
        project='tecrax',
        source='from govengine import GovernanceRequest\n',
    )
    consumer_args = [
        '--consumer-root',
        str(rexecop),
        '--consumer-root',
        str(tecrax),
    ]

    for local_mode in ([], ['--local']):
        with pytest.raises(
            AssertionError,
            match='api_local_mode_rejects_consumer_roots',
        ):
            validate_api_stability_main([*local_mode, *consumer_args])

    assert validate_api_stability_main(['--cross-repo', *consumer_args]) == 0
    assert capsys.readouterr().out.startswith(
        'api_stability_ok:cross-repo:'
    )


@pytest.mark.parametrize(
    'path',
    (
        'PUBLISHING.md',
        'docs/API_BOUNDARY.md',
        'docs/DOWNSTREAM_IMPORT_MAP.md',
        'docs/VALIDATION.md',
    ),
)
def test_public_consumer_qualification_commands_are_explicit(path: str) -> None:
    text = (Path(__file__).resolve().parents[1] / path).read_text(
        encoding='utf-8'
    )

    assert (
        'scripts/validate_api_stability.py \\\n'
        '  --cross-repo \\\n'
        '  --consumer-root /path/to/rexecop \\\n'
        '  --consumer-root /path/to/tecrax'
    ) in text
