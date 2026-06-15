Vision Pipeline Client Frontend

Kanonische Handover-Doku:
- `README.md`

Operatorische Einstiegspunkte:
- Chat-Start: `start.bat`
- Konfiguration: `config.bat`
- Per-User-Installation/Reparatur: `installer.bat`
- Runtime-Build: `build-runtime.bat`
- Dev-Tests: `dev-tests\\bootstrap.bat` und `dev-tests\\run-tests.bat`

Laufzeitmodell:
- Immutable Produktartefakte liegen im Modulroot.
- Die kanonische Produktquelle liegt unter `client_frontend\\`.
- `src\\` und `server\\` sind pfadstabile Surface- und Launcher-Fassaden.
- Generierte Build-Checks gehoeren nicht zur Produktquelle und bleiben ueber lokale Ignore-Regeln aus `src\\` heraus.
- Mutable Laufzeitdaten liegen standardmaessig unter `%LOCALAPPDATA%\\Enterprise Stack\\Client Frontend` oder unter `VISION_PIPELINE_CLIENT_FRONTEND_HOME`.
- Der externe App-Home enthaelt `config\\`, `state\\` und `logs\\`.

Stabile Test- und Import-Seams:
- Browser-Surfaces unter `src\\` bleiben stabil.
- Server-Surfaces unter `server\\` bleiben stabil.
- Die Runtime-Pfad-Seams `client_frontend\\runtime_paths.js` und `client_frontend\\runtime_paths\\*` bleiben stabil.

Deploy:
- `tools\\deploy.ps1` kopiert den immutable Payload inklusive `client_frontend\\`, `server\\`, `shared\\`, `runtime\\`, `node\\`, `app\\`, `assistant\\` und `data\\`.
- `tools\\installer.ps1` installiert standardmaessig nach `%LOCALAPPDATA%\\Enterprise Stack\\Client Frontend\\app` oder in den per `VISION_PIPELINE_CLIENT_FRONTEND_HOME` gesetzten App-Home.

Hinweise:
- Es gibt in diesem Refactor bewusst weiterhin kein `module-manifest.json`; die Frontend-Surface ist nicht sauber als Orchestrator-Action-Contract ableitbar.
- `shared\\provider-catalog.json` bleibt bewusst als root-nahe immutable Metadatenquelle ausserhalb des Package-Roots.
- `client_frontend\\` bleibt die einzige Implementierungsquelle; `src\\` und `server\\` sind duenne Fassaden.
