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
| `govengine.policy.compiler` | `PolicyCompiler`, `CompiledPolicyPack`, `CompileResult`, `PolicyRule`, module-scoped typed `PolicyCondition` |
| `govengine.policy.runtime` | `PolicyEngine`, `evaluate_policy()` |
| `govengine.policy.explain` | `PolicyEvaluationExplanation`, `explain_policy_evaluation()` redacted decision reasoning |
| `govengine.policy.reasons` | versioned kernel reason registry and authored-code grammar |
| `govengine.policy.migration` | module-scoped v0.1 equality-map to typed-v1 normalization scaffold |
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
- duplicate rule ids
- **conflicting rules** that share identical conditions but differ in `effect`
- redundant rules that repeat the exact predicate and effect
- conflicting obligation/constraint ids with different definitions
- more than 256 rules, 32 conditions per rule, 4096 total conditions or 64
  controls per rule
- invalid or unbounded priorities
- invalid reason-code identifiers, risk classes or non-bounded risk scores

Compiled rules are sorted by `priority` (lower first).
The compiler performs exact deterministic analysis only; it does not attempt
partial-overlap reasoning, subsumption or SAT solving.

### Typed conditions (`schema_version: v1`)

Policy pack v1 replaces the implicit equality map with an explicit condition
AST:

```yaml
policy_id: policy-pack-typed
version: "1.0.0"
schema_version: v1
issuer_ref: organization:example
policy_epoch: 7
validity:
  not_before: "2026-07-16T00:00:00Z"
  expires_at: "2026-08-16T00:00:00Z"
supersedes: []
rules:
  - rule_id: allow-bounded-read
    effect: allow
    conditions:
      - path: action.mode
        operator: eq
        value: read
      - path: resource.risk_score
        operator: lte
        value: 0.5
      - path: principal.roles
        operator: contains
        value: operator
```

The closed operator set is:

`eq`, `neq`, `in`, `not_in`, `contains`, `exists`, `lt`, `lte`, `gt`,
`gte`, `subset_of`, `matches_namespace`.

Condition paths must use one of the neutral namespaces `principal`, `action`,
`resource`, `request_context` or host-supplied evaluator `context`. GovEngine
validates the namespace and path syntax; profiles retain ownership of leaf
vocabulary and domain meaning.

Missing paths do not satisfy predicates except an explicit `exists: false`.
Comparison does not coerce booleans, integers, floats or strings. Invalid
compile-time operands are rejected with `invalid_policy_condition_operand`;
wrong runtime operand types fail with
`policy_condition_operand_type_mismatch`. `matches_namespace` performs exact
or dot-delimited child matching only and is not a regex facility.

Legacy packs without `schema_version`, or with `v0.1`, remain equality-map
inputs. The compiler normalizes them internally to typed `eq` conditions while
`CompiledPolicyPack.as_dict()` preserves the v0.1 wire representation.

`govengine.policy.migration.migrate_policy_pack_v0_1_to_v1()` provides a
normalizing compatibility scaffold. It requires caller-supplied `issuer_ref`,
`policy_epoch`, `not_before` and `expires_at`; it does not infer trust, activate
the pack, sign it or store it. The helper is module-scoped compatibility API
and is intentionally absent from the capped `govengine.v1` facade.

### Reason codes

`govengine.policy.reasons.policy_reason_code_registry()` publishes the fixed
kernel codes used for compile results, invariant outcomes and evaluator
errors. Rule-authored outcome codes are not centrally assigned by GovEngine:
they remain part of the signed policy pack, but must match the bounded
`^[a-z][a-z0-9_]{0,127}$` grammar. Dynamic values belong in bounded error
context, never in the identifier.

### Active policy binding

V1 packs declare `issuer_ref`, `policy_epoch`, a UTC validity window and
optional `supersedes` references. Declaration alone is not activation.
`PolicyActivationPort.current_binding()` supplies a host-authenticated,
module-scoped `PolicyActivationBinding` containing the current policy
id/version/digest/epoch/issuer, trust reference, activation window and status.

Canonical governance accepts only `active`. It rejects `superseded`, `revoked`
and `expired`, plus future or elapsed activation windows and drift in the
policy identity, digest, epoch or issuer. A host activation may narrow the
pack's declared validity window but cannot extend it. GovEngine defines the
contract and deterministic checks; host adapters retain repository, trust,
storage and activation mutation ownership.

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
govengine-policy schema policy-pack-v1
govengine-policy schema policy-request
govengine-policy schema policy-verdict
```

Normalize a compiled pack:

```bash
govengine-policy compile policy.json --json
```

Evaluate and explain one bounded request:

```bash
govengine-policy explain policy.json request.json --json
govengine-policy simulate policy.json request.json --json
```

Evaluate and explain child-operation planning admission without runtime
mutation:

```bash
govengine-policy automation-transition automation-request.json --json
```

The CLI never executes work, contacts SCLite, writes audit ledgers, or invokes a
runner. Validation is performed through the same `PolicyCompiler` used by the
runtime path.

### CLI contract registry (G8)

GovEngine publishes a machine-readable registry for `govengine-policy` and
`govengine-supervisor` operator CLIs:

- schema: `govengine.cli_contract_registry.v0.1`
- module: `govengine.cli_contracts.cli_contract_registry()`
- error envelope: `govengine.cli_error.v0.1` on `--json` failure paths

Exit-code policy:

| Code | Meaning |
| --- | --- |
| `0` | success, explained, passed, or catalog emission |
| `2` | validation/input error, blocked policy outcome, or compatibility failure |

Blocked explain/simulate/compatibility outcomes still emit their bounded JSON
payload before returning exit code `2`. Input and authoring failures with
`--json` emit `govengine.cli_error.v0.1` instead of unstructured stderr only.

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

## Explanation output

`explain_policy_evaluation(request, pack)` evaluates through the same
`PolicyEngine` path and returns `PolicyEvaluationExplanation`. Legacy packs
retain schema `v0.1`; typed policy packs emit schema `v1`.
The explanation is intended for host/runtime UX such as RExecOp review screens,
without requiring the host runtime to reimplement GovEngine policy reasoning.

It includes:

- decision, reason code, risk class and risk score;
- `evaluation_path`: `invariant`, `matched_rule`, `no_match` or `verdict`;
- the selected matched rule, when a rule produced the verdict;
- redacted rule evaluation metadata showing condition paths, operators and match status,
  without actual request values;
- obligations and constraints with support status;
- unsupported controls that make enforcement fail closed;
- projected neutral runtime controls and enforcement-plan status/blockers.

For typed packs the v1 trace also binds `policy_pack_digest`, issuer, epoch and
reason-registry version. `trace_digest` is recomputed over the complete
redacted explanation body. A golden test runs on every supported Python
version, so verdict, reason, rule order and both digests cannot drift silently.

It does not expose raw request payload values, execute work, approve operators,
verify SCLite artifacts, or prove that a host enforced projected controls.

### Built-in invariants (before rule matching)

| Condition | Verdict |
| --- | --- |
| `action.unsafe_execution_shape` or `context.execution.unsafe_execution_shape` | `deny` / `unsafe_execution_shape` |
| `action.destructive` without a bound approval attestation | `deny` / `destructive_action_without_approval_evidence` |
| mutating action on `resource.criticality: critical` without a bound approval attestation | `approval_required` / `critical_mutating_action_requires_approval` |
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

Hosts remain responsible for mapping runtime events into `PolicyRequest` and
acting on verdicts under their own operator and storage controls. Legacy
strings in `evidence_refs`, admission digests, and context booleans do not prove
approval and do not release a critical mutation; the compatibility path remains
`approval_required` until the versioned bound approval-attestation contract is
implemented.

## Related

- [ADMISSION_POLICY.md](ADMISSION_POLICY.md) — admission envelopes and audit ledger
- [RUNTIME_ADMISSION.md](RUNTIME_ADMISSION.md) — `RuntimeAdmissionResult` composition
- [SECURITY_INTEGRATION.md](SECURITY_INTEGRATION.md) — canonical v1 security order
