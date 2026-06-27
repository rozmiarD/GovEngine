#!/usr/bin/env python3
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from govengine import __version__ as package_version  # noqa: E402
from govengine.contract_proofs import (  # noqa: E402
    governance_contract_vocabulary,
    ravenclaw_contract_proof,
    tecrax_contract_proof,
    validate_governance_contract_vocabulary,
    validate_runtime_contract_proof,
)
from govengine.surfaces import public_surface_index  # noqa: E402


EXPECTED_VERSION = '0.16.1'
EXPECTED_RELEASE_LABEL = '0.16.1'
EXPECTED_SURFACES = [
    'artifact_governance_core',
    'planning_contracts_core',
    'admission_policy_core',
    'evidence_review_core',
    'domain_profile_sdk',
    'runtime_contract_proofs',
    'controlled_execution_core',
]
FORBIDDEN_PUBLIC_TERMS = (
    'C2',
    'C2i',
    "Commander's Intent",
    'ROE',
    'Tasking Order',
    'Control Measures',
    'SITREP',
    'AAR',
    'FRAGO',
)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def _pyproject() -> dict:
    return tomllib.loads(_read('pyproject.toml'))


def _assert(condition: bool, reason: str) -> None:
    if not condition:
        raise AssertionError(reason)


def main() -> int:
    project = _pyproject()['project']
    version = str(project['version'])
    classifiers = tuple(str(item) for item in project.get('classifiers', ()))
    surfaces = public_surface_index()
    surface_names = [surface.name for surface in surfaces]

    _assert(version == EXPECTED_VERSION, f'alpha_version_mismatch:{version}')
    _assert(package_version == EXPECTED_VERSION, f'package_version_mismatch:{package_version}')
    _assert('Development Status :: 3 - Alpha' in classifiers, 'missing_alpha_classifier')
    _assert('Development Status :: 2 - Pre-Alpha' not in classifiers, 'pre_alpha_classifier_still_present')
    _assert(surface_names == EXPECTED_SURFACES, f'surface_mismatch:{surface_names}')
    _assert(not any(surface.optional_profile for surface in surfaces), 'optional_surface_retained')
    _assert(all(surface.status.startswith('alpha_') for surface in surfaces), 'surface_status_retains_pre_alpha_label')

    vocabulary = validate_governance_contract_vocabulary()
    _assert(tuple(entry.term for entry in vocabulary) == tuple(entry.term for entry in governance_contract_vocabulary()), 'vocabulary_mismatch')

    for proof in (ravenclaw_contract_proof(), tecrax_contract_proof()):
        checked = validate_runtime_contract_proof(proof)
        _assert(checked.profile_conformance.status == 'passed', f'proof_conformance_failed:{checked.proof_id}')
        _assert(checked.supervision_plan.dry_run is True, f'proof_not_dry_run:{checked.proof_id}')
        _assert(checked.supervision_plan.live_backend_enabled is False, f'proof_live_backend_enabled:{checked.proof_id}')
        _assert(checked.evidence_refs, f'proof_missing_evidence_refs:{checked.proof_id}')

    public_text = '\n'.join(
        _read(path)
        for path in (
            'README.md',
            'CONTRIBUTING.md',
            'PUBLIC_STATUS.md',
            'SECURITY.md',
            'PUBLISHING.md',
            'docs/ARCHITECTURE.md',
            'docs/API_BOUNDARY.md',
            'docs/ROADMAP.md',
            'docs/VALIDATION.md',
        )
    )
    _assert(EXPECTED_RELEASE_LABEL in public_text, 'missing_alpha_release_label')
    for term in FORBIDDEN_PUBLIC_TERMS:
        _assert(term not in public_text, f'forbidden_public_term:{term}')
    _assert('production-readiness claims' in public_text or 'production readiness' in public_text, 'missing_production_non_claim')

    print(f'alpha_readiness_ok:govengine=={EXPECTED_VERSION}:{EXPECTED_RELEASE_LABEL}:surfaces={len(surface_names)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
