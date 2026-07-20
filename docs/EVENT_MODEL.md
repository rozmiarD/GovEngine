# Event Model

> Legacy experimental compatibility surface. RExecOp owns current runtime event
> ingestion, lifecycle and scheduling mechanics. These records remain outside
> `govengine.v1` and the canonical v1 authorization path.

GovEngine event contracts are neutral metadata for orchestration and review. They are not a scheduler, queue, carrier payload, credential container, subprocess request, or live execution instruction.

## What Events Are

`GovEvent` records a small fact that a host runtime may pass into GovEngine-controlled orchestration:

- artifact state changed;
- policy decision recorded;
- trust decision recorded;
- runner receipt recorded;
- OODA control decision recorded;
- profile handoff requested or completed.

`EventEnvelope` wraps the event with source, correlation id, sequence, and metadata. The envelope is transport-neutral: it does not deliver itself, schedule itself, or carry adapter-specific payloads.

## Payload Boundary

Event payloads may carry compact references and status metadata. They must not carry:

- raw intent or prompts;
- credentials, secrets, tokens, passwords, or API keys;
- live commands, subprocess requests, shell fragments, or command arrays;
- carrier delivery or transport payloads.

`validate_gov_event()` and `validate_event_envelope()` reject those fields recursively.

## Relationship To Orchestration

Events are inputs and outputs around `OrchestrationStep` records. They tell the deterministic control shell what changed. They do not decide what to run, when to run it, or how to deliver it to an operator or carrier.

## Relationship To Runtime

The runtime owns event-loop liveness, queues, schedules, transports, UI, credentials, and concrete execution. GovEngine may validate an event envelope and use it as control metadata; it must not become the event bus.

## Release Use

Event docs, public exports, surface metadata, and tests agree that events are
compact governance metadata only. Runtime scheduling, carrier delivery,
credential handling, and live execution stay outside GovEngine.
