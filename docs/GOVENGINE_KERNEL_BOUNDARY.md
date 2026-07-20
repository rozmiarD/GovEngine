# GovEngine kernel boundary

This page is the short ownership checklist. The complete design is in
[ARCHITECTURE.md](ARCHITECTURE.md); the machine-readable compatibility report is
`govengine.boundary.kernel_boundary_report()`.

## Owned By GovEngine

- deterministic PolicyEngine compilation and evaluation;
- approval requirements and attestation validation;
- scope and capability compatibility decisions;
- bounded governance request, decision, obligations and explanations;
- GovEngine-owned record digests and reason codes;
- checks that terminal runtime facts satisfy decision obligations.

## Owned By Profiles

Profiles such as Tecrax own domain vocabulary, intents, workflows, taxonomy,
thresholds and connector semantics. GovEngine may validate a compatibility
projection but does not interpret or own that meaning.

## Owned By Runtimes

RExecOp is the current domain-neutral runtime. It owns operation lifecycle,
queues, leases, fencing, retries, rollback coordination, runtime permits,
connectors, secrets and live I/O. Other hosts own the equivalent integration
mechanics when they embed GovEngine.

## Owned By SCLite

SCLite owns lifecycle/evidence schemas, canonicalization, artifact digests,
receipts, evidence contracts, review bundles and verification truth. GovEngine
may consume a SCLite result or opaque digest but does not reproduce its
authority.

## Non-Claims

GovEngine does not provide live target authorization, carrier adapter
ownership, runtime scheduling/execution, raw evidence storage, production
identity/key custody, SCLite verification, or resistance to a compromised host
that bypasses the kernel.

The broad package root also contains pre-v1 compatibility records. Their
presence does not change this ownership boundary and does not make them part of
`govengine.v1`.
