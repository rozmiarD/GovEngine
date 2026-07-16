# Security Policy

GovEngine is a governance and contract-helper package. It is not a scanner, exploit framework, sandbox, or authorization authority.

## Supported versions

GovEngine is currently alpha and still pre-1.0. Security fixes should target `main` until a stable release line exists.

## Reporting issues

Please report security-sensitive issues privately to the project owner when possible. Do not publish credentials, private targets, raw runtime logs, or exploit details in public issues.

## Security boundaries

GovEngine must not:

- treat LLM prose as executable authority;
- construct live shell commands from untrusted text;
- widen Ravenclaw/GovEngine/SCLite dependency direction;
- publish raw stdout/stderr, command logs, credentials, cookies, private paths, or private target identifiers;
- claim authorization to test a target;
- claim live vulnerability evidence from dry-run artifacts.

The detailed trusted computing base, attacker model and residual risks are in
[`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md). Tested guarantees, digest
bindings and explicit non-claims are in
[`docs/SECURITY_GUARANTEES.md`](docs/SECURITY_GUARANTEES.md).

GovEngine runs in the host process. It does not claim resistance to a malicious
or fully compromised in-process host that skips the library or ignores its
decision.

## Expected safe behavior

New safety-sensitive code should be deterministic by default, testable without live targets, and explicit about:

- scope and policy decisions;
- approved vs prepared execution shape;
- dry-run/local/mock/live truth;
- receipt/evidence non-claims;
- owner-review boundaries.
