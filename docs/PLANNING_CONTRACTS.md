# Planning Contracts

`govengine.planning` defines neutral planner-to-runtime handoff contracts for
host runtimes.

It is a shape and validation layer only. It does not implement a planner, own
domain planning semantics, store queues, run schedulers, hold credentials,
deliver carrier messages, or execute tools.

## Objects

- `GovTaskContract` validates one host-provided task contract. Hosts provide
  redacted `target_ref` values rather than raw targets.
- `GovPlanIntentContract` validates a planner handoff envelope containing one
  or more unique task contracts.
- `PlannerPort` describes supported planning contract shapes without becoming a
  planner implementation.

## Boundary

Planning metadata must not contain raw targets, raw prompts, credentials,
commands, subprocesses, shell payloads, live-backend claims, runtime storage
paths, carrier payloads, or schedules.

Hosts such as Ravenclaw may map their own planner/runtime task semantics into
these objects. GovEngine validates the neutral representation; the host still
owns security meaning, target selection, planning stages, UI behavior, queue
mutation, process control, operator approval, and concrete execution.
