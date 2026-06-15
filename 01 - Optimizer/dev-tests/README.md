# Dev Tests

Lokale Dev-Test-Suite fuer `01 - Optimizer`.

```bat
bootstrap.bat
run-tests.bat
```

- Die Suite kombiniert Unit-/Contract-Tests mit einem kleinen versionierten Corpus unter `dev-tests/corpus/`.
- Der Corpus deckt einen echten Markdown-End-to-End-Fall und einen anonymisierten Vision-Payload-Golden-Fall ab.
- Packaging-/Runtime-Vertragstests pruefen zusaetzlich `check-runtime.bat`, `runtime/runtime-manifest.json`, `installer.bat`, `build-installer.bat` und den installierten Contract-only Slot ohne lokalen Launcher.
- LLM-OCR-E2E mit echten Binaerdokumenten und Provider-Calls bleibt bewusst ausserhalb des Repos, damit die Suite offline und ohne Secrets reproduzierbar bleibt.
- `dev-tests/.venv` ist die erwartete Dev-Test-Runtime; `.pytest-local-tmp` und `pytest-cache-files-*` im Modulroot sind disposable Local-Artefakte.
