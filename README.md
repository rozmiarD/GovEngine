# GovEngine

[![CI: pytest](https://github.com/rozmiarD/GovEngine/actions/workflows/pytest.yml/badge.svg)](https://github.com/rozmiarD/GovEngine/actions/workflows/pytest.yml)
[![Package: govengine 1.0.0rc1](https://img.shields.io/badge/package-govengine%201.0.0rc1-blueviolet.svg)](https://pypi.org/project/govengine/1.0.0rc1/)
[![Python: 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](pyproject.toml)
[![Dependency: SCLite ==2.0.0](https://img.shields.io/badge/dependency-SCLite%20%3D%3D2.0.0-informational.svg)](https://github.com/rozmiarD/SCLite)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)

GovEngine is an in-process Python governance kernel designed to be integrated
into execution runtimes. It evaluates policy, approval, scope and capability
facts for one concrete operation attempt and returns a deterministic
`allowed`, `approval_required` or `denied` governance decision.

GovEngine recomputes and validates its own governance records and decision
bindings. It does not define artifact truth or verify lifecycle and evidence
bundles; those responsibilities belong to SCLite. GovEngine does not perform
the operation, schedule jobs, manage credentials, contact targets or store
evidence.

The published release-candidate package `1.0.0rc1` exposes a frozen candidate
contract through `govengine.v1`. Current `main` retains the `1.0.0rc1` version
label but is not the immutable published artifact: it contains documented
unreleased fixes that require a new release candidate before stable promotion.
The wider package still contains explicitly classified compatibility,
experimental and fixture surfaces.

The immutable PyPI long description for `1.0.0rc1` is stale: it was built from
the pre-publication README and still describes the old release posture and
`0.16.11` installation path. The wheel, dependency pin and release hashes are
unaffected. This repository README is the corrected project description; the
next release candidate must publish it as package metadata.

## Why GovEngine exists

Intent is not execution authority. A request from an operator, UI, agent or
LLM does not by itself establish that:

- the active policy allows the operation;
- approval covers this exact attempt, target and side-effect class;
- the requested destination is independently authorized;
- the selected runtime has the required capabilities;
- the decision is still current for the active lease and fencing token;
- a result belongs to the decision and runtime permit that preceded I/O.

GovEngine turns those independently supplied facts into one bounded,
reviewable and fail-closed governance decision. The host runtime must still
authenticate, atomically claim and enforce that decision.

## How the components work together

GovEngine is one component in a cooperating set of independent projects. This
set has no formal product name. Together they separate domain meaning,
governance, execution and proof:

- **A domain profile**, such as Tecrax, owns intent vocabulary, workflows,
  connector semantics, findings and domain validation.
- **RExecOp** owns domain-neutral workflow interpretation, operation lifecycle,
  queues, leases, fencing, retries, connector dispatch and I/O.
- **GovEngine** owns deterministic policy evaluation, approval requirements,
  scope and capability decisions, governance authorization and checks that
  terminal runtime facts satisfy the decision's obligations.
- **SCLite** owns canonical lifecycle and evidence contracts, integrity,
  receipts, review bundles and verification truth.

Used together, a profile describes what an operation means, RExecOp prepares
and executes it, GovEngine decides whether the exact attempt may proceed, and
SCLite makes the resulting lifecycle and evidence independently verifiable.

```text
Domain profile                 meaning, workflows, connector contracts
      |
      v
RExecOp                        lifecycle, lease/fencing, permit, I/O
      |  +---- request / terminal facts -----> GovEngine
      |  <---- decision / conformance result -+  policy, approval, scope,
      |                                           capabilities
      |
      +---- final lifecycle/evidence --------> SCLite
                                                  lifecycle/evidence truth
                                                  and verification
```

The canonical integration order is documented in
[`docs/SECURITY_INTEGRATION.md`](docs/SECURITY_INTEGRATION.md).

## Canonical governance flow

1. RExecOp constructs a digest-bound `GovernanceRequest` for one operation,
   step and attempt.
2. GovEngine recomputes complete GovEngine-owned governance bindings and
   evaluates the active typed policy.
3. GovEngine validates independently supplied approval, target scope and
   capability inventory facts.
4. `evaluate_governance()` returns a `GovernanceDecision`. Only `allowed`
   carries a short-lived authorization bound to the exact attempt, runtime,
   lease, fencing token, policy, scope and inventory.
5. RExecOp verifies the signed decision, atomically claims its digest and
   nonce, issues its own runtime permit and performs the final pre-I/O checks.
6. After I/O, GovEngine checks whether bounded terminal runtime facts match the
   exact decision and runtime permit and satisfy its output postconditions.
7. RExecOp projects final lifecycle and evidence artifacts for SCLite
   verification.

GovEngine runs inside the host process. A compromised host can bypass the
kernel or fabricate inputs, so malicious-host resistance is not claimed.

## What GovEngine provides

The frozen `govengine.v1` facade provides:

- a deterministic, typed and fail-closed PolicyEngine;
- policy obligations, constraints, enforcement plans and redacted
  explanations;
- independently bound `ApprovalAttestation` validation;
- digest-bound validation of GovEngine-owned `GovernanceRequest` records;
- deterministic `GovernanceDecision` evaluation;
- short-lived attempt-bound authorization contracts;
- governance traces, digests of GovEngine-owned records and stable reason
  codes.

Supporting module-scoped contracts provide:

- independent scope-policy and capability-inventory comparison;
- signed-decision verification through host-provided trust ports;
- checks that terminal runtime facts satisfy a decision and bind to an opaque
  RExecOp runtime permit;
- a language-neutral governance-protocol conformance corpus shared with runtime
  consumers.

Legacy admission, runner, planning, orchestration, state-machine and
runtime-shell APIs remain available only as classified compatibility or
experimental surfaces. They are not a second authorization protocol and are
outside the `govengine.v1` compatibility promise.

## What GovEngine does not do

GovEngine does not provide:

- operation lifecycle, queues, scheduling, retries, rollback or connector I/O;
- raw-intent, subprocess, scanner or exploit execution;
- domain intent, target, finding or connector semantics;
- credential, secret, PKI, CA, KMS, HSM or trust-anchor management;
- production policy, approval, replay, nonce, audit or receipt storage;
- raw artifact or evidence storage;
- SCLite schemas, canonicalization, lifecycle truth or proof verification;
- legal authorization or resistance to a host that ignores its decision.

RExecOp and other host runtimes own enforcement. Profiles own domain meaning.
SCLite owns truth and proof.

## Installation

Install the published release candidate:

```bash
python -m pip install govengine==1.0.0rc1
```

Use the exact pin shown above. Because `1.0.0rc1` is a pre-release, an
unqualified `pip install govengine` continues to select the latest stable
`0.16.11` line.

Requirements:

- Python 3.11 or newer;
- exact dependency `sclite-core==2.0.0`;
- imports intended for 1.x compatibility should come from `govengine.v1`.

## Quick start: evaluate a typed policy

This small example uses only the frozen candidate facade:

```python
from govengine.v1 import PolicyCompiler, PolicyEngine

compiled = PolicyCompiler().compile(
    {
        "schema_version": "v1",
        "policy_id": "example-read-policy",
        "version": "1.0.0",
        "issuer_ref": "organization:example",
        "policy_epoch": 1,
        "validity": {
            "not_before": "2026-01-01T00:00:00Z",
            "expires_at": "2099-01-01T00:00:00Z",
        },
        "supersedes": [],
        "rules": [
            {
                "rule_id": "allow-bounded-read",
                "effect": "allow",
                "conditions": [
                    {
                        "path": "action.mode",
                        "operator": "eq",
                        "value": "read",
                    }
                ],
                "reason_code": "bounded_read_allowed",
            }
        ],
    }
)

assert compiled.ok and compiled.policy_pack is not None

verdict = PolicyEngine().evaluate(
    {
        "request_id": "request-1",
        "subject_ref": "operation://example/1",
        "action": {"mode": "read"},
        "resource": {"criticality": "low"},
    },
    compiled.policy_pack,
)

assert verdict.decision == "allow"
assert verdict.reason_code == "bounded_read_allowed"
```

Policy evaluation alone is not execution permission. Runtime integrations
continue with the bound request and decision contracts described in
[`docs/GOVERNANCE_REQUEST.md`](docs/GOVERNANCE_REQUEST.md) and
[`docs/GOVERNANCE_DECISION.md`](docs/GOVERNANCE_DECISION.md).

## API stability and release status

| Item | Current status |
| --- | --- |
| Source/package version | `1.0.0rc1` |
| Package maturity | Public release candidate |
| Candidate 1.x facade | `govengine.v1`, exactly 40 exports |
| GovEngine-owned v1 records | 15 frozen records |
| SCLite dependency | `sclite-core==2.0.0` |
| Legacy root modules | Compatibility, experimental or fixture classifications |

Current source/package version: `1.0.0rc1`.
Current package pin: `govengine==1.0.0rc1`.

The final `1.0.0` promotion state is maintained in
[`PUBLIC_STATUS.md`](PUBLIC_STATUS.md). Exact facade and schema compatibility
rules are documented in
[`docs/API_COMPATIBILITY.md`](docs/API_COMPATIBILITY.md).

## Security model

GovEngine is deterministic and fail-closed at its documented boundaries:

- complete GovEngine-owned records have their digests recomputed;
- approval is separate from admission and binds the exact operation subject;
- scope policy and operation requirements are independent of requested scope
  and runtime inventory;
- decision digests provide integrity, not signer identity;
- the runtime must verify a trusted signed decision before atomic claim;
- terminal runtime facts are checked after I/O against decision-bound output
  obligations.

See the [threat model](docs/THREAT_MODEL.md), tested
[security guarantees](docs/SECURITY_GUARANTEES.md) and canonical
[security integration order](docs/SECURITY_INTEGRATION.md).

## Documentation

Start with the [documentation map](docs/README.md). The main references are:

- [Architecture and ownership](docs/ARCHITECTURE.md)
- [Governance request](docs/GOVERNANCE_REQUEST.md)
- [Governance decision](docs/GOVERNANCE_DECISION.md)
- [API stability matrix](docs/API_STABILITY_MATRIX.md)
- [API compatibility and migration](docs/API_COMPATIBILITY.md)
- [Conformance corpus](docs/CONFORMANCE.md)
- [Validation gates](docs/VALIDATION.md)

Release changes are in [`CHANGELOG.md`](CHANGELOG.md). Contribution rules are
in [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Development

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
python -m mypy govengine
python -m ruff check .
python scripts/validate_public_truth.py
python scripts/validate_release_readiness.py
```

On current post-tag `main`, `validate_release_readiness.py` validates source
invariants but reports `publishable=false`. It does not authorize republishing
`rc1` or promoting the changed source directly to stable.

Use `scripts/validate_clean_package_install.py --no-editable --venv <path>` for
an isolated package-install smoke test. See
[`docs/VALIDATION.md`](docs/VALIDATION.md) for the complete gate.

## License and provenance

GovEngine is MIT-licensed. It was extracted from Ravenclaw in contract-first
stages, so [`LICENSE`](LICENSE) preserves the copyright notice for the
originating Ravenclaw contribution lineage. The author metadata in
`pyproject.toml` identifies the GovEngine package maintainer; it does not
replace or reassign the originating copyright notice.
