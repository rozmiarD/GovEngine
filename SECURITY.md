# Security Policy

GovEngine is an in-process governance kernel. It is not a scanner, exploit
framework, sandbox, execution runtime, or remote authorization authority.

## Supported versions

GovEngine source currently tracks the published `1.0.0rc2` release candidate.
Security fixes should target `main` until the stable release line exists. The
public rc2 artifacts passed independent external review with zero open P0/P1
and were published through the tag-confirmed OIDC workflow. Final `1.0.0`
promotion requires the candidate observation window to complete without an
open P0/P1 and the remaining downstream qualification to stay green. The
published rc2 window is elapsed_unclosed, not completed: stable promotion stays
`publishable=false` until a forward-only closure record binds the frozen record
and locally verified closure evidence by SHA-256.

## Reporting issues

Please report security-sensitive issues privately to the project owner when possible. Do not publish credentials, private targets, raw runtime logs, or exploit details in public issues.

## Security boundaries

GovEngine must not:

- treat LLM prose as executable authority;
- construct live shell commands from untrusted text;
- violate the documented SCLite/GovEngine/RExecOp/profile dependency direction;
- publish raw stdout/stderr, command logs, credentials, cookies, private paths, or private target identifiers;
- claim authorization to test a target;
- claim live vulnerability evidence from dry-run artifacts.

The detailed trusted computing base, attacker model and residual risks are in
[`docs/THREAT_MODEL.md`](docs/THREAT_MODEL.md). Tested guarantees, digest
bindings and explicit non-claims are in
[`docs/SECURITY_GUARANTEES.md`](docs/SECURITY_GUARANTEES.md).

GovEngine runs in the host process. It does not claim resistance to a malicious
or fully compromised in-process host that skips the kernel or ignores its
decision.

## Expected safe behavior

New safety-sensitive code should be deterministic by default, testable without live targets, and explicit about:

- scope and policy decisions;
- approved vs prepared execution shape;
- dry-run/local/mock/live truth;
- receipt/evidence non-claims;
- bounded, recursively filtered metadata at key-resolution and trust-store
  adapter boundaries;
- owner-review boundaries.
