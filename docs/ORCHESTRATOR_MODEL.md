# Orchestrator Model

`govengine.orchestration` is a legacy experimental compatibility surface for
deterministic handoff records. RExecOp owns current orchestration mechanics.
GovEngine must not become an agent loop, workflow scheduler, operator UI,
carrier adapter, credential store, or live executor.

## What The Compatibility Contract Describes

The compatibility contract describes reusable control-flow boundaries:

- state-transition routing;
- between-step control decisions;
- receipt-reference routing;
- profile-boundary checks.

The machine-readable entrypoints are `govengine.orchestration.orchestrator_boundary_contract()` and `govengine.orchestration.validate_orchestration_step()`.

## What A Runtime Owns

The host runtime owns concrete operation:

- event-loop liveness;
- workflow scheduling;
- operator UI;
- credential handling;
- carrier delivery;
- concrete execution.

The compatibility record can declare required decisions and expected boundary
outputs. RExecOp owns traversal and decides which runtime step comes next,
when and where work is scheduled, how operators see it, which carrier
transports it, and whether credentials or live execution are available.

## Orchestration Step

`OrchestrationStep` is a bounded handoff record. It describes:

- `step_id`: stable local id;
- `stage`: one allowed orchestration stage;
- `profile`: consuming domain profile;
- `consumes`: prior artifacts, decisions, receipts, or events;
- `produces`: expected boundary outputs;
- `required_decisions`: decisions that must exist before a host proceeds;
- `forbidden_authority`: authority the step must not claim;
- `metadata`: optional host metadata.

A step is not a prompt, raw intent, scheduled job, subprocess command, UI action, or transport message. Inputs containing `raw_intent` or `prompt` are rejected by `validate_orchestration_step()`.

## Allowed Stages

The legacy `v0.1` contract retained from the 0.2 line allows these stages:

- `admission`;
- `policy_check`;
- `trust_check`;
- `runner_gate`;
- `between_step_control`;
- `receipt_review`;
- `profile_handoff`.

Unknown stages fail validation so a host cannot silently smuggle runtime behavior into the kernel.

## Forbidden Authority

An orchestration step must not claim:

- `llm_agent_loop`;
- `workflow_scheduler`;
- `operator_ui`;
- `credential_access`;
- `live_execution`;
- `carrier_adapter`.

These remain runtime-owned even when GovEngine produces the control decision that tells the runtime to pause, abort, continue, review, or hand off.

## Relationship To OODA

OODA decisions answer whether the next step should continue, pause, abort, cool down, degrade to dry run, require owner review, or replan. The orchestrator model describes the neutral handoff around those decisions. It does not run the loop itself.

## Release Use

Public API, boundary docs, and tests agree that orchestration is deterministic
control metadata only. Runtime scheduling, UI, adapters, credentials, and live
execution must remain outside GovEngine.
