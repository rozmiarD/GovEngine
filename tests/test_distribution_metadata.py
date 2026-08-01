from __future__ import annotations

import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from scripts import validate_distribution_metadata as validator


ROOT = Path(__file__).resolve().parents[1]
ROOT_NAME = 'govengine-1.0.0rc2'


def _metadata(*, dependency: str = 'sclite-core==2.0.1', description: bytes | None = None) -> bytes:
    body = description if description is not None else (ROOT / 'PYPI_LONG_DESCRIPTION.md').read_bytes()
    return (f'Name: govengine\nVersion: 1.0.0rc2\nDescription-Content-Type: text/markdown\nRequires-Dist: {dependency}\n\n').encode() + body


def _artifacts(tmp_path: Path, *, wheel_metadata: bytes | None = None) -> tuple[Path, Path]:
    metadata = _metadata()
    wheel = tmp_path / f'{ROOT_NAME}-py3-none-any.whl'
    with zipfile.ZipFile(wheel, 'w') as archive:
        archive.writestr(f'{ROOT_NAME}.dist-info/METADATA', wheel_metadata or metadata)
    sdist = tmp_path / f'{ROOT_NAME}.tar.gz'
    with tarfile.open(sdist, 'w:gz') as archive:
        info = tarfile.TarInfo(f'{ROOT_NAME}/PKG-INFO')
        info.size = len(metadata)
        archive.addfile(info, io.BytesIO(metadata))
    return wheel, sdist


def test_accepts_exact_distribution_metadata(tmp_path: Path) -> None:
    wheel, sdist = _artifacts(tmp_path)
    validator.validate_distribution_metadata(wheel=wheel, sdist=sdist)


def test_rejects_dependency_drift(tmp_path: Path) -> None:
    wheel, sdist = _artifacts(tmp_path, wheel_metadata=_metadata(dependency='sclite-core==2.0.0'))
    with pytest.raises(validator.MetadataValidationError, match='wheel:requires_dist'):
        validator.validate_distribution_metadata(wheel=wheel, sdist=sdist)


def test_rejects_description_byte_drift(tmp_path: Path) -> None:
    wheel, sdist = _artifacts(tmp_path, wheel_metadata=_metadata(description=b'drift\n'))
    with pytest.raises(validator.MetadataValidationError, match='wheel:description_mismatch:source'):
        validator.validate_distribution_metadata(wheel=wheel, sdist=sdist)
