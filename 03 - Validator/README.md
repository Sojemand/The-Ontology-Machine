# 03 - Validator Vision

Host-only Validator fuer `structured.json` aus Vision-, File- und Table-Interpretern.

## Zweck

- validiert einzelne `structured.json`-Dateien oder ganze Ordner
- dispatcht strikt ueber `processing.interpreter_profile`
- prueft Vision-Dokumente gegen Kontext, Fields, Rows und `content.free_text`
- prueft File-Dokumente gegen kanonische Raw-Evidence aus `*.raw.json`
- prueft Table-Dokumente raw-backed gegen deterministische Tabellenwahrheit aus dem aktiven Optimizer-Slot
- erzeugt pro Dokument genau einen JSON-Report

## Betrieb

- Die einzige Debug-GUI liegt im `00 - Orchestrator`.
- Das Modul exponiert lokal nur noch den dateibasierten Contract `validator_vision.orchestrator_contract` sowie Runtime-/Installer-Helfer.
- Der additive Debugpfad laeuft headless ueber `debug_run` und schreibt nur unter dem vom Host zugewiesenen `session_root`.
- Die produktiven Contract-Actions `validate_document` und `healthcheck` bleiben unveraendert.

## Runtime und Pfade

- self-contained Runtime unter `runtime/python`
- Runtime-Rebuild erwartet eine explizite portable Python-Quelle via Root-Tooling/`-SourceRuntime` oder `tools/python-runtime-source`
- Runtime-Rebuild und Per-User-Installer publizieren immutable App-/Runtime-Baeume aus Stage-Ordnern und rollen bei fehlgeschlagenem Runtime-Check auf den vorherigen Stand zurueck.
- mutable Daten standardmaessig unter `%LOCALAPPDATA%\Enterprise Stack\Validator Vision`
- session-lokales Home-Overlay im Debug Host ueber `VALIDATOR_VISION_HOME`
- lokale Defaults weiter unter `config/config.json`

| Pfad | Rolle | Mutable |
| --- | --- | --- |
| `validator_vision/` | Produktcode und Contract-Surfaces | nein |
| `runtime/` | portable Runtime und Packaging-Metadaten | nein nach Build |
| `config/config.json` | gebuendelte Defaults | nein |
| `%LOCALAPPDATA%\Enterprise Stack\Validator Vision` | produktive Config-, Log-, State- und Output-Homebase | ja |

## Orchestrator Contract

- `validate_document`
  - produktiver Einzelrequest mit `structured_path`, `validation_output_path`, optional `raw_path`
  - `raw_path` ist fuer `file` und `table` der kanonische Raw-backed Evidence-Pfad
- `healthcheck`
  - Runtime- und Contract-Selbsttest
- `debug_run`
  - headless Debugpfad fuer den Orchestrator
  - Pflichtfelder: `action`, `mode`, `session_root`, `output_root`
  - `output_root` muss innerhalb von `session_root` liegen; fremde Schreibziele werden fail-closed abgelehnt
  - `single`: `source_path`
  - `batch`: `input_root`
  - optionale `options`: `raw_evidence.raw_path`, `raw_evidence.raw_root`, `check_toggles`

Debug-Session-Artefakte:

- `request.json`
- `response.json`
- `snapshot.json`
- `result.json`
- `run.log`
- `cancel.request`
- `outputs/validation_reports/*.vision_validation_report.json`
- `outputs/validation_reports/*.files_validation_report.json`
- `outputs/validation_reports/*.vision_validation_report.json` fuer `table`
- `outputs/config_snapshot.json`
- `outputs/report_index.json`

## Interne Surfaces

- `validator_vision.orchestrator_contract`
  - stabile Subprozess-Surface fuer Orchestrator und Debug Host
- `validator_vision.edit_contract`
  - owner-lokale Edit-Surface fuer `06 - Edit Suite`
- `validator_vision.validator`
  - fachliche Validierungslogik
- `validator_vision.main`
  - interne headless CLI fuer `validate` und `validate-batch`; keine lokale GUI- oder Maintenance-Surface

## Edit Suite

- Owner-local Edit-Contract: `validator_vision.edit_contract`
- Additive Fast-Path-Action: `read_bundle` fuer die Edit Suite; Produkt-Contract und Manifest-Actions bleiben unveraendert
- Edit-Surfaces:
  - `validator.settings`
  - `validator.report_preview_policy`
  - `validator.debug_capabilities`
- `validator.settings` und `validator.report_preview_policy` schreiben beide owner-lokal in die mutable `config/config.json` unter dem App-Home.
- `validator.debug_capabilities` spiegelt die read-only Manifest-Wahrheit fuer Contract- und Debug-Capabilities.
- Report-Dateien und Debug-Session-Artefakte bleiben bewusst ausserhalb des Edit-Contracts.

## Entwicklung

Portable Runtime pruefen:

```bat
check-runtime.bat
```

Per-User-Installation:

```bat
installer.bat
```

Dev-Tests:

```bat
dev-tests\bootstrap.bat
dev-tests\run-tests.bat
```

Installer stage/compile:

```bat
build-installer.bat --skip-runtime-build
build-installer.bat --skip-runtime-build --compile
```

`--compile` setzt Inno Setup 6 (`ISCC.exe`) auf der Build-Maschine voraus.

## Report

Pro Dokument wird profilabhaengig genau ein Report geschrieben:

- Vision: `*.vision_validation_report.json`
- File: `*.files_validation_report.json`
- Table: `*.vision_validation_report.json`

Moegliche Resultate:

- `PASS`
- `WARN`
- `FAIL`

## Safety Limits

- JSON-Eingaben werden vor dem Laden auf eine maximale Groesse von 16 MiB begrenzt.
- `structured.json` muss fuer `content`, `context`, `source`, `processing`, `content.fields` und `content.rows` die erwarteten Container-Shapes einhalten; falsche Shapes werden fail-closed abgelehnt.
- Batch-Discovery stoppt bei mehr als 5000 `*.structured.json`-Dateien.
- Raw-Indexing stoppt bei mehr als 5000 `*.raw.json`-Dateien.
- Automatisch abgeleitete Report-Dateinamen werden fuer Windows-Pfadbudgets stabil gekuerzt und gehasht.
- Kaputte Raw-Dateien im `raw_root` werden nicht still verschluckt; fehlgeschlagene Raw-Aufloesung nennt die Anzahl uebersprungener Raw-Dateien.
- `debug_run` erzeugt `report_index.json` und Antwort-Outputs ausschliesslich aus den Reports des aktuellen Laufs; stale Dateien im Session-Output werden nicht als aktuelle Runtime Truth rekonstruiert.
- File-Raw-Claims ignorieren isolierte OCR-Edge-Seitennummern in mehrseitigen Dokumenten, damit Footer/Page-Label wie `21` nicht als fehlender fachlicher Numeric Claim failen. Tabellenzellen und nicht-isolierte Werte bleiben claims-relevant.

## Regressionen

- Dev-Tests decken Contract-, Runtime-, Installer-, Edit-Contract- und Pfadgrenzen ab.
- Golden-Report-Regressionen existieren fuer Vision-, File- und Table-Profile.
- Table-Profil wird mit `deterministic_extract.tables_base` gegen raw-backed Claims getestet.

## Abweichungslog

| Modul | Regel | Abweichung | Grund | Owner | Follow-up Datum | Risiko wenn offen |
| --- | --- | --- | --- | --- | --- | --- |
| 03 - Validator | SHOULD: Regressionen mit realistischen oder echten Artefakten | Golden-Regressionen fuer Vision/File/Table sind vorhanden; der reale, anonymisierte Dokumentkorpus bleibt klein | echte Kundendokumente sind noch nicht als versionierte Fixtures freigegeben | Pipeline Cleanup | 2026-05-15 | Seltene Dokumentvarianten koennen spaeter Drift zeigen |
