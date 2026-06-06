# Admission Policy Contracts

`govengine.admission` defines neutral admission, policy, approval, and audit
record contracts for host runtimes.

It is a shape and validation layer only. It does not implement a policy engine,
own profile policy meaning, run operator approval workflows, store audit logs,
deliver carrier messages, hold credentials, or execute tools.

## Objects

- `GovAdmissionDecision` validates one host-provided go/no-go decision over a
  redacted `subject_ref`.
- `GovPolicyDecision` validates the policy result attached to a host subject.
- `GovApprovalRequest` validates approval-request state without owning the
  approval workflow.
- `GovAuditRecord` validates an append-only audit record shape without owning
  storage or retention.

## Boundary

Admission metadata must not contain raw targets, raw prompts, credentials,
commands, subprocesses, shell payloads, live-backend claims, runtime storage
paths, carrier payloads, or schedules.

Hosts such as Ravenclaw may map their own runtime admission and execution-gate
semantics into these objects. GovEngine validates the neutral representation;
the host still owns security meaning, target selection, budget logic, cooldown
logic, operator approval, queue mutation, process control, audit persistence,
and concrete execution.

The canonical runtime admission contract lives in
[RUNTIME_ADMISSION.md](RUNTIME_ADMISSION.md). The initial
`RuntimeAdmissionResult` record is the bounded admission decision surface. The
next composition helper must populate it from policy, ticket, trust, SCLite
guarded verification, replay freshness, runner-profile, and
receipt-obligation signals without making intent an execution authority.
