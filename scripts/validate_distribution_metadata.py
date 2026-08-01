#!/usr/bin/env python3
"""Fail closed unless one wheel and one sdist carry exact GovEngine metadata."""
from __future__ import annotations

import argparse
import re
import tarfile
import tomllib
import zipfile
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import NamedTuple


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_HEADERS = ("Name", "Version", "Description-Content-Type")
EXPECTED_DEPENDENCY = "sclite-core==2.0.0"


class MetadataValidationError(ValueError):
    pass


class DistributionMetadata(NamedTuple):
    name: str
    version: str
    description_content_type: str
    description: bytes
    requires_dist: tuple[str, ...]


def _project() -> dict[str, object]:
    with (ROOT / "pyproject.toml").open("rb") as source:
        return tomllib.load(source)["project"]


def _single_exact_member(names: list[str], *, kind: str, expected: str) -> str:
    matches = [name for name in names if name == expected]
    if len(matches) != 1:
        raise MetadataValidationError(f"{kind}:exact_member_count:{len(matches)}")
    return matches[0]


def _wheel_metadata_bytes(path: Path, *, root: str) -> bytes:
    expected = f"{root}.dist-info/METADATA"
    try:
        with zipfile.ZipFile(path) as archive:
            member = _single_exact_member(
                [info.filename for info in archive.infolist()], kind="wheel_metadata", expected=expected
            )
            info = archive.getinfo(member)
            mode = info.external_attr >> 16
            if mode and (mode & 0o170000) not in (0, 0o100000):
                raise MetadataValidationError("wheel_metadata:not_regular")
            return archive.read(member)
    except (OSError, zipfile.BadZipFile, KeyError) as error:
        raise MetadataValidationError(f"wheel:unreadable:{error}") from error


def _sdist_metadata_bytes(path: Path, *, root: str) -> bytes:
    expected = f"{root}/PKG-INFO"
    try:
        with tarfile.open(path, "r:gz") as archive:
            member = _single_exact_member(
                [item.name for item in archive.getmembers()], kind="sdist_root_pkg_info", expected=expected
            )
            info = archive.getmember(member)
            if not info.isfile():
                raise MetadataValidationError("sdist_root_pkg_info:not_regular")
            extracted = archive.extractfile(info)
            if extracted is None:
                raise MetadataValidationError("sdist:pkg_info_unreadable")
            return extracted.read()
    except (OSError, tarfile.TarError) as error:
        raise MetadataValidationError(f"sdist:unreadable:{error}") from error


def _parse_metadata(raw: bytes, *, kind: str) -> DistributionMetadata:
    message = BytesParser(policy=policy.default).parsebytes(raw)
    if message.defects or message.is_multipart():
        raise MetadataValidationError(f"{kind}:invalid_metadata")
    values: dict[str, str] = {}
    for header in REQUIRED_HEADERS:
        occurrences = message.get_all(header, [])
        if len(occurrences) != 1 or not occurrences[0].strip():
            raise MetadataValidationError(f"{kind}:{header}:count:{len(occurrences)}")
        values[header] = occurrences[0].strip()
    separators = ((raw.find(b"\r\n\r\n"), 4), (raw.find(b"\n\n"), 2))
    candidates = [(offset, size) for offset, size in separators if offset >= 0]
    if not candidates:
        raise MetadataValidationError(f"{kind}:missing_header_body_separator")
    offset, size = min(candidates)
    return DistributionMetadata(
        values["Name"], values["Version"], values["Description-Content-Type"],
        raw[offset + size :], tuple(message.get_all("Requires-Dist", [])),
    )


def validate_distribution_metadata(*, wheel: Path, sdist: Path) -> None:
    project = _project()
    name, version = str(project["name"]), str(project["version"])
    if project.get("readme") != "PYPI_LONG_DESCRIPTION.md":
        raise MetadataValidationError(f"project_readme:{project.get('readme')!r}")
    root = f"{re.sub(r'[-_.]+', '_', name)}-{version}"
    if wheel.name != f"{root}-py3-none-any.whl" or sdist.name != f"{root}.tar.gz":
        raise MetadataValidationError("artifact_name_mismatch")
    source_description = (ROOT / "PYPI_LONG_DESCRIPTION.md").read_bytes()
    metadata = {
        "wheel": _parse_metadata(_wheel_metadata_bytes(wheel, root=root), kind="wheel"),
        "sdist": _parse_metadata(_sdist_metadata_bytes(sdist, root=root), kind="sdist"),
    }
    for kind, parsed in metadata.items():
        if parsed.name != name:
            raise MetadataValidationError(f"{kind}:name:{parsed.name}!={name}")
        if parsed.version != version:
            raise MetadataValidationError(f"{kind}:version:{parsed.version}!={version}")
        if parsed.description_content_type != "text/markdown":
            raise MetadataValidationError(f"{kind}:description_content_type:{parsed.description_content_type}")
        if parsed.description != source_description:
            raise MetadataValidationError(f"{kind}:description_mismatch:source")
        if EXPECTED_DEPENDENCY not in parsed.requires_dist or any(
            requirement.startswith("sclite-core") and requirement != EXPECTED_DEPENDENCY
            for requirement in parsed.requires_dist
        ):
            raise MetadataValidationError(f"{kind}:requires_dist:{parsed.requires_dist!r}")
    if metadata["wheel"].description != metadata["sdist"].description:
        raise MetadataValidationError("wheel_sdist:description_mismatch")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--sdist", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        validate_distribution_metadata(wheel=args.wheel, sdist=args.sdist)
    except MetadataValidationError as error:
        print(f"distribution_metadata_invalid:{error}")
        return 1
    project = _project()
    print(f"distribution_metadata_ok:{project['name']}=={project['version']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
