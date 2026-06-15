# State Machine

GovEngine state-machine contracts define neutral run-state metadata and allowed transitions. They do not persist state, schedule work, own queues, hold credentials, or execute live commands.

## Run State

`GovRunState` summarizes one governed run:

- `run_id`: stable host-supplied id;
- `state`: current neutral state;
- `profile`: consuming domain profile;
- `event_refs`: compact references to `EventEnvelope` records;
- `artifact_refs`: compact references to governed artifacts;
- `blockers`: reasons that currently block progress;
- `metadata`: optional host metadata.

The object is a boundary summary, not a storage record. Hosts choose where and how state is persisted.

## Allowed States

Current 0.2 boundary work recognizes:

- `new`;
- `admitted`;
- `policy_checked`;
- `trust_checked`;
- `gated`;
- `running_dry_run`;
- `receipt_recorded`;
- `paused`;
- `blocked`;
- `completed`.

There is intentionally no `running_live` state. Live execution remains outside GovEngine's default contract.

## Transitions

`StateTransition` describes a deterministic transition request. `validate_state_transition()` checks that the transition is allowed and that moving from `gated` to `running_dry_run` carries a `runner_gate_decision` requirement.

`apply_state_transition()` returns a new `GovRunState`; it does not write to disk, enqueue work, deliver messages, or execute anything.

## Forbidden Metadata

Run states and transitions must not carry:

- raw intent or prompts;
- credentials, secrets, tokens, passwords, or API keys;
- runtime storage paths or persistence claims;
- queues, schedulers, or schedules;
- live execution, live backend, command, subprocess, or shell payloads.

These remain runtime responsibilities. GovEngine validates compact governance state only.

## Relationship To Events

Events describe what happened. State transitions describe how the neutral run state changes in response. Both remain metadata: the host runtime owns the actual event bus, persistence, scheduling, UI, adapters, credentials, and execution.

## Release Use

State-machine docs, public exports, surface metadata, and tests agree that state
transitions are deterministic metadata only. Runtime persistence, queueing,
scheduling, credentials, and live execution stay outside GovEngine.

GovEngine uses two related but distinct state vocabularies:

- `GovRunState` / `StateTransition` in `govengine.state_machine` — narrow
  governed-run progression metadata;
- `RUNTIME_STATES` / host lifecycle actions in `govengine.runtime_shell` —
  higher-level control projections such as `start`, `pause`, and `cooldown`.

Hosts map their own persistence and process control onto these neutral shapes.
GovEngine validates records; it does not own a host state store.

`running` in `govengine.runtime_shell` is a host projection state only. It is not
equivalent to `running_dry_run`, and it must not be copied into
`govengine.state_machine.RUN_STATES`. The strict state machine has no
`running_live` state.
