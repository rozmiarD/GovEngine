# Governance conformance corpus

GovEngine ships `govengine/conformance/v1` as plain JSON so another
implementation can consume the cases without importing Python fixture
builders. The manifest lists 41 cases: five valid flows and 36 negative
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

## Coverage inventory

The original wheel-shipped v1 manifest had 33 cases: 27 GovEngine-owned cases
and six RExecOp-owned `consume_decision` cases. The latter remain shared
serialized inputs, but GovEngine deliberately reports `not_applicable` because
atomic claim, lifecycle and pre-I/O execution remain RExecOp-owned.

The 41-case manifest adds eight formerly unit-only negative vectors with a
GovEngine owner: non-ASCII binding, timezone-naive activation timestamp,
approval not-yet-valid, inactive activation states (superseded, revoked and
expired), signed-decision body tampering and conflicting policy rules. The
resulting shared corpus has 35 GovEngine-owned and six RExecOp-owned cases.
`tests/conformance/v2` remains a test-only additive boundary fixture; it is not
a wheel-shipped interoperability manifest or evidence of another consumer.

The checked-in JSON is generated deterministically:

```bash
python scripts/generate_conformance_corpus.py --check
pytest -q tests/test_conformance_corpus.py
```

Regeneration is an explicit contract change and must be reviewed together with
reason-code, digest and migration changes. Passing the corpus proves
conformance to these bounded cases only. It does not prove malicious-host
resistance, production adapter correctness or an implementation in another
language. `--check` rejects missing, extra or hand-edited JSON and manifest
drift. `validate_v1_freeze.py` separately freezes the facade/schema inventory;
immutable RC records retain the manifest digest from their published source and
are never rewritten by corpus regeneration.
