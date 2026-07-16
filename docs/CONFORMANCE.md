# Governance conformance corpus

GovEngine ships `govengine/conformance/v1` as plain JSON so another
implementation can consume the cases without importing Python fixture
builders. The manifest lists 33 cases: five valid flows and 28 negative
security/binding cases.

Each case declares:

- one operation and serialized input;
- expected status and stable reason code for both GovEngine and RExecOp;
- expected binding digests or explicit `not_applicable`;
- maximum schema version;
- forbidden output keys for secrets, raw targets and raw output.

`govengine.conformance` validates and executes GovEngine-owned operations.
RExecOp consumes the same wheel-shipped files and is responsible for
`consume_decision` cases covering runtime instance, attempt, lease, fencing
and nonce claim semantics. GovEngine reports those cases as
`not_applicable`; it does not simulate runtime atomicity.

The checked-in JSON is generated deterministically:

```bash
python scripts/generate_conformance_corpus.py --check
pytest -q tests/test_conformance_corpus.py
```

Regeneration is an explicit contract change and must be reviewed together with
reason-code, digest and migration changes. Passing the corpus proves
conformance to these bounded cases only. It does not prove malicious-host
resistance, production adapter correctness or an implementation in another
language.
