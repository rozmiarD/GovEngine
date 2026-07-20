# Superseded roadmap lines

This is a compact architecture index, not an active roadmap or validation
source. Exact changes are preserved in [CHANGELOG.md](../../CHANGELOG.md) and
Git history.

| Line | Historical focus | Current disposition |
| --- | --- | --- |
| `0.1.x` | SCLite bridges, artifact state, signing/trust helpers | compatibility only; SCLite owns verification truth |
| `0.2.x`–`0.4.x` | boundary, runtime shell, orchestration, events, state and planning records | experimental/adapter surface; RExecOp owns runtime mechanics |
| `0.5.x`–`0.9.x` | admission, audit, runner supervision, review, profile fixtures and contract proofs | compatibility/fixture surface outside `govengine.v1` |
| `0.10.x`–`0.12.x` | package hardening, SCLite migrations and security-facade retirement | superseded migration history |
| `0.13.x`–`0.17.x` | governed-runtime MVP, PolicyEngine and typed execution/admission helpers | superseded as the canonical authorization path by v1 governance |
| `1.0.0rc1` | narrow governance facade, independent bindings, attempt-bound decision and shared conformance | current release candidate |

Obsolete MVP runbooks, guarded-admission examples and partial validation
histories were removed because they were unsafe as runnable current guidance
and duplicated the changelog. The durable boundary is:

```text
GovEngine decides; RExecOp executes; SCLite verifies lifecycle/evidence;
profiles define domain meaning.
```
