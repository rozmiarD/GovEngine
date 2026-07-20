# Runtime Shell

`govengine.runtime_shell` is a legacy experimental surface defining neutral
runtime/control projection records for compatibility consumers. RExecOp owns
the current queue, scheduler and operation-lifecycle mechanics.

It is a shape and validation layer only. It does not persist state, own queues,
run a scheduler, deliver carrier messages, hold credentials, or execute tools.

## Objects

- `GovControlAction` validates high-level host actions such as `start`, `pause`,
  `resume`, `stop`, `cancel`, `replan`, `degrade_to_dry_run`, `cooldown`,
  `retry`, and `archive`.
- `GovQueueLane` and `GovQueueSnapshot` validate redaction-bounded queue
  summaries. The host owns queue storage and scheduling.
- `GovRuntimeSnapshot` combines host-provided state, control actions, and queue
  snapshots into a compact reviewable projection.
- `GovSchedulerTick` records deterministic tick metadata without becoming a
  scheduler.

## Boundary

Runtime-shell metadata must not contain raw prompts, credentials, commands,
subprocesses, shell payloads, live-backend claims, runtime storage paths, carrier
payloads, or schedules.

Host runtimes may map their own state and operator actions into these objects.
GovEngine validates the neutral representation; the host still owns UI
behavior, persistence, queue mutation, process control, operator approval and
concrete execution. Ravenclaw remains a legacy compatibility consumer.

## Historical Ravenclaw 0.11 / GovEngine 0.3 fit

This surface exists because Ravenclaw's state/control projection showed that the
0.2 `GovRunState` and `ControlDecision` objects could represent some governance
facts, but could not faithfully represent host lifecycle actions such as
`start`, `resume`, `stop`, `cancel`, `replan`, and `cooldown` without collapsing
them into `record_only` gaps.

GovEngine 0.3 keeps those actions as explicit neutral control records while
remaining non-authoritative about how a host performs them.

Runtime-shell states are projection states. They are intentionally broader than
the strict `govengine.state_machine` run-state vocabulary. A host may report a
projection such as `running` or `cooldown`, but GovEngine's deterministic
state-machine path still uses `running_dry_run` and never defines
`running_live`.
