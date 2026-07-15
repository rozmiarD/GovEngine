# Governance decision

`govengine.governance_decision.evaluate_governance()` is the canonical G2-C
composition point for one `GovernanceRequest v1`. It reuses the existing
PolicyEngine verdict, enforcement plan and governance trace, then combines
them with independent approval, scope and capability decisions.

## Allowed decision

`status: allowed` is emitted only when all of these conditions hold:

- the request and every supplied GovEngine-owned digest validate;
- the request policy epoch equals the host-owned `PolicyActivationPort` view;
- PolicyEngine produces an enforceable plan;
- an `approval_required` verdict is resolved only by the request's exact
  `ApprovalAttestation`;
- approval trust, time, revocation and host-provided cryptographic signature
  verification pass;
- requested scope is allowed by the independent scope policy;
- operation requirements are compatible with the bound runtime inventory.

Mutation always requires a validated approval, even when the matching policy
rule returns `allow`. Opaque references, booleans and policy evidence strings
are not approval inputs.

## Attempt-bound authorization

Only an allowed decision contains `GovernanceAuthorization`. It binds:

- operation, step and attempt;
- runtime instance, lease id/epoch and fencing-token digest;
- execution-spec and payload digests;
- requested-scope and runtime-inventory digests/epoch;
- policy pack and policy epoch;
- an explicit nonce and validity window of at most 60 seconds.

The authorization declares `consume_once: true`, but GovEngine does not claim
or persist it. RExecOp owns the atomic decision claim, its runtime attempt
permit, the final pre-I/O recheck and all connector execution. Consequently
`GovernanceAuthorization` is not a second runtime permit.

Module-scoped `DecisionClaimPort` makes that handoff explicit. Its host adapter
must atomically claim both the decision digest and nonce: exactly the first
claim may return `True`, and reuse of either value must return `False` even for
a different attempt or runtime instance. The attempt and runtime identifiers
are audit bindings, not replay namespaces. Callers verify the signed decision,
runtime bindings and expiry before the claim. A successful production claim
remains consumed across restart and recovery while its authorization or
attempt remains recoverable; a rejected claim does not overwrite its existing
owner binding. GovEngine provides no storage, lock, retention or recovery
implementation; those remain RExecOp concerns.

`approval_required` and `denied` decisions never contain authorization.

## Determinism and JSON validation

The evaluator does not generate clocks or nonces. The caller supplies the
evaluation time, expiration and nonce, so identical inputs produce an
identical decision body and digest across supported Python versions.

`GovernanceDecision.from_mapping()` rejects unknown fields, validates its
nested authorization and recomputes `decision_digest` from the full body. A
supplied digest cannot override the computed record.

The digest proves record integrity, not GovEngine identity.
`sign_governance_decision()` signs the complete validated record through a
host-owned `SignerPort`. `require_trusted_governance_decision()` then checks
the exact record type, schema, purpose, decision digest, signing policy,
cryptographic verifier result and trust policy before returning the decision.
Another valid decision, an untrusted signer or a failed verifier result is
rejected.

These helpers reuse the existing `SignedArtifact`/`VerifierPort` boundary; G2
does not embed a second signature or key system in the decision contract. A
runtime must call the fail-closed verifier before claiming authorization.

## Trust and ownership boundaries

`PolicyActivationPort`, `ApprovalRevocationPort` and
`ApprovalSignatureVerificationPort` are host-provided read boundaries.
`DecisionClaimPort` is a host-provided atomic mutation boundary used only after
those checks. GovEngine defines their fail-closed semantics but does not
provide production storage, PKI, key custody or remote trust services. SCLite
schemas and canonical verification remain unchanged.

The deterministic `DemoDigestSigner`/`DemoDigestVerifier` used by tests remain
fixtures and are not production identity proof.
