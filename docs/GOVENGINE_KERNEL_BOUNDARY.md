# GovEngine Kernel Boundary

GovEngine is the reusable governed-runtime kernel. Domain runtimes such as Ravenclaw supply profile meaning, operator workflow language, UI, storage, and live execution adapters.

## Owned By GovEngine

GovEngine owns portable mechanics that can be reused across profiles:

- artifact-governance boundary objects and transition decisions;
- controlled-execution gates and runner request/receipt envelopes;
- policy, trust, OODA, and SCLite lifecycle bridge decisions;
- public surface metadata for boundary review;
- kernel/profile/runtime/SCLite ownership reports.

The machine-readable entrypoint is `govengine.boundary.kernel_boundary_report()`.

## Owned By Profiles

Profiles own domain semantics. A profile may define taxonomy, policy meaning, tool semantics, evidence expectations, and operator workflow language. It may consume GovEngine and SCLite surfaces through a declared `DomainProfileContract`, but it must not claim kernel or runtime authority.

## Owned By Runtimes

Runtimes own concrete operation:

- operator UI;
- concrete tool or subprocess execution;
- local state storage;
- credential handling;
- OpenClaw, MCP, A2A, or other carrier adapters.

GovEngine must not become a hidden runtime by accepting raw intent or directly executing live work.

## Owned By SCLite

SCLite owns schema lifecycle, canonicalization, artifact-chain verification, and review-bundle verdicts. GovEngine consumes SCLite artifacts and verdicts; it does not redefine their authority.

## Non-Claims

The kernel boundary deliberately excludes:

- live target authorization;
- scanner or exploit execution;
- credential or key-store ownership;
- carrier adapter ownership;
- Ravenclaw, Tecrax, or other product UX ownership;
- SCLite schema or canonicalization authority.

## Release Use

Before a 0.2 release, the boundary report and public docs must agree: `KernelBoundary`, known domain profiles, conformance checks, public surface metadata, and non-claims should tell the same story.
