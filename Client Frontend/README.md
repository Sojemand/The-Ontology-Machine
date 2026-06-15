# Client Frontend

Frontend-Ausnahme der Vision Pipeline mit lokalem HTTP-Server, Browser-UI, Provider-I/O, lokaler Persistenz, Runtime-/Installer-Logik und read-only Minimal-Agent.

## Zielbild

- Die kanonische Produktquelle lebt unter `client_frontend/`.
- `Client Frontend` bleibt bewusst eine manifestfreie Frontend-Surface. Es ist
  kein Orchestrator-Action-Modul und bekommt kein `module-manifest.json`, solange
  dafuer Pseudo-Actions oder kuenstliche `contract_module`-Semantik erfunden
  werden muessten.
- `src/` bleibt die pfadstabile Build- und Browser-Surface.
- `server/` bleibt die pfadstabile Runtime- und Direct-Run-Surface.
- `shared/provider-catalog.json` bleibt als root-nahe immutable Contract-Datei bewusst ausserhalb des Package-Roots.
- Mutable Laufzeitdaten liegen ausserhalb des Modulroots unter `%LOCALAPPDATA%\Enterprise Stack\Client Frontend` oder `VISION_PIPELINE_CLIENT_FRONTEND_HOME`.
- OAuth- und Modellkatalog-State liegen dort unter `state/credentials_state.json`, `state/oauth_token.enc`, `state/oauth_token.lock`, `state/oauth_latest_report.json` und `state/model_catalog_state.json`.
- Temporäre Build-Pruefartefakte gehoeren nicht zur Produktquelle und bleiben ueber lokale Ignore-Regeln ausserhalb des Source-Vertrags.

## Struktur

```text
Client Frontend/
|- client_frontend/
|- src/
|- server/
|- shared/
|- dev-tests/
|- runtime/
|- node/
|- README.md
|- README.txt
|- requirements.txt
|- start.bat
|- config.bat
|- installer.bat
|- build-runtime.bat
|- package.json
```

### Kanonische Produktquelle

- `client_frontend/browser/`
  - Browser- und UI-Produktcode fuer `main_app`, `config_app`, `render`, `api`, `types`, `chat_controller`, `config_select` und Styles.
  - Die `/config`-Surface bearbeitet `frontend_policy.json` ueber gruppierte Editorfelder innerhalb einer einzigen Policy-Karte.
- `client_frontend/http/`
  - HTTP-Server-Workflow und Surface fuer `server/index.js`.
- `client_frontend/credentials/`
  - Serverseitige Credential- und OAuth-Ownership fuer Login-Flow, sanitisierten Session-Status, Token-State und LLM-Resolver.
- `client_frontend/model_catalog/`
  - Nicht-sensitive Modellkatalog-Ownership fuer `llm_shared` und `embeddings`, getrennt vom Provider-I/O.
- `client_frontend/app_paths/`, `config/`, `provider/`, `vault/`, `chat_store/`, `memory/`, `min_agent/`, `runtime_paths/`
  - Gleichrangige Server-Subsysteme mit sichtbaren Stufen.
- Der aktive Corpus wird nicht im Modulroot materialisiert. Frische Configs defaulten auf die gebuendelte Demo-DB `..\SampleDB\Consciousness Travel - Default Demo\Corpus\corpus.db`, relativ zum Client-Frontend-Modul. User-Auswahl bleibt user-konfiguriert und kann explizit leer gesetzt werden.
- Seitenbilder werden bevorzugt aus der optionalen DB-Tabelle `document_page_images(document_id, page, content_type, image_blob)` im aktiven Corpus bedient.
- Der oeffentliche Bild-Entry-Point bleibt `GET /api/image/<docId>/<page>`; fuer alte Corpora ohne eingebettete Bilder bleibt der Fallback ueber `page_images/` relativ zum aktiven Corpus-Verzeichnis erhalten.
- Der read-only Minimal-Agent bietet neben SQL, Dokumentabruf, Provenienz, Semantic Search und Workbench ein deterministisches `database_coverage_snapshot`-Tool. Es liest nur kompakte Coverage-Fakten aus dem aktiven Corpus, damit der Query-Agent Materialisierung, Promotions, Fields, Rows, Weak Spots und Release-Mix erklaeren kann, ohne Kernel-Workflow oder zusaetzliche Analyse-LLM-Kaskade.
- Die Workbench bleibt bewusst genau diese lokale read-only Diagnose-Surface des Minimal-Agenten. Sie ist kein Default-Pfad fuer normale Corpus-Abfragen; `sql_query`, `get_document`, `semantic_search`, Provenienz und `database_coverage_snapshot` bleiben die bevorzugten Fachtools, wenn sie ausreichen.
- Workbench-Capabilities sind absichtlich eng und explizit:
  - Python laeuft ueber den gebuendelten Runner `server/workbench_python_runner.py` mit read-only Dateisystem-Guards, ohne Netzwerk-, Prozess-, Native- oder Registry-Schreibzugriff; SQLite wird ausser `:memory:` read-only geoeffnet.
  - PowerShell laeuft nur ueber die gebuendelte Runtime und wird vorab statisch gegen eine read-only Allowlist validiert. Schreibende Cmdlets, Netzwerkzugriffe, Prozessstarts, dynamische Invocation und Path-Traversal sind nicht Teil der Surface.
  - Erlaubte Lesepfade sind der aktive Corpus unter `MIN_AGENT_DATA_DIR`, die aktive DB unter `MIN_AGENT_DB_PATH` und explizit zugelassene Config-/Soul-Dateien.
  - PowerShell erbt die Launcher-/Prozessumgebung und darf sie ueber erlaubte read-only Cmdlets inspizieren. Das ist fuer lokale Diagnose bewusst Teil des Workbench-Vertrags, kein accidental secret leak. Secrets, die dort nicht sichtbar sein sollen, duerfen nicht in die Launcher-Umgebung gelegt werden.
  - Eine spaetere Aenderung an dieser Env-Inspection-Faehigkeit ist eine bewusste Workbench-Vertragsaenderung und braucht README-Update plus Regressionstest.
- `client_frontend/tokens.js`, `client_frontend/vector.js`
  - Kleine Fachmodule ohne kuenstlichen Pipeline-Spam.
- `client_frontend/shared/provider_catalog.ts` und `client_frontend/shared/provider_catalog.js`
  - Einziger lokaler Adapter auf `shared/provider-catalog.json`.
- Wrapper-Seams fuer Browser- und Runtime-Tests bleiben bewusst pfadstabil:
  - `src/main_app/`
  - `server/chat_store/surface.js`
  - `client_frontend/runtime_paths.js`
  - `client_frontend/runtime_paths/*`

### Pfadstabile Root-Surfaces

- Browser:
  - `src/main.ts`
  - `src/config.ts`
  - `src/main_app.ts`
  - `src/config_app.ts`
  - `src/ui/render.ts`
  - `src/styles/main.css`
- Server:
  - `server/index.js`
  - `server/min_agent.js`
  - `server/provider.js`
  - `server/config.js`
  - `server/vault.js`
  - `server/chat_store.js`
  - `server/memory.js`
  - `server/app_paths.js`
  - `server/runtime_paths.js`
  - `server/tokens.js`
  - `server/vector.js`

## Laufzeitmodell

- Start- und Config-Starter laufen weiter ueber `runtime/launch-server.bat`.
- Gebuendelte Runtimes bleiben unter `node/` und `runtime/`.
- Der Runtime-Checker bleibt `tools/check-runtimes.mjs`.
- Produktiver Start bleibt host-unabhaengig: kein produktiver Fallback auf System-Node, System-Python oder Downloads.
- Die gebuendelte Python-Runtime bleibt stdlib-only und dient nur dem isolierten read-only Workbench-Runner des Minimal-Agenten.
- `config/config.json` bleibt OAuth-frei; Access- und Refresh-Tokens duerfen nie in Browser-Storage, Query-Parametern oder `GET /config/api/current` landen.
- Eine gesunde OAuth-Session ist der primaere LLM-Pfad; Embeddings und Vektorabfragen bleiben weiter API-key-basiert.
- `state-snapshot/` ist ein optionales Packaging-/Migration-Artefakt aus `tools/deploy.ps1 -IncludeStateSnapshot`, keine Produktquelle. Es kann app-home-nahe Config-/State-Dateien enthalten, darunter `.salt`, verschluesselte Keystore-/OAuth-Caches, OAuth-Supportberichte, Chats und Modellkatalog-State. Der Installer importiert diesen Snapshot nur in leere Ziel-Config-/State-Dateien. Der Ordner ist deshalb als sensitive Runtime-Transfer-Artefakt zu behandeln, nicht manuell zu pflegen und bleibt per `.gitignore` ausserhalb der Versionskontrolle.

## Pipeline Manager Kernel Surface

- Der `Pipeline Manager` verwendet jetzt direkt die kanonische `Semantic Control Kernel` Workflow- und Support-Toolsurface.
- Model-sichtbar bleiben genau die 29 permanenten Kernel-Tools fuer Workflow-Auswahl und Support-Control.
- Die Tool-Schemas bleiben bis auf `kernel_continue_resumable_workflow` absichtlich leere Object-Schemas. Pfade, IDs, Confirmations, Recovery-Scope und andere Domain-Werte werden nicht mehr vom Agenten in Chat-Argumente geschrieben.
- `kernel_continue_resumable_workflow` akzeptiert als einzige Ausnahme genau `resume_option_ref`; der Wert muss aus `kernel_resume_state.resume_options[]` stammen und wird als opaque Kernel-Ref an MCP weitergereicht.
- Permanent sichtbare Kernel-Workflow-/Support-Tools werden an MCP mit `{}` als Argumentobjekt gerufen; nur das generische Resume-Continue-Tool darf das eine opaque Resume-Ref-Feld weiterreichen. Request/session metadata wird nicht in diese leeren Schemas geschrieben.
- Event-scoped Recovery-Tools werden nicht permanent in den Agent-Kontext geladen. Sie werden nur fuer die aktive Kernel-Mirror-Recovery-Event-ID injiziert, wenn ein Kernel-authored `recovery_options`-Eintrag das Tool an `recovery_id`, `state_snapshot_id`, `tool_call_nonce` und alle tool-spezifischen Hidden-Scope-Felder bindet. Bei fehlender Bindung, Resolve, Expiry, Supersession oder Stale-Reject wird kein temporaeres Recovery-Tool exponiert.
- Permanente Next-Step-Tools in einem `workflow_completed` Mirror sind keine Recovery-Signale. Recovery-Chrome und temporaere Recovery-Tool-Injektion duerfen nur aus `recovery_options` oder event-scoped Recovery-Tools entstehen; ein erfolgreicher Completed-Mirror raeumt stale Recovery-State global aus der aktiven Pipeline-Surface.
- Das alte Action-Surface-Modell mit retired catalog routing, workflow-family indirection, level-split execute surfaces und generischen Wrapper-Tools ist retired und darf weder im Prompt noch im produktiven Frontend-Routing wieder aufgebaut werden.

## Kernel Event Transport

- Browser und Server sprechen fuer den `Pipeline Manager` ueber die lokale HTTP-Bridge:
  - `GET /api/v2/pipeline-manager/kernel/events`
  - `POST /api/v2/pipeline-manager/kernel/interactions/<interaction_request_id>/response`
  - `POST /api/v2/pipeline-manager/kernel/interactions/<interaction_request_id>/cancel`
- Diese Routen poll-en `kernel.client_frontend_event_batch.v1`, relay-en `kernel.user_interaction_response.v1` an die host-only Bridge und schicken Dialogwerte nie als Chat-Nachricht an den Agenten.
- Der Browser zeigt Kernel-owned Dialog-Submit/Cancel sofort als lokale Pending-UI: Eingaben und Dialog-Buttons werden deaktiviert, der ausgeloeste Button zeigt `Wird verarbeitet...`, und doppelte Submits fuer dieselbe `interaction_request_id` werden clientseitig ignoriert.
- Der Merge-Dialog `database_list_picker` kann neben Kernel-Optionslisten auch
  einen manuellen Artifact-Tree-Pfadmodus rendern, wenn der Kernel
  `prefilled_values.manual_path_count` setzt. Der Browser submitet weiterhin
  nur `selected_database_paths`; die DB-/Release-Aufloesung bleibt Kernel-State.
- Rebuild nutzt dieselbe generische Dialog-Bridge: `database_rebuild_from_artifacts`
  startet argumentleer, rendert `choose_artifact_root_folder`, `name_database`
  und bei existierender Ziel-DB `user_confirmation`. Der Browser submitet nur
  Dialogwerte; Zielpfad, Release-Fingerprint und Overwrite-Receipt bleiben
  Kernel-State.
- Der Progress-Bereich darf vor dem ersten echten `kernel.progress_event.v1` eine lokale Handoff-/Pending-Zeile anzeigen. Diese UI ist nicht persistierte Kernel-Wahrheit und wird sofort von realen Kernel-Events, `active_workflow_run` oder `active_pipeline_run` ueberstimmt.
- Kernel-Mirror-Events werden serverseitig als interne Session-History mit `role: "kernel"` gehalten. Sie bleiben Kernel-State und werden nicht als user-authored Display-Messages persistiert.
- Aktive pending interaction request events sind sticky/replayable: Wenn ein
  Browser-Cursor durch eine dynamisch verkuerzte Eventliste am offenen Dialog
  vorbeilaufen wuerde, liefert die Kernel-Bridge den aktiven Dialog trotzdem
  erneut aus, bis er submitted, cancelled, closed, expired oder superseded ist.
- Vor jedem normalen User-Chat-Turn liest der Server `kernel_status` und gleicht volatile Dialog-/Progress-Kontexte gegen die aktuelle Kernel-Wahrheit ab. Alte Dialog- oder Waiting-Mirror-Eintraege duerfen einen neuen User-Wunsch nicht blockieren oder als "Dialog ist bereits offen" ausgegeben werden, wenn der Kernel keinen aktiven Workflow und keine pending interaction meldet.
- Terminale Kernel-Mirror-Events (`workflow_completed`, `workflow_failed`,
  `workflow_cancelled`) pensionieren jeden non-terminalen Progress-Fallback
  derselben `workflow_run_id`. Eine Final Notice darf deshalb nicht zusammen
  mit einem alten `kernel_background_continuation`/`step_started`-Eintrag als
  weiter laufender Hintergrundprozess angezeigt werden.
- Orchestrator-Snapshot-Progress kann `artifact_refs.kind =
  orchestrator_stage_statuses` enthalten. Der Pipeline Manager rendert diese
  Module als einzelne Zeilen und laesst Details umbrechen, damit lange
  Subprozesszustaende nicht am rechten Rand abgeschnitten werden.
- Wenn der Orchestrator live Error-Cases im Artifact Tree sieht, erscheint
  eine eigene `Error Cases`-Zeile im Progress-Bereich. Das ist Live-Status,
  nicht erst Final-Notice; die Zahl steht fuer recoverbare Quelldateien aus
  `Error Cases/**/originals/**`, nicht fuer eingefrorene Diagnoseartefakte.
- Der Browser sendet abgelehnte Kernel-Confirmation-Dialoge als kanonisches
  `confirmation_decision: "rejected"`; die HTTP-Bridge normalisiert altes
  `"declined"` vor der Kernel-Uebergabe auf denselben Wert.
- `agent_explanation_guidance.response_mode = "explain_now"` startet einen reinen Erklaerungslauf: Der Modellkontext enthaelt nur das aktuelle Mirror-Event, damit alte Dialog- oder Waiting-History keine finale Notice verfaelscht. Die Session-History bleibt serverseitig erhalten, aber Workflow-, Support- und Recovery-Tools sind in diesem Turn nicht model-sichtbar. Der Agent darf das aktuelle Mirror-Event erklaeren und Optionen nennen, aber keinen neuen Workflow starten.
- Wenn ein Explain-Now-Mirror `workflow_explanation_context_path` setzt, muss der Pipeline Manager die Kernel-Provenance in den Agent-Kontext geben: `already_available` sind wiederverwendete Vorbedingungen, `performed_this_run` sind die wirklich neu ausgefuehrten Schritte des aktuellen Runs.
- No-projections completion mirrors fuer `empty_database_default_taxonomy_no_projections` werden auto-erklaert wie andere `explain_now`-Events. Der Agent-Kontext enthaelt den projectionless State, `projections_missing`, `database_ready_for_ingest: false` und die spaetere Fortsetzung `create_custom_projection_path`; ausgefuehrt wird sie erst nach expliziter Kernel-Resume-Auswahl.

## Recovery And Dialog Policy

- Kernel-owned Dialoge fuer Input, Auswahl, Confirmation, Blocker und Recovery werden im Browserpanel gerendert und nicht durch Agent-Fragen ersetzt.
- `kernel_cancel_active_run` ist der einzige Abort-Pfad fuer den `Pipeline Manager`.
- `kernel_cancel_active_run` stoppt Kernel-eigene Background-Continuation-Prozessbaeume ueber persistierte `*.ref.json`-Refs und markiert aktive Kernel-Laeufe als `cancelled`. Der Kernel Reset ruft denselben Stop-Pfad vor dem Archivieren des Runtime-State auf.
- `kernel_status` und `kernel_resume_state` liefern Support-/Resume-Kontext, ohne das alte Workflow-Familien-Inspection-Modell wieder einzufuehren. Explizites Fortsetzen laeuft danach ueber `kernel_continue_resumable_workflow`, nicht ueber einen primaeren Workflow-Starter.
- Der Kernel Reset archiviert aktive Kernel-Runtime-State-Dateien inklusive aktiver Database/Artifact-Bindings und Kernel-held Attach-States. Er loescht keine Corpus-Datenbanken, Artifact Trees, Semantic Releases oder sonstige Owner-Modul-Dateien.
- Support-Bundle-Hinweise und Recovery-Optionen werden nur aus Kernel-Events und Kernel-Tooldefinitionen gerendert.

## Debugbare Stufen

- Browser:
  - `src/*.ts` und `src/styles/main.css` sind stabile Eintrittsflaechen.
  - Die eigentliche Browser-Logik liegt unter `client_frontend/browser/`.
  - Fehler lassen sich in `main_app`, `config_app`, `render`, `api` oder `styles` zuordnen.
- Server:
  - `server/*.js` sind stabile Eintrittsflaechen.
  - Die eigentliche Server-Logik liegt unter `client_frontend/http/`, `provider/`, `config/`, `vault/`, `chat_store/`, `memory/`, `min_agent/`, `runtime_paths/` und `app_paths/`.
  - Fehler lassen sich dadurch HTTP-, Provider-, Config-, Vault-, Store-, Runtime- oder Minimal-Agent-Stufen zuordnen.

## Start, Build und Tests

- Chat-Start:

```bat
start.bat
```

- Konfiguration:

```bat
config.bat
```

- Runtime-Build:

```bat
build-runtime.bat
```

- Dev-Tests:

```bat
dev-tests\bootstrap.bat
dev-tests\run-tests.bat
```

- Zentraler Dispatcher:

```bat
..\run-dev-tests.bat --module "Client Frontend"
```

- Runtime-Check:

```bat
node\node.exe --disable-warning=ExperimentalWarning tools\check-runtimes.mjs
```

## Abweichungslog

| Modul | Regel | Abweichung | Grund | Risiko wenn offen |
| --- | --- | --- | --- | --- |
| Client Frontend | MUST: `module-manifest.json` vorhanden und belastbar | Kein `module-manifest.json` eingefuehrt | Die Frontend-Surface ist nicht sauber als Orchestrator-Action-Contract mit evidenzbasierten `actions`, `contract_module` und `launcher_module` ableitbar, ohne Pseudo-Actions zu erfinden | Foederationsaudit muss die Ausnahme bewusst lesen statt implizit ein Standardmodul anzunehmen |
| Client Frontend | SHOULD: kompletter Runtime-Neuaufbau aus lokalen Quellen ohne Host-Abhaengigkeiten moeglich | Vollstaendiger Quell-Neuaufbau aller gebuendelten Third-Party-Runtimes bleibt weiter nur teilweise erreichbar | Der Refactor haertet Struktur und Product-Root, nicht den kompletten Rebuild aller gebuendelten Fremd-Binaries | Vollstaendig offline reproduzierbare Runtime-Builds bleiben teilweise von vorhandenen Host-/Artefakt-Voraussetzungen abhaengig |
| Client Frontend | SHOULD: root-nahe Metadaten leben im lokalen Package-Root | `shared/provider-catalog.json` bleibt ausserhalb von `client_frontend/` | Die JSON-Datei ist eine bewusst root-nahe immutable Contract-Quelle fuer Browser und Server und soll nicht zu einer lokalen Sonderkopie driften | Aenderungen muessen weiter ueber den expliziten Adapter gelesen werden statt direkt verteilt |
| Client Frontend | SHOULD: OAuth-Architektur und Credential-Ownership folgen den Orchestrator-Begriffen | Frontend bleibt manifestfreie Ausnahme, uebernimmt aber `credentials`, `model_catalog`, `provider`, `config_app`, `http` und `state` als interne Ownership-Grenzen | Die Federationsangleichung soll ohne kuenstliche Frontend-Pseudo-Module erfolgen | Ohne explizite Dokumentation driftet die Frontend-Auth-Struktur semantisch vom Orchestrator weg |
| Client Frontend | MUST: keine mutable Corpus-Wahrheit im Modulroot | `sql_database_path` defaultet fuer frische Configs auf die gebuendelte Demo-DB unter `..\SampleDB\...`, nicht auf eine mutable DB im Frontend-Modulroot. Explizit leere Configs bleiben fail-closed. | Live-Corpora werden ausserhalb des Frontend-Modulroots materialisiert und owner-seitig gemanaged; die Demo-DB ist ein ausgeliefertes Sample im Installationsroot. | Ohne vorhandene Demo-DB oder User-Auswahl liefert der Minimal-Agent einen fail-closed Hinweis statt aus einem Modulroot-Fallback zu lesen |
| Client Frontend | MUST: Secrets nicht zufaellig zwischen Produktartefakten | `state-snapshot/` kann bei explizitem Export sensitive app-home State-Dateien als Transfer-Artefakt enthalten | Deploy-/Installer-Kompatibilitaet fuer frische Zielinstallationen mit optionaler State-Uebernahme | Ohne Ignore- und README-Vertrag koennte der Snapshot als Produktquelle oder commitbares Artefakt missverstanden werden |
| Client Frontend | SHOULD: read-only Tool-Surfaces bleiben verstaendlich dokumentiert | PowerShell-Workbench darf die Launcher-/Prozessumgebung ueber erlaubte read-only Cmdlets inspizieren | Lokale Diagnose soll das tatsaechliche Startumfeld sichtbar machen, waehrend Schreib-, Netzwerk- und Prozesspfade blockiert bleiben | Ohne expliziten Workbench-Vertrag wird dieselbe Faehigkeit in Reviews wiederholt als unbeabsichtigte Drift reklassifiziert |
