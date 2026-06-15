# Dev Tests

Local development test suite for `00 - Orchestrator`.

```bat
bootstrap.bat
run-tests.bat
```

- The suite protects the package surfaces `orchestrator.main`,
  `orchestrator.orchestrator_contract` and `orchestrator.ui` against entrypoint
  and monkeypatch regressions.
- Pipeline test helpers live flat under `tests/`; there is no separate
  `pipeline_support/` subtree anymore.
- Packaging regressions additionally check `check-runtime.bat`,
  `build-installer.bat`, `runtime/runtime-manifest.json`, the staged
  `release-manifest.json` and the installed module slot with and without
  sibling modules.

## Regression Fixtures

- Replay-based regressions live under `fixtures/regression/`.
- These cases start the real Orchestrator end-to-end run but feed it versioned
  stage artifacts instead of live modules.
- The current core cases are derived from real runs and anonymized before
  check-in.
- A live capture of a synthetic receipt is also frozen as a replay case.
- Additional synthetic replay cases cover product-critical review/retry paths
  that were not present in the small real-case set.
- The additional `synthetic_*` cases reproduce only format, profile, page-count
  and artifact-structure patterns from a local artifact folder; they contain no
  production content.
- Golden expectations check only stable outputs such as summary,
  `pipeline_state.json`, bundle manifests and central artifact paths.
