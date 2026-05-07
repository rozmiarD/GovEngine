# Validation

Local scaffold validation:

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
```

Current focused tests cover:

- public module imports;
- action compilation;
- dry-run result assembly;
- neutral scope helpers;
- approved execution spec and ticket helper shapes;
- SCLite lifecycle verifier seam availability.

Non-claims:

- these tests do not execute live targets;
- these tests do not prove Ravenclaw runtime integration;
- these tests do not validate Logdash or public snapshot publishing.
