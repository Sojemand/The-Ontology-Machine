# Interpreter

`02 - Interpreter` ist das zusammengefuehrte Interpreter-Modul der Vision
Pipeline. Es besitzt genau einen oeffentlichen Modulslot mit
`module_key = "interpreter"` und verarbeitet einen kanonischen
`interpreter.request.json`-Vertrag fuer zwei fachliche Profile:

- `vision`: bild- und OCR-lastige Requests
- `file`: born-digital und dateibasierte Requests

Das Downstream-Feld `processing.interpreter_profile` bleibt bewusst stabil und
ist weiterhin `vision` oder `file`.

## Contract

- Entry-Point: `llm_interpreter.orchestrator_contract`
- Actions:
  - `interpret_document`
  - `healthcheck`
  - `debug_run`
  - `generate_llm`

Der produktive Request ist vereinheitlicht. Legacy-Shapes wie `pages` und
`file_reference` gehoeren nicht mehr zum produktiven Vertrag.
`generate_llm` ist eine generische Provider-Bruecke fuer den Semantic Control
Kernel. Sie nimmt Messages, optionales JSON-Schema und Runtime-Settings vom
Orchestrator entgegen, nutzt nur die ephemer injizierte Orchestrator-Auth und
liefert eine `kernel.llm_provider_response.v1`-kompatible Antwort zurueck.

## Runtime

- Immutable Payload:
  - `llm_interpreter/`
  - `runtime/`
  - `tools/`
  - `module-manifest.json`
- Mutable Laufzeitdaten:
  - `%INTERPRETER_HOME%`
  - `%LOCALAPPDATA%\Enterprise Stack\Interpreter`
  - Quellslot-Fallback `.appdata/`
- Erwartete mutable Pfade:
  - `config/`
  - `state/`
  - `output/`
  - `logs/`

`config/.env` enthaelt nur owner-lokale, nicht-sensitive Runtime- und
Limit-Werte. Auth, Modellwahl und `max_output_tokens` bleiben
orchestrator-owned. Auch `generate_llm` darf keine modul-lokalen Credentials
lesen oder persistieren, sondern laeuft ueber dieselbe `VISION_PROVIDER_*`-Env
wie `interpret_document` und `healthcheck`.

## Edit Suite

Owner-lokale Surfaces fuer `06 - Edit Suite`:

- `interpreter.runtime_policy_env`
- `interpreter.execution_limits`
- `interpreter.prompt_bundle`
- `interpreter.output_contract_preview`
- `interpreter.debug_capabilities`

Diese Surfaces gelten fuer beide Profile des vereinten Moduls. Profilunterschiede
leben in der Interpreter-Logik und im Request, nicht in getrennten
Modulslots. Das editierbare Prompt-Bundle liegt unter `config\prompt_bundle\`.

## Packaging

- Per-user-Installationsziel:
  - `%LOCALAPPDATA%\Enterprise Stack\Interpreter\app`
- `tools\build-runtime.bat` baut und validiert die portable Runtime fuer
  Dev- und Packaging-Laeufe.
- `installer.bat`, `check-runtime.bat` und `build-installer.bat` validieren
  Quellslot und Zielinstallation.
- Die Runtime bleibt headless und shippt kein Tcl/Tk.
- Das Modul erwartet produktive Auth nur ueber orchestrator-owned Runtime-Env.

## Tests

```bat
dev-tests\bootstrap.bat
dev-tests\run-tests.bat
```

Die Dev-Suite prueft Contract, Prompt-Bundle, Runtime, Packaging und den
vereinheitlichten Edit-Contract.
