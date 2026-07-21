from __future__ import annotations

from pathlib import Path

from scripts.validate_api_stability import consumer_import_map


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
