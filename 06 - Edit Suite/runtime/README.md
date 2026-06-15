# Edit Suite Runtime

- `runtime/python`: bundled CPython runtime.
- `runtime/wheelhouse`: offline source for rebuilds.
- `runtime/requirements.lock.txt`: reproducible runtime pins.
- `runtime/runtime-manifest.json`: runtime and provenance contract.
- `run.bat`: runs a runtime provenance preflight before GUI startup.
- `EDIT_SUITE_OWNER_CONTRACT_TIMEOUT_SECONDS`: optional override for
  owner-local contract calls, default `1800`.
