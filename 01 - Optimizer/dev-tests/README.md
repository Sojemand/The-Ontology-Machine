# Dev Tests

Local development test suite for `01 - Optimizer`.

```bat
bootstrap.bat
run-tests.bat
```

- The suite combines unit/contract tests with a small versioned corpus under
  `dev-tests/corpus/`.
- The corpus covers one real Markdown end-to-end case and one anonymized
  vision-payload golden case.
- Packaging/runtime contract tests additionally check `check-runtime.bat`,
  `runtime/runtime-manifest.json`, `installer.bat`, `build-installer.bat` and
  the installed contract-only slot without a local launcher.
- LLM OCR E2E with real binary documents and provider calls intentionally stays
  outside the repo so the suite remains offline and reproducible without
  secrets.
- `dev-tests/.venv` is the expected dev-test runtime. `.pytest-local-tmp` and
  `pytest-cache-files-*` in the module root are disposable local artifacts.
