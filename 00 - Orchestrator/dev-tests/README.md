# Dev Tests

Lokale Dev-Test-Suite fuer `00 - Orchestrator`.

```bat
bootstrap.bat
run-tests.bat
```

- Die Suite sichert die package-surfaces `orchestrator.main`, `orchestrator.orchestrator_contract` und `orchestrator.ui` explizit gegen Entrypoint- und Monkeypatch-Regressionen ab.
- Pipeline-Testhilfen liegen flach direkt unter `tests/`; ein separater `pipeline_support/`-Unterbaum existiert nicht mehr.
- Packaging-Regressionen pruefen zusaetzlich `check-runtime.bat`, `build-installer.bat`, `runtime/runtime-manifest.json`, das gestagte `release-manifest.json` und den installierten Modulslot mit sowie ohne Schwester-Module.

## Regression Fixtures

- Replay-basierte Regressionen liegen unter `fixtures/regression/`.
- Diese Faelle starten den echten Orchestrator-End-to-End-Lauf, speisen ihn aber mit versionierten Stage-Artefakten statt mit Live-Modulen.
- Die aktuellen Kernfaelle sind aus echten Kundenlaeufen abgeleitet und vor dem Einchecken anonymisiert worden.
- Zusaetzlich ist ein Live-Capture eines synthetischen Kassenbons als Replay-Fall eingefroren worden.
- Ergaenzend decken synthetische Replay-Faelle die produktkritischen Review-/Retry-Pfade ab, die im kleinen Realfall-Satz nicht vorkamen.
- Die zusaetzlichen `synthetic_*`-Faelle bilden nur Format-, Profil-, Seitenzahl- und Artefaktstruktur-Muster aus einem lokalen Artefaktordner nach; sie enthalten keine Produktionsinhalte.
- Die Golden-Erwartungen pruefen nur stabile Outputs wie Summary, `pipeline_state.json`, Bundle-Manifeste und zentrale Artefaktpfade.

