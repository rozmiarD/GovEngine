# Guarded-Fresh Runtime Admission Example

This example documents the deterministic governed-runtime path for a
runtime-consumable SCLite artifact.

```text
SCLite guarded-strict verification
  -> GovEngine replay freshness claim
  -> RuntimeAdmissionResult composition
  -> dry-run runner profile
  -> receipt obligation
```

The example does not execute a backend and does not require credentials.

## Inputs

The host supplies bounded gate summaries:

- a prepared execution contract status and digest;
- a host-owned policy decision;
- an SCLite execution ticket status and ticket id/digest;
- a host-owned trust decision;
- an SCLite guarded-strict verification result;
- a GovEngine replay freshness decision;
- a dry-run runner profile;
- a receipt obligation binding admission and ticket references.

SCLite owns guarded verification and ticket semantics. GovEngine records replay
freshness and composes the runtime admission result from bounded signals.

## Expected Result

When all gates pass, `compose_runtime_admission_result()` returns an allowed
`RuntimeAdmissionResult`:

```text
status: allowed
allowed: true
reason_code: all_required_gates_passed
sclite_guarded_strict.verification_status: passed
replay_freshness.replay_status: fresh
runner_profile.name: dry-run
receipt_obligation.required: true
```

The second claim for the same guarded payload must be blocked as replayed. A
runtime-consumable admission must not treat replayed, stale, missing, or
non-strict guarded verification as allowed.

## Boundary

This example is intentionally dry-run/default-safe:

- no live subprocess runner;
- no target contact;
- no raw evidence storage;
- no credential loading;
- no PKI/KMS/key-store ownership;
- no SCLite schema or canonicalization ownership;
- no Ravenclaw/OpenClaw/MCP/A2A dependency.

