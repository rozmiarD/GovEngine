# GovEngine Roadmap

GovEngine is being extracted in stages from Ravenclaw. The goal is a reusable governed-execution core that consumes SCLite and remains independent of Ravenclaw UI/runtime specifics.

## Stage 0 — package boundary

Status: completed.

- Create importable `govengine` package.
- Add standalone tests and CI.
- Document owned vs excluded surfaces.
- Keep live execution out of scope.

## Stage 1 — SCLite consumption

Status: completed for initial public package.

- Pin SCLite as the contract lifecycle dependency.
- Keep schema/lifecycle ownership in SCLite.
- Expose GovEngine helpers that prepare/check execution contracts around SCLite artifacts.

## Stage 2 — Ravenclaw external consumption

Status: completed in Ravenclaw migration branch.

- Remove in-tree `govengine/` from Ravenclaw.
- Consume GovEngine from the public git dependency.
- Preserve Ravenclaw compatibility wrappers.
- Validate focused GovEngine/Ravenclaw seams and Security Contract receipt.

## Stage 3 — API hardening

Next recommended work.

- Reduce implicit host-context assumptions.
- Convert remaining dictionary-heavy boundaries into explicit typed structures where useful.
- Add more tests around policy gateway and execution-ticket failure modes.
- Clarify which helpers are stable public API vs internal extraction compatibility.

## Stage 4 — runner protocol design

Not started.

- Define a small runner protocol and result type.
- Keep Ravenclaw subprocess execution as the first adapter.
- Move dry-run-safe assembly before any live execution mechanics.
- Require operator review before moving live subprocess execution into GovEngine.

## Stage 5 — carrier adapters

Not started.

Potential hosts/carriers such as OpenClaw, MCP, or A2A should come after the core API is stable. GovEngine should not become protocol-first.
