# Control Model

govengine.control defines deterministic between-step control decisions for hosts that already have governed event metadata, run state, and orchestration handoff records.

The core object is ControlDecision. It is a JSON-safe decision record with:

- a decision id and run id;
- a bounded action such as advance_state, record_only, pause, block, or request_profile_handoff;
- optional state transition endpoints;
- event references and required prior decisions;
- public-safe metadata.

validate_control_decision() checks the record and delegates state-transition legality to govengine.state_machine.validate_state_transition() whenever the decision claims a state transition. apply_control_decision() applies only that validated state transition to an in-memory GovRunState; it does not write to disk, enqueue work, schedule jobs, deliver messages, or execute commands.

## Boundary

Control decisions may describe a deterministic next governance step. They must not contain raw intent or prompts, credentials, secrets, tokens, commands, subprocesses, or shells. They also must not claim queues, schedulers, or schedules, delivery transports, runtime storage paths, live backends, or live execution authority.

Hosts such as Ravenclaw remain responsible for runtime loops, persistence, operator UX, delivery, credentials, carrier adapters, and concrete execution.

## Relationship To Runtime Shell

`govengine.control` remains the lower-level between-step control-decision layer
for validated state-machine transitions. `govengine.runtime_shell` is the 0.3
host-facing projection layer for higher-level actions such as `start`, `resume`,
`stop`, `cancel`, `replan`, and `cooldown`. Those actions are still metadata:
the host decides how to persist state, mutate queues, start or stop processes,
or ask an operator for approval.
