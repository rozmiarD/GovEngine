# Guarded-Fresh Runtime Admission Example

> Archived compatibility example for the pre-v1 `RuntimeAdmissionResult`
> admission/replay path. It is retained as historical evidence, not as the
> current connector-authorization procedure.

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

The host supplies bounded gate summaries with `runtime_consumable=True` when
guarded/replay outcomes should block admission:

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
`compose_runtime_admission_result()` does not verify SCLite artifacts or record
replay persistence; obtain guarded/replay summaries first (for example via
`verify_guard_and_record_replay()`), then compose admission.

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
