# Orchestrator

Standalone-Orchestrator fuer die Vision Pipeline.

## Runtime Build

- Zielplattform: Windows x64
- Gebuendelte Runtime: CPython 3.11 x64
- Offline-Quelle fuer Runtime-Pakete: `runtime/wheelhouse`
- Runtime-Vertrag: `runtime/runtime-manifest.json`
- Build-Befehl:

```bat
build-runtime.bat
```

- Portable Runtime pruefen:

```bat
check-runtime.bat
```

## Per-User Installation

- Installationsziel: benutzerschreibbarer Ordner
- Keine Adminrechte erforderlich
- Kein vorinstalliertes Python erforderlich
- Kein Internet fuer den Betrieb erforderlich
- Inno-Setup-Stage oder Installer bauen:

```bat
build-installer.bat
build-installer.bat --compile
```

- Default-Ziel fuer den Installer: `%LOCALAPPDATA%\Programs\Vision Pipeline\00 - Orchestrator`

Der Orchestrator bleibt bewusst ein **Modulslot** im Pipeline-Root. Auch nach Installation werden die in `module-registry.json` referenzierten Nachbarmodule relativ zum Orchestrator im selben Pipeline-Root erwartet.

## Edit Contract

- Der Produkt-Contract liegt unter `orchestrator.orchestrator_contract`.
- Fuer die Edit Suite existiert zusaetzlich der owner-lokale, headless Contract `orchestrator.edit_contract`.
- Aufruf:

```bat
python -m orchestrator.edit_contract --request <request.json> --response <response.json>
```

- Der Edit-Contract beschreibt und bearbeitet ausschliesslich die vier owner-lokalen Policy-Surfaces:
  - `orchestrator.route_intake_policy`
  - `orchestrator.execution_policy`
  - `orchestrator.health_dependency_policy`
  - `orchestrator.artifact_publication_policy`
- In der Edit Suite erscheinen diese vier Surfaces als gefuehrter Policy-Slot:
  - Summary liefert die Snapshot-Karten `Routing Snapshot`, `Execution Snapshot`, `Health Profiles` und `Artifact Layout`
  - Settings nutzt einen Guided-Editor mit Top-Level-Gruppen, Typed Inputs fuer einfache Werte und JSON-Teil-Editoren fuer verschachtelte Policy-Maps
- GUI-State unter `state/ui_state.json`, `state/runtime_settings.json`, Credentials und Protokollkonstanten bleiben bewusst ausserhalb dieses Edit-Contracts.
- Eine eng begrenzte Produkt-Contract-Action `activate_corpus_context` darf den Orchestrator-owned Corpus-Kontext setzen. Sie validiert, dass die Ziel-DB existiert, eine Datei ist und innerhalb des angegebenen `corpus_output_folder` liegt; danach setzt sie `selected_corpus_db_path`, `corpus_output_folder`, `semantic_release_mode=database_default` und leert `semantic_release_path`.

## Entwicklung

Lokale Dev-Test-Suite mit derselben Hauptversion wie die gebuendelte Runtime:

```bat
dev-tests\bootstrap.bat
dev-tests\run-tests.bat
```

Alternativ laufen alle Suiten zentral ueber `run-dev-tests.bat --module "00 - Orchestrator"`.

## Main-Architektur und Debug

- `orchestrator.main` ist jetzt die pfadstabile Package-Surface fuer den Startpfad des Moduls.
- Die Main-Stufen sind explizit getrennt:
  - `surface`: Parser-Bau und minimaler Entrypoint-Dispatch
  - `workflow`: Logging-Setup, Startup-Prerequisites und GUI-Start
- `python -m orchestrator`, `run.bat` und `from orchestrator import main` bleiben kompatibel.
- Debugging entlang der Main-Stufen:
  - Startparameter zuerst in `surface`
  - Runtime-/GUI-Startprobleme in `workflow`

## Regression-Layer

- Unter `dev-tests/fixtures/regression/` liegt eine kleine replay-basierte Regressionsebene mit kuratierten End-to-End-Faellen.
- Die Regressionen laufen offline: der Orchestrator wird echt ausgefuehrt, die Stage-Artefakte kommen aber aus versionierten Replay-Files statt aus Live-Modulaufrufen.
- Die ersten beiden Replay-Faelle basieren auf anonymisierten echten Kundenlaeufen und wurden fuer die Tests strukturerhaltend bereinigt.
- Aktuell abgedeckte Faelle:
  - `happy_path`: erfolgreicher Ein-Dokument-Run bis `corpus.db`
  - `receipt_live`: Live-Capture eines synthetischen Kassenbons mit echten Schwester-Modulen, eingefroren als Replay-Fall
  - `validator_fail`: wiederholter Validator-Fehler mit finalem Error-Case-Snapshot
  - `interpreter_review`: synthetischer Interpreter-Review-Pfad mit finalem Error-Case-Snapshot nach drei Versuchen
  - `normalizer_review`: synthetischer Normalizer-Review-Pfad mit finalem `needs_review`-Erfolg inklusive `normalized`-Artefakt
- Der Reset-Roundtrip wird in derselben Suite gezielt auf Basis von `validator_fail` geprueft, damit Rueckverschiebung aus `Error Cases` sowie der Erhalt von Erfolgsartefakten und `corpus.db` gemeinsam regressionsstabil bleiben.
- Ausfuehrung:

```bat
python -m pytest dev-tests\tests\test_pipeline_regression.py
```

## Laufzeitmodell

- Die GUI arbeitet mit genau einem `Artefakt Folder`.
- GUI-Einstellungen werden ohne separaten `Speichern`-Schritt debounce-basiert in `state/ui_state.json` persistiert und spaetestens bei Focus-Out, Tabwechsel, Start und App-Close geflusht.
- Nicht-GUI-Policy-Defaults liegen owner-lokal unter `config/*.json` und sind die einzige editierbare Truth fuer Routing-, Execution-, Health- und Artifact-Publication-Policy.
- Unter diesem Root schreibt der Orchestrator die persistenten Erfolgsartefakte route-lokal:
  - `Documents/originals/`, `raw_extracts/`, `page_images/`, `requests/`, `structured/`, `validation/`, `normalized/`, `logs/`
  - `Error Cases/<Modulname>/<Route-Name>/originals|raw_extracts|page_images|requests|structured|validation|normalized|logs/`
- Dokumentbezogene Working-Artefakte entstehen waehrend des aktiven Laufs run-scoped unter `state/pipeline/runs/<run_id>/d.<hash>/source|artifacts|requests|structured|validation|normalized|logs/`.
- `requests`, `structured`, `validation`, `normalized` und der dokumentbezogene Run-Log liegen nicht global am Artefakt-Root; sie werden nur bei finalem Erfolg in die jeweilige Route publiziert oder bei finalem Fehler/Abbruch ausschliesslich im Error-Tree eingefroren.
- Es gibt keinen separaten `Error Folder` und keinen separaten Review-Sammelpfad mehr.
- Final erfolgreiche Dokumente verschieben ihr Original erst am Ende nach `Documents/originals/...` und publizieren erst dann `raw_extracts`, `page_images`, `requests`, `structured`, `validation`, `normalized` und den dokumentbezogenen Run-Log in `Documents`.
- Finale Fehler-, Review- und Abbruchfaelle verschieben das Original kanonisch nach `Error Cases/<Modulname>/<Route-Name>/originals/...` und duerfen nach Abschluss keine dokumentbezogenen Artefakte in `Documents` hinterlassen.
- Die manuelle `reset`-Action bzw. der Button `Reset Error Bundle` bereinigt nur `Error Cases` plus einen eventuellen Legacy-`errors/`-Baum, legt dort archivierte Originale nach Moeglichkeit ins Input-Verzeichnis zurueck und laesst `corpus.db`, Erfolgsartefakte sowie erfolgreiche State-Eintraege unveraendert.
- Der zusaetzliche Status-Button `Reset Pipeline Logs` loescht die versteckte Run-Historie unter `state/pipeline/` sowie `state/orchestrator.log` inklusive Backups und Legacy-`vision_orchestrator.log*`, ohne Artefakte, `corpus.db`, `debug_sessions/`, Credentials oder Settings anzufassen.
- `state/pipeline/pipeline_state.json` haelt den Pipeline-State ausserhalb des Artefakt-Roots; transiente per-run Dateien und Live-Run-Logs liegen unter `state/pipeline/runs/`, bis `Reset Pipeline Logs` diesen Bereich bewusst leerraeumt.
- Kernel-owner Runs ueber den Produkt-Contract duerfen die Queue auf die vom
  Kernel bestaetigten `input_files`-Content-Hashes beschraenken. Dadurch kann
  die GUI weiterhin retrybare `pipeline_state.json`-Records einsammeln, aber
  Kernel-gefuehrte Manual-Ingestion zieht keine Error-Case-Records heimlich aus
  dem Pipeline-State nach.
- Der Live-Snapshot fuer `Error Cases` zaehlt nur recoverbare Quelldateien
  unter `Error Cases/**/originals/**`; eingefrorene Requests, Raw Extracts,
  Structured/Validation-Dateien und Logs sind Diagnoseartefakte und zaehlen
  nicht als Error-Case-Quellen.
- Generische Debug-Sessions fuer Schwester-Module liegen getrennt davon unter `state/debug_sessions/<session_id>/<module_key>/` mit `request.json`, `response.json`, `snapshot.json`, `result.json`, append-only `run.log`, optional `cancel.request` und dauerhaften Testartefakten unter `outputs/`.
- Der Debug Host besitzt eigene Eingabepfade in `state/debug_host_state.json`: `Source Path` fuer Single-Laeufe sowie `Input Path` fuer Scan/Batch. Diese Pfade werden beim Start nicht aus dem Haupttab-Input, Pipeline-State oder Kernel-Artefact-State abgeleitet.
- Der Debug-Tab-Button `Reset Debug Output` loescht nur diesen `state/debug_sessions/`-Baum inklusive `outputs/`, `request.json`, `response.json`, `snapshot.json`, `result.json`, `run.log`, `home/` und `cancel.request`; Replay-Importe, `state/debug_host_state.json` und der normale Pipeline-Reset bleiben davon unberuehrt.

## Route- und Intake-Policy

- Logische Stages der Vision-Pipeline:
  - `Intake`
  - `Optimizer`
  - `Request Enrichment`
  - `Interpreter`
  - `Validator`
  - `Normalizer`
  - `Corpus Builder`
  - `Embeddings`
- Live-Foederationsmodule:
  - `optimizer`
  - `interpreter`
  - `validator`
  - `normalizer`
  - `corpus_builder`
- Feste Route-Familien:
  - `Documents`: `.jpg`, `.jpeg`, `.png`, `.tif`, `.tiff`, `.bmp`, `.webp`, `.eml`, `.emlx`, `.mbox`, `.msg`, `.oft`, `.pst`, `.ost`, `.doc`, `.docx`, `.odt`, `.rtf`, `.txt`, `.md`, `.markdown`, `.yaml`, `.yml`, `.toml`, `.ini`, `.cfg`, `.conf`, `.env`, `.properties`, `.pdf`
- PDF-Regel:
  - born-digital PDF -> `optimizer_profile=file` + `interpreter_profile=file`
  - Scan-PDF -> `optimizer_profile=vision` + `interpreter_profile=vision`
- Der Preflight arbeitet zweiphasig:
  - zuerst Discovery plus Intake-Klassifikation
  - danach Healthcheck nur fuer die in der Queue wirklich benoetigten Live-Module; fuer das `vision`-Profil des `optimizer` wird `optimizer_ocr` als LLM-OCR-Abhaengigkeit verlangt, fuer das file-Profil werden zusaetzlich feature-skopierte `required_dependencies` aus der Ready-Queue profiliert
- Die GUI zeigt Auto-Routing read-only ueber `Route Family`, `Optimizer`, `Interpreter` und `Intake Reason`.

## Runtime Layout

| Pfad | Rolle | Mutable |
| --- | --- | --- |
| `orchestrator/` | Produktcode und package-surfaces | nein |
| `config/` | owner-lokale Policy-Defaults fuer Edit Suite und Runtime | ja |
| `runtime/python` | gebuendelte CPython-Runtime gemaess `module-manifest.json` | nein |
| `runtime/runtime-manifest.json` | Packaging- und Runtime-Provenance-Vertrag | nein |
| `runtime/wheelhouse` | Offline-Buildquelle fuer Runtime-Neubauten | nein nach Build |
| `state/` | lokaler UI-, Credential- und GUI-Log-Zustand | ja |
| `state/pipeline/` | `pipeline_state.json` plus transiente `runs/` fuer aktive Laeufe | ja |
| `<Artefakt Folder>/Documents|Error Cases` | persistente Erfolgs- und Fehlerartefakte des Produktlaufs | ja |
| `%LOCALAPPDATA%\Programs\Vision Pipeline\00 - Orchestrator` | installierter Modulslot fuer Endnutzer | ja fuer `state/` und `config/`, nein fuer Payload |

`check-runtime.bat` validiert nur den lokalen Bundle- und Provenance-Vertrag. Die Foederations-Nachbarschaft bleibt separat und wird erst ueber den Startup-Preflight gegen `module-registry.json` geprueft.

## Semantic Release

- Optional kann in der GUI eine `Semantic Release`-Datei gesetzt werden.
- Vor einem Run aktiviert der Orchestrator diesen Release einmalig fuer die Ziel-`corpus.db`.
- Ohne gesetzte Release-Datei verwendet der Orchestrator den bereits aktiven Release-Stand des Corpus Builders.

## Credentials Resolver

- `orchestrator.credentials` ist die pfadstabile Surface fuer die zentrale Auth-Ownership des Orchestrators.
- Der neue GUI-Tab `Credentials` liegt fest zwischen `Status` und `Log`; `Status` bleibt Default-Tab.
- `state/ui_state.json` bleibt strikt credentials-frei und speichert weiterhin nur Pfad- und Mode-Felder der Hauptoberflaeche.
- Nicht-sensitive Credential-Metadaten liegen separat in `state/credentials_state.json`:
  - Presence-Flags fuer `llm_shared`, `optimizer_ocr` und `embeddings`
  - OAuth-Status-Metadaten ohne Tokens oder Secrets
  - Legacy-`auth_mode` bleibt lesbar, wird aber nicht mehr als user-owned Zustand persistiert
- Nicht-sensitive Modellkatalog-Metadaten liegen separat in `state/model_catalog_state.json`:
  - getrennte Gruppen `llm_shared`, `optimizer_ocr` und `embeddings`
  - letzter erfolgreicher Provider-Refresh mit `models[]`, `refreshed_at` und `source`
  - ohne erfolgreichen Refresh sichtbarer Seed aus `state/runtime_settings.json`
- Secret-Material liegt ausschliesslich im lokalen Orchestrator-State:
  - `state/keystore.enc` plus `state/keystore.lock` fuer Shared-LLM-, Optimizer-OCR- und Embeddings-API-Keys
  - `state/oauth_token.enc` plus `state/oauth_token.lock` fuer die DPAPI-geschuetzte OAuth-Session
  - `state/oauth_latest_report.json` nur als sanitiserter OAuth-Report ohne Tokenwerte
- Aktuelle Resolver-Semantik:
  - `llm_shared`: gemeinsamer OpenAI-Key fuer `interpreter` und `normalizer`
  - `optimizer_ocr`: separater LLM-Key fuer die OCR-Kante des `optimizer`
  - `embeddings`: separater OpenAI-Key fuer `corpus_builder`-Embeddings
  - `oauth`: echter Browser-/PKCE-Login mit DPAPI-Cache, Refresh vor Laufzeitnutzung und sanitisierten Session-Metadaten
- Der Orchestrator bleibt alleiniger Auth-Owner; Schwester-Module bekommen nur ephemere Laufzeit-Credentials ueber Subprocess-Env, nie ueber Request-JSON.
- Die fruehere GUI-Annahme "OAuth ist nur Duplikat von API Keys" war falsch; der alte Schalter war funktional und wurde bewusst durch Auto-Fallback ersetzt.
- Aktuelle LLM-Resolver-Semantik:
  - aktive OpenAI-OAuth-Session -> `interpreter`, `normalizer` und OpenAI-`optimizer_ocr` laufen ueber OAuth
  - sonst -> `interpreter` und `normalizer` nutzen `llm_shared`; `optimizer_ocr` nutzt sein eigenes Credential-Ziel
- `optimizer_ocr` bleibt logisch getrennt:
  - kein stiller Fallback auf `llm_shared` oder `embeddings`
  - Env-Overlay an den Optimizer nutzt ausschliesslich `OPTIMIZER_OCR_*`
  - Modell, max_output_tokens und timeout_seconds liegen in `state/runtime_settings.json` unter `optimizer_ocr`
  - OpenAI-OAuth wird im Optimizer als derselbe ChatGPT/Codex-SSE-Backendcall
    wie beim Interpreter ausgefuehrt; direkte Provider-Calls bleiben dem
    API-Key-Modus vorbehalten
- `embeddings` bleiben logisch getrennt:
  - ein gesetzter Embeddings-Key schaltet `corpus_builder generate_embeddings` auch unter aktivem OAuth frei
  - ein fehlender Embeddings-Key blockiert keinen OAuth-Laufpfad, sondern fuehrt nur zu einer sichtbaren Warnung und zum Ueberspringen der Embeddings-Stufe

## UI-Architektur und Debug

- `orchestrator.ui` ist jetzt die pfadstabile, flache Surface der Desktop-GUI; der externe Import bleibt `from orchestrator.ui import OrchestratorApp`.
- Die GUI trennt die Stufen explizit innerhalb eines flachen UI-Pakets:
  - `surface`: `OrchestratorApp` als duenne Eintrittsflaeche und Dispatch-Schicht
  - `repository`: `UiState`-Mapping und Persistenz nach `state/ui_state.json`
  - `validation`: harte Start-Invarianten fuer Pflichtpfade
  - `workflow`: Worker-Start, Abort, Queue-Drain, Finish und Cleanup
  - `debug_layout`, `debug_rendering`, `debug_actions`, `debug_repository`: generischer `Debug`-Tab mit eigener Persistenz in `state/debug_host_state.json`
  - `layout`, `credentials_layout`, `rendering`, `credentials_rendering`, `dialogs`: sichtbare Tk-Boundaries fuer Widget-Aufbau, Credential-Tab, Snapshot-/Log-Ausgabe und Dialoge
  - `policy`: `orchestrator.ui.view_model` fuer Status-, Farb- und Detailformatierung
- Im `Debug Host` sitzt der destruktive Button `Reset Debug Output` bewusst getrennt neben der Ueberschrift und blockiert waehrend laufender Debug-Sessions; er bereinigt nur gespeicherte Debug-Artefakte unter `state/debug_sessions/`.
- Der Startpfad baut nur Shell plus `Status` sofort; `Debug`, `Credentials`, `Modelle` und `Log` werden lazy beim ersten Tabwechsel aufgebaut.
- Der fruehere Tiefenast `orchestrator.ui.app` existiert nicht mehr; die UI-Hilfsmodule liegen jetzt direkt unter `orchestrator/ui/`.
- `orchestrator.debug_host` ist die generische Host-Surface fuer descriptor-gesteuerte Debugplaene, persistente Modulstarts und spaetere host-seitige Schritte wie `request_enrichment`.
- Debugging entlang der UI-Stufen:
  - Startprobleme zuerst in `validation` oder `repository`
  - Credential-Modus-, Key- und OAuth-Probleme zuerst in `orchestrator.credentials` oder `credentials_rendering`
  - Debug-Session-Start, Snapshot-Polling und Session-Cancel zuerst in `orchestrator.debug_host` oder `debug_rendering`
  - Worker-/Lifecycle-Probleme in `workflow`
  - Widget-Aufbau in `layout`, Snapshot-/Log-Darstellung in `rendering`, Dialoge in `dialogs`
  - Laufende GUI- und Pipeline-Logs unter `state/orchestrator.log`
  - `Reset Pipeline Logs` leert diese GUI-Logs im Hauptprozess und leert parallel die versteckte Pipeline-Historie unter `state/pipeline/`

## Models-Architektur und Debug

- `orchestrator.models` bleibt die pfadstabile Surface fuer gemeinsam genutzte Orchestrator-Typen.
- `orchestrator.model_catalog` ist die pfadstabile Surface fuer den nicht-sensitiven Modellkatalog-Cache und provider-verifizierte Refreshes auf `GET /v1/models`.
- Die Modellschichten sind explizit getrennt:
  - `types`: persistente UI-, Dokument- und Pipeline-State-Traeger
  - `snapshots`: sichtbare Pipeline-Stufen, Stage-Snapshots und Default-Stage-Map
  - `results`: Run- und Reset-Zusammenfassungen
  - `coercion`: best-effort Deserialisierung fuer gespeicherte JSON-Zustaende
- Die GUI `Modelle`-Tab-Semantik:
  - alle fuenf Modell-Slots sind provider-gestuetzte Dropdowns
  - `Refresh Models` aktualisiert `llm_shared`, `optimizer_ocr` und `embeddings` getrennt
  - OAuth-only refresht den LLM-Katalog nicht live, sondern faellt auf Cache/Seed zurueck, bis ein verifizierter OpenAI-Vertrag dafuer existiert
- Debugging entlang der Modellschichten:
  - Lade-/Persistenzprobleme zuerst in `types` oder `coercion`
  - Snapshot- oder Stage-Reset-Verhalten in `snapshots`
  - Action-Result-Zusammenfassungen in `results`

## State-Architektur und Debug

- `orchestrator.state` bleibt die pfadstabile Surface fuer UI- und Pipeline-State-Persistenz.
- `orchestrator.credentials.repository` ist bewusst separat und verwaltet nur den nicht-sensitiven Resolver-State in `state/credentials_state.json`.
- `orchestrator.model_catalog.repository` verwaltet separat den nicht-sensitiven Modellkatalog-State in `state/model_catalog_state.json`.
- Die State-Stufen sind explizit getrennt:
  - `surface`: stabile Load-/Save-API und `atomic_json_write`
  - `repository`: `UiState`- und `PipelineState`-Serialisierung
  - `adapter`: Raw-JSON-Datei-I/O und atomisches Schreiben
- Debugging entlang der State-Stufen:
  - Dateilesen/-schreiben sowie `state/pipeline/pipeline_state.json`- oder `state/pipeline/runs/`-Probleme zuerst in `adapter`
  - Deserialisierung und Default-Fallbacks in `repository`
  - Credential-Flags, OAuth-Metadaten und DPAPI-Key-Probleme in `orchestrator.credentials.repository` oder `orchestrator.credentials.keystore`

## Worker-Architektur und Debug

- `orchestrator.worker` bleibt die pfadstabile Surface fuer Worker-Start und Prozessabbruch.
- Die Worker-Stufen sind explizit getrennt:
  - `surface`: stabile API und kompatible Test-Seams
  - `workflow`: Action-Dispatch, Queue-Events, Engine-Lifecycle
  - `runtime`: plattformneutrale Terminierungslogik
  - `adapter`: Win32-/POSIX-Prozessgrenzen und Low-Level-OS-Zugriffe
- Debugging entlang der Worker-Stufen:
  - Action-Dispatch oder Queue-Ereignisse zuerst in `workflow`
  - Harter Prozessabbruch in `runtime`
  - Plattform- oder Win32-Sonderfaelle in `adapter`

## Integrations-Architektur und Debug

- `orchestrator.integrations` bleibt die pfadstabile Surface fuer den Produktcode.
- Die Integrationsstufen sind explizit getrennt:
  - `surface`: Re-Exports der stabilen Produkt-API
  - `registry`: einzige Quelle fuer sibling module order, Required-Actions, Stage-Namen und Timeouts
  - `workflow`: Stage-Dispatch und Healthcheck-Orchestrierung auf Basis der Registry
  - `adapter`: pfadstabile Subprocess-/Contract-Boundary fuer synchrone Contract-Calls und persistente Debug-Prozessstarts ueber `launch_contract_process(...)`
  - `contract_parsing`: Contract-Fehlertext, Result-Parsing und Health-Koerzierung
  - `validation`: harte Runtime- und Response-Invarianten
  - `policy`: weiche Koerzierung fuer best-effort Contract-Felder
  - `types`: benannte Stage-Result- und Health-Traeger
- Debugging entlang der Integrationsstufen:
  - Runtime-/Manifest-Probleme zuerst in `validation`
  - Subprocess-/Response-Datei- und Env-Overlay-Probleme in `adapter`
  - Contract-Failure-Text und Feldkoerzierung in `contract_parsing`
  - Payload-Dispatch, Runtime-Credential-Aufloesung und Stage-Zuordnung in `workflow`
  - feldweise Fallbacks oder Health-Koerzierung in `policy`

## Pipeline-Architektur und Debug

- `orchestrator.pipeline` bleibt die pfadstabile Surface fuer `OrchestratorEngine`, `OrchestratorBusyError` und `OrchestratorCancelled`.
- Die Pipeline-Stufen sind explizit geschnitten:
  - `surface`: Engine-Konstruktion und oeffentliche Methoden
  - `workflow`: Run-Loop, Queue-Aufbau und Reset-Orchestrierung
  - `document_workflow`: duenne per-record Surface fuer Status-Setup und lineare Stage-Reihenfolge
  - `optimizer_workflow`, `interpreter_workflow`, `validator_workflow`, `normalizer_workflow`, `corpus_workflow`: klar getrennte Dokumentstufen
  - `repository`: State-, Artefakt- und Error-Bundle-Mutationen
  - `validation`: harte UI-, Pfad- und Datei-Invarianten
  - `policy`: Output-Naming, Review-Parsing und Konflikt-Suffixe
  - `debug`: Snapshot-, Stage- und Run-Log-Steuerung
- Sichtbarer Datenfluss pro Dokument:
  - Input-Discovery
  - Intake
  - route-aware Preflight-Healthcheck mit `optimizer_ocr` fuer Vision-OCR und feature-skopiertem file-Profil des `optimizer` aus der Ready-Queue
  - Optimizer
  - Request Enrichment
  - Interpreter
  - Validator
  - Normalizer
  - Corpus Builder
  - Embeddings
  - Success- oder Error-Case-Routing
- Das kanonische Optimizer-Raw-Evidence liegt waehrend der Verarbeitung run-scoped unter `state/pipeline/runs/<run_id>/.../artifacts/raw_extracts/` und wird erst bei finalem Erfolg nach `Documents/raw_extracts/*.raw.json` publiziert.
- Der Request-Trace besteht aus `ocr.request.json`, `interpreter.request.json` und `normalizer.request.json`. OCR- und Normalizer-Requests werden als auditierbare Call-Inputs persistiert; `Request Enrichment` baut zwischen Optimizer und Interpreter das kanonische `interpreter.request.json`, validiert den `projection_catalog` fail-closed und rewritet Source/Page-Backlinks fuer die finale Publikation.
- `interpreter` konsumiert dieses kanonische `interpreter.request.json` fuer beide Profile direkt; ein interpreter-seitiger Raw-Staging-Pfad existiert nicht mehr.
- Nach dem Optimizer fannt `stage_scheduler` mehrseitige Quellen in page-scoped Work Items auf. Jede Page laeuft einzeln durch Request Enrichment, Interpreter, Validator, Normalizer und Corpus Builder; der `DocumentRecord` bleibt nur Aggregat fuer Original, Publikation, Review-State und finale Disposition.
- Fuer das file-Profil reicht `validator_workflow` exakt den page-scoped Optimizer-`raw_path` fail-closed an den Validator weiter; ohne gueltiges Raw-Evidence startet die Validator-Stufe fuer diese Page nicht.
- Retries sind nach dem Optimizer page-local. Ein Interpreter-/Validator-/Normalizer-/Corpus-Fehler setzt dieselbe Page priorisiert zurueck in die passende Stage; ein Validator-FAIL setzt die betroffene Page beim Interpreter wieder ein. Erschoepfte Einzelpages werden unter `Error Cases/<Modulname>/<Route>/...` als Diagnoseartefakte ohne `originals`-Move eingefroren; page-scoped Raw-, Request-, Debug- und Manifest-Artefakte muessen dabei ihren `pNNN.ofMMM` Suffix behalten, damit mehrere fehlgeschlagene Pages desselben Dokuments einander nicht ueberschreiben. Erst wenn alle Pages terminal sind, laufen Embeddings, Erfolgspublikation und Original-Archivierung; komplett fehlgeschlagene Dokumente nutzen den normalen Dokument-Error-Bundle-Pfad.
- Debugging entlang der Pipeline-Stufen:
  - Queue-/Retry-Probleme zuerst in `workflow` oder `record_repository`
  - Dokumentstufen isoliert in den jeweiligen `*_workflow`-Modulen
  - Dateisystem-, Route- und Error-Case-Probleme in `artifact_repository` oder `bundle_repository`
  - Pfad- und Contract-Grenzen in `validation`
  - Review-, Naming- und Konfliktverhalten in `policy`
  - Snapshot- oder Run-Log-Verhalten in `debug`

## Bootstrap-Architektur und Debug

- `orchestrator.bootstrap` bleibt die pfadstabile Surface fuer Registry-, Manifest- und Startup-Pruefungen.
- Die Bootstrap-Stufen sind explizit getrennt:
  - `surface`: re-exportiert Konstanten, Exceptions und die stabile Bootstrap-API
  - `adapter`: Registry-/Manifest-I/O, Modulpfad-Aufloesung, Python-Candidates und Runtime-Dependency-Import
  - `runtime_report`: gemeinsamer Runtime-/Startup-Health-Report fuer `check-runtime.bat`, Packaging-Tests und installierte Modulslots
  - `validation`: harte Manifest-, `runtime_dir`-, Actions- und Dependency-Invarianten
  - `workflow`: Registry-Laden, Runtime-Spec-Aufbau und Startup-Prerequisites
  - `types`: benannte Bootstrap-Specs fuer Manifest und Runtime
- Debugging entlang der Bootstrap-Stufen:
  - Registry-/Manifest-Fehler zuerst in `validation` oder `workflow`
  - Packaging- oder Provenance-Probleme zuerst in `runtime_report`
  - Runtime-Pfad- und Bundled-Python-Probleme in `adapter` oder `workflow`
  - UI-Runtime-Abhaengigkeiten wie `customtkinter` in `adapter`

## Contract

- `module-manifest.json` referenziert die sichtbare Package-Surface `orchestrator.orchestrator_contract`.
- `orchestrator.edit_contract` ist additiv und aendert den Produkt-Contract nicht.
- Die Contract-Stufen sind explizit getrennt:
  - `surface`: `orchestrator.orchestrator_contract` als stabile Patch- und Entry-Surface
  - `adapter`: Request-/Response-I/O
  - `validation`: harte Action- und Payload-Grenzen
  - `workflow`: `run`, `reset`, `reset_pipeline_logs`, `embeddings` und `healthcheck`
  - `types`: zentrale Action-Literale fuer Contract-, Worker- und UI-Dispatch
- Unterstuetzte Actions:
  - `run`
  - `reset`
  - `reset_pipeline_logs`
  - `embeddings`
  - `activate_corpus_context`
  - `inspect_source_document_sample`
  - `kernel_llm_runtime_profile`
  - `kernel_llm_generate`
  - `healthcheck`
  - `create_artifact_tree`
  - `validate_artifact_tree`
  - `create_pipeline_batch_manifest`
  - `finalize_pipeline_batch_manifest`
- `reset_pipeline_logs` leert die versteckte Erfolgs-/Run-Historie unter `state/pipeline/` und die globalen GUI-Logdateien unter `state/`, damit ein geloeschter Artefaktbaum auch wirklich ohne alte Run-Spuren neu gestartet werden kann.
- `run` kann fuer Kernel-gesteuerte Pipeline Manager Laeufe eine
  `snapshot_path`, `workflow_run_id`, `pipeline_batch_id` und
  `target_identity` erhalten. Der Orchestrator schreibt dort
  Fortschritts-Snapshots und liefert im Owner-Response Input-Dispositionen,
  Output-Artefakte, materialisierte Records, Record Counts und Run-Refs fuer
  Kernel-Batch-Korrelation.
- `embeddings` triggert den manuellen Corpus-Embeddings-Lauf fuer bereits vorhandene Corpus-Artefakte, ohne den normalen Dokument-Run umzubenennen.
- `activate_corpus_context` ist die einzige headless Owner-Action fuer den Orchestrator-Run-Zielkontext. Direkte MCP- oder Edit-Suite-Schreibzugriffe auf `state/ui_state.json` bleiben gesperrt.
- `inspect_source_document_sample` bleibt eine nicht materialisierende
  Optimizer-Inspektion fuer einzelne Quelldokumente. Die Antwort enthaelt nun
  zusaetzlich `output_refs.raw_extract_paths`, damit der Semantic Control
  Kernel raw sample documents ueber die bestehende Optimizer-Kante in
  `kernel.analyze_sample.input.v1` normalisieren kann.
  Die Inspection startet den Optimizer mit `SubmodulePipelineModules`, damit
  Runtime Settings, OAuth/API-Key-Credentials und das separate `optimizer_ocr`
  Modell-Overlay auch fuer Kernel-Sample-Inspections gelten.
- `kernel_llm_runtime_profile` und `kernel_llm_generate` sind die Host-Bruecke
  fuer den Semantic Control Kernel. Der Orchestrator nimmt dafuer das
  Interpreter-Profil aus `state/runtime_settings.json`, loest die
  Interpreter-Credentials ueber `orchestrator.credentials` und ruft danach
  ausschliesslich die Interpreter-Action `generate_llm` mit ephemerem
  `env_overlay` auf. Secret-Werte werden nicht in Requests, State oder
  Kernel-Profile gespiegelt.
- `create_pipeline_batch_manifest` und `finalize_pipeline_batch_manifest`
  koennen vom Kernel bereits validierte Pending-/Final-Manifeste erhalten.
  Der Orchestrator schreibt dann genau diese Manifestform und echoet die
  Kernel-Zielidentitaet, statt eine zweite Batch-Wahrheit zu erzeugen.
- `orchestrator.admin_contract` ist die owner-klare headless Admin-Surface fuer Runtime-Settings, Credential-Metadaten/API-Key-Verwaltung und explizites Secret-Reveal.
- Admin-Actions:
  - `inspect_runtime`
  - `manage_runtime_settings`
  - `manage_credentials`
  - `reveal_secret`
- `manage_runtime_settings` liest, ersetzt oder setzt Defaults fuer `state/runtime_settings.json` nur ueber `RuntimeSettingsState`-Validierung.
- `manage_credentials` setzt oder loescht API-Keys nur ueber `orchestrator.credentials`; Secret-Werte werden nicht in State-JSON gespiegelt.
- `reveal_secret` gibt Plaintext nur mit expliziter Unlock-Phrase `REVEAL_SECRET:<target>` zurueck und schreibt ein Audit-Event nach `state/admin_audit.jsonl`.
- Fuer `healthcheck` bleibt `scope="pipeline_run"` stabil; das vision-Profil des `optimizer` erhaelt bei OCR-Bedarf `optimizer_ocr`, und das file-Profil erhaelt bei route-spezifischem Preflight optional weitere `required_dependencies`.
- `run.bat` und `python -m orchestrator --gui` bleiben unveraenderte Produkt-Entry-Points fuer die Desktop-Nutzung.

## Installer und Packaging

- `build-installer.bat` nutzt denselben Root-Staging-/Compile-Pfad wie `05 - Corpus Builder`, aber mit modul-lokalem `installer/installer-manifest.json`.
- Die Stage liefert die vier Default-Policy-Dateien unter `config/` mit aus.
- Der Inno-Installer behandelt `config/` wie `state/` als persistierte User-Daten: das Verzeichnis bleibt bei Reinstall erhalten, und vorhandene user-editierte `config/*.json` werden nicht ueberschrieben.
- Das generierte `dist/stage/release-manifest.json` weist explizit aus:
  - `mutable_dirs=["state"]`
  - `excluded_runtime_paths=["runtime\\wheelhouse"]`
  - `sign_targets` fuer Batch- und Manifest-Surfaces
- Der Installer bringt bewusst **kein komplettes Pipeline-Bundle** mit. Er installiert nur den Orchestrator-Modulslot; Schwester-Module muessen separat im selben Pipeline-Root liegen.

## Abweichungslog

- `SHOULD: Regressionen mit realistischen oder echten Artefakten`
  - Aktueller Stand: kleiner Replay-Korpus mit anonymisierten Kundenfaellen, einem Live-Capture aus einem synthetischen Kassenbon und synthetischen Review-/Retry-Faellen vorhanden, aber noch kein breiter anonymisierter Produktionskorpus und keine regelmaessigen Live-Sibling-End-to-End-Regressionslaeufe.
  - Grund: offline reproduzierbare Dev-Suite und deterministische Handover-Basis haben Vorrang; zusaetzliche reale Faelle muessen weiterhin kuratiert und datenschutzsauber bereinigt werden.
  - Risiko wenn offen: Drift gegen weitere Schwester-Modul-Ausgaben oder seltene reale Dokumentvarianten kann spaeter auftreten, obwohl die lokale Replay-Suite gruen bleibt.
- `MUST: Installations- und Packaging-Pfade muessen die Foederationsgrenze sichtbar machen`
  - Aktueller Stand: der neue Installer ist absichtlich nur ein Modulslot-Installer; die Nachbarmodule bleiben externe Voraussetzung im selben Pipeline-Root.
  - Grund: `module-registry.json` und relative Schwesterpfade bleiben der sichtbare Foederationsvertrag; der Installer darf diese Struktur nicht still lokal uminterpretieren.
  - Risiko wenn offen: isolierte Einzelinstallationen starten lokal sauber, scheitern aber spaeter am fehlenden Schwesterverbund, wenn diese Grenze nicht im Handover sichtbar bleibt.
- `SHOULD: Signierung oder zentrale Sign-Pipeline sichtbar machen`
  - Aktueller Stand: `sign_targets` werden im generierten `release-manifest.json` dokumentiert und getestet, aber es gibt noch kein foederationsweites Tooling, das diese Liste automatisch signiert oder verifiziert.
  - Grund: im Root existiert noch kein gemeinsamer Signatur- oder Bootstrapper-Pfad fuer alle Module.
  - Risiko wenn offen: Trust-Grenzen fuer Batch-Wrapper und Manifestdateien bleiben dokumentiert, aber noch nicht zentral technisch durchgesetzt.
- `SHOULD: unsupported Intake-Fehler ohne vierte Route-Familie ablegen`
  - Aktueller Stand: unsupported Formate behalten `route_family=""`, werden fuer Error-Cases aber unter `Error Cases/Intake/Unrouted/` abgelegt.
  - Grund: der Blueprint verlangt keine vierte serialisierte Route-Familie; fuer finale Intake-Fehler braucht der Orchestrator dennoch einen stabilen Bundle-Root ausserhalb von `Images|Files`.
  - Risiko wenn offen: unsupported Sonderfaelle haben einen sichtbaren Bundle-Pfad ausserhalb des Zwei-Familien-Schemas, obwohl die serialisierte Route-Matrix stabil nur `Images|Files` kennt.
- `MUST: Action-Namen folgen im Verband normalerweise dem Muster <verb>_document oder healthcheck`
  - Aktueller Stand: der Orchestrator behaelt bewusst die operativen Top-Level-Actions `run`, `reset`, `reset_pipeline_logs`, `embeddings` und `healthcheck`, weil er keine Schwester-Stufe der Dokumentpipeline ist, sondern deren zentrale Steuerflaeche.
  - Grund: Worker-, UI- und Subprocess-Dispatch teilen dieselben Action-Literale; ein Umbenennen nur fuer die Pattern-Treue wuerde den sichtbaren Bedienvertrag aendern, ohne die Foederationsgrenze zu verbessern.
  - Risiko wenn offen: Der Orchestrator bleibt terminologisch eine Sonderrolle gegenueber Schwester-Modulen; ohne explizite Doku wirkt das wie zufaellige Drift statt wie eine bewusste Ausnahme.
- `MUST: Die Desktop-Surface des Orchestrators als Sonderrolle gegenueber headless Schwester-Modulen sichtbar halten`
  - Aktueller Stand: `run.bat` und `python -m orchestrator --gui` bleiben bewusst erhalten, waehrend die vom Orchestrator geladenen Schwester-Module headless bleiben.
  - Grund: die SPEC stellt fuer orchestratorgebundene Schwester-Module auf headless Betrieb um; der Orchestrator selbst bleibt aber die zentrale Bedien- und Kontrollsurface des Verbands.
  - Risiko wenn offen: Ohne diese Klarstellung wirkt die lokale Desktop-Surface wie ein Policy-Verstoss statt wie die dokumentierte Sonderrolle des zentralen Host-Moduls.

## Phase 19 Owner Contracts

- `orchestrator/workspace_domain/` owns the Kernel Artifact Tree contract.
- Public owner actions:
  - `create_artifact_tree`
  - `validate_artifact_tree`
- Request fields include the shared Phase 19 owner envelope plus:
  - `artifact_root_parent`, `artifact_root_name`, `create_mode`, `folder_contract_version`
  - or `artifact_root_path` for validation
- Response detail includes canonical `Input`, `Corpus`, `Documents`, `Error Cases` and `Semantic Release` paths, stable path hashes, missing-path diagnostics and folder-contract fingerprints.
- Path safety rule: every created or validated path must stay inside the selected artifact root.

- `orchestrator/pipeline_batches/` owns traceable batch identity and finalization.
- Public owner actions:
  - `create_pipeline_batch_manifest`
  - `finalize_pipeline_batch_manifest`
- Canonical manifest location:
  - `<artifact_root>/Documents/logs/pipeline_batches/<pipeline_batch_id>/pipeline_batch_manifest.json`
- Pending manifests stay in the same batch folder under `pending_pipeline_batch_manifest.json`.
- Finalization returns manifest fingerprint, cleanup eligibility and correlation-report refs.
- Kernel owner-run evidence correlates materialized DB rows from active `documents`
  entries by exact materialized hash when available, otherwise by the governed
  source file name from the Input/original refs. This keeps scan PDFs and
  page-wise documents valid when Corpus Builder stores per-page/content hashes
  instead of the original file byte hash.
