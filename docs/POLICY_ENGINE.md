# Policy engine MVP

`govengine.policy` provides a **deterministic, fail-closed policy runtime** for
hosts that already use GovEngine admission contracts. It evaluates bounded
`PolicyRequest` records against compiled declarative rule packs and returns
`PolicyVerdict` envelopes suitable for projection into `GovPolicyDecision`.

It is **not** a domain policy product, operator workflow, SCLite authority, raw
evidence store, scheduler, or execution authority.

## Modules

| Module | Role |
| --- | --- |
| `govengine.policy.model` | `PolicyRequest`, `PolicyVerdict`, `PolicyObligation`, `PolicyConstraint`; validators |
| `govengine.policy.compiler` | `PolicyCompiler`, `CompiledPolicyPack`, `CompileResult`, `PolicyRule` |
| `govengine.policy.runtime` | `PolicyEngine`, `evaluate_policy()` |
| `govengine.policy.enforcement` | Policy pack/verdict digest binding, `PolicyEnforcementPlan`, existing admission binding, neutral control projection |
| `govengine.policy.baselines` | deterministic baseline policy pack generator |
| `govengine.policy.schema` | JSON Schema documents for authoring and host validation |
| `govengine.policy.cli` | `govengine-policy` authoring CLI |

Top-level imports are re-exported from `govengine` and listed in
[API_STABILITY_MATRIX.md](API_STABILITY_MATRIX.md).

## Request and verdict (schema `v0.1`)

`PolicyRequest` carries:

- `request_id`, `subject_ref`, `schema_version`
- bounded `principal`, `action`, `resource`, `context` mappings
- `evidence_refs` (references only — no raw evidence payloads)
- `metadata` (forbidden keys reject credentials, commands, stdout/stderr, targets, URLs, …)

`PolicyVerdict` decisions:

| Decision | Meaning |
| --- | --- |
| `allow` | Permitted with no extra obligations |
| `allow_with_obligations` | Permitted when host satisfies returned obligations/constraints |
| `approval_required` | Blocked until operator approval evidence is present |
| `deny` | Fail closed |

## Policy packs

Hosts compile declarative packs with `PolicyCompiler().compile(mapping)` or
`compile_policy_pack(mapping)`.

Pack shape:

```yaml
policy_id: policy-pack-1
version: "2026-06-20"
rules:
  - rule_id: allow-read-with-receipt
    effect: allow_with_obligations
    conditions:
      action.mode: read
    reason_code: read_allowed_with_receipt
    obligations:
      - obligation_id: receipt-required
        kind: receipt
    constraints:
      - constraint_id: bounded-output
        kind: output_limit
        value: 4096
  - rule_id: deny-unsafe
    effect: deny
    conditions:
      action.mode: unsafe
    reason_code: unsafe_action_denied
```

Compiler rejects:

- packs without `policy_id`, `version`, or rules
- rules without `rule_id`, `effect`, or non-empty `conditions`
- **conflicting rules** that share identical conditions but differ in `effect`

Compiled rules are sorted by `priority` (lower first).

## Authoring CLI

The package ships an authoring CLI. It is deliberately **JSON-first**: JSON is
the canonical GovEngine policy interchange format, and JSON files are also
YAML-compatible for hosts that want to store them under `.yaml`. GovEngine does
not parse domain profile YAML or take over host taxonomy ownership.

Generate a baseline:

```bash
govengine-policy scaffold governed-runtime --output policy.json
```

Available baselines:

- `readonly`
- `mutating-approval`
- `destructive-deny`
- `bounded-output`
- `governed-runtime`

Validate a policy pack:

```bash
govengine-policy validate policy.json
govengine-policy validate policy.json --json
```

Emit the JSON Schema used for authoring tools:

```bash
govengine-policy schema policy-pack
govengine-policy schema policy-request
govengine-policy schema policy-verdict
```

Normalize a compiled pack:

```bash
govengine-policy compile policy.json --json
```

The CLI never executes work, contacts SCLite, writes audit ledgers, or invokes a
runner. Validation is performed through the same `PolicyCompiler` used by the
runtime path.

## Runtime evaluation

```python
from govengine import PolicyCompiler, PolicyEngine, policy_verdict_to_gov_policy_decision

pack = PolicyCompiler().compile({...}).policy_pack
verdict = PolicyEngine().evaluate(
    {
        "request_id": "request-1",
        "subject_ref": "artifact://task/1",
        "action": {"mode": "read"},
        "resource": {"criticality": "low"},
    },
    pack,
)
decision = policy_verdict_to_gov_policy_decision(verdict)
```

### Built-in invariants (before rule matching)

| Condition | Verdict |
| --- | --- |
| `action.unsafe_execution_shape` or `context.execution.unsafe_execution_shape` | `deny` / `unsafe_execution_shape` |
| `action.destructive` without approval evidence refs | `deny` / `destructive_action_without_approval_evidence` |
| mutating action on `resource.criticality: critical` without approval evidence | `approval_required` / `critical_mutating_action_requires_approval` |
| no matching rule | `deny` / `no_matching_policy_rule` |

When multiple rules match, evaluation order is: **deny** → **approval_required** → **allow_with_obligations** → first **allow**.

## Admission integration

`policy_verdict_to_gov_policy_decision()` maps verdicts into `GovPolicyDecision`
for existing admission composition:

- `allow_with_obligations` → `decision: allow` with `controls` like `obligation:receipt-required`
- `approval_required` → `decision: require_approval` with blockers
- `deny` → `decision: deny`

Pass the resulting summary into `compose_runtime_admission_result()` as
`policy_decision`. GovEngine still does not execute work or store audit logs.

## Policy enforcement plan and admission binding

`admit_policy_execution(pack, verdict)` is the fail-closed boundary between a
PolicyEngine verdict and a host runner. It binds the compiled pack and verdict
with GovEngine-owned `sha256:` record digests and returns a
`PolicyEnforcementPlan`. `policy_enforcement_admission(plan)` projects that plan
into the existing `GovAdmissionDecision` contract; it does not introduce a second
runtime admission envelope. The matching validators reject pack, version,
verdict, control, plan, admission, or digest drift.

Supported control projection:

| Policy item | Runtime projection | Required host behavior |
| --- | --- | --- |
| obligation `receipt` or `receipt_required` | `receipt_required: true` | emit a terminal runner receipt |
| obligation/constraint `output_digest_required` | `output_digest_required: true` | bind each executed step to a bounded output digest |
| constraint `output_limit` | `max_output_bytes` | cap the persisted/redacted output record |
| constraint `timeout` | `timeout_seconds` | apply the tighter timeout at the supported IO boundary |
| constraint `max_steps` | `max_steps` | reject a workflow exceeding the admitted step count |

Repeated numeric limits project to the smallest positive value. Unknown kinds,
non-positive limits, invalid boolean controls, deny, and approval-required
verdicts produce `status: blocked`. The plan and admission record contain no
commands, credentials, raw output, target URL, or domain taxonomy.

The projection is not proof that a host enforced it. A host must validate the
plan and admission immediately before execution, enforce all controls, and bind
both references into its request and receipt. SCLite remains responsible for
canonical evidence and review artifacts.

## Boundary (non-claims)

GovEngine policy MVP does **not**:

- own Tecrax/Ravenclaw domain semantics or profile YAML meaning
- run operator approval workflows or persist audit ledgers (see `govengine.admission` ports)
- verify SCLite tickets, signatures, or guarded bundles
- authorize live subprocess/SSH/API execution by itself
- claim that a projected control was enforced by a host runner

Hosts remain responsible for mapping runtime events into `PolicyRequest`,
supplying approval evidence refs, and acting on verdicts under their own
operator and storage controls.

## Related

- [ADMISSION_POLICY.md](ADMISSION_POLICY.md) — admission envelopes and audit ledger
- [RUNTIME_ADMISSION.md](RUNTIME_ADMISSION.md) — `RuntimeAdmissionResult` composition
- [GOVERNED_RUNTIME_MVP_RUNBOOK.md](GOVERNED_RUNTIME_MVP_RUNBOOK.md) — operator chain
