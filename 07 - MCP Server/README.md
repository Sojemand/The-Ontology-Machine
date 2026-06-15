# 07 - MCP Server

Lokaler MCP-Control-Plane-Server fuer die Vision Pipeline.

## Rolle

- Eigenes Modul mit Package-Root `mcp_server/`.
- Transport: lokales stdio-MCP, keine Netzwerk-Surface.
- Zweck: Tool-Katalog, Self-Description und owner-klare Delegation an bestehende Contracts in `00`, `01`, `03`, `04` und `05`.
- Kein zweiter Business-Logic-Host und kein Raw-State-Schreiber.

## Owner-Grenzen

Der Server ruft schreibende Cross-Modul-Operationen nur ueber owner-lokale Contracts auf:

- `04 - Normalizer`: Produkt-Contract und `normalizer_vision.edit_contract`
- `01 - Optimizer`: Produkt-Contract und `ingestion_layer_vision.edit_contract`
- `03 - Validator`: `validator_vision.edit_contract` fuer dedizierte Validator-Edit-Atomics
- `05 - Corpus Builder`: Produkt-Contract und `corpus_builder.edit_contract`
- `00 - Orchestrator`: Produkt-, Edit- und Admin-Contracts, kein Raw-State-Shortcut

Diese Faehigkeiten sind freigegeben, weil die jeweiligen Owner sie als
manifestierte Contract-Actions mit Tests tragen oder weil sie explizite
MCP-eigene Control-Plane-Hilfen ohne fachliche Dauerwahrheit sind:

- `activate_corpus_context`
- `create_empty_corpus_db`
- `prepare_pipeline_workspace_root`
- `write_workspace_release_change_confirmation`
- `write_workspace_db_reset_confirmation`
- `verify_workspace_active_release`
- `inspect_active_workspace_status`
- `run_active_pipeline`
- `start_active_pipeline_run`
- `inspect_active_pipeline_run`
- `inspect_source_document_sample`
- `read_working_release`
- `list_working_release_profiles`
- `read_working_release_profile`
- `validate_working_release`
- `compile_working_release`
- `preview_working_release_impact`
- `create_working_release_package`
- `export_working_release`
- `derive_working_release_from_blueprint`
- `create_minimal_custom_release`
- `create_projection_draft`
- `generate_locale_translation_payload`
- `translate_working_release_locale`
- `create_locale_scaffold`
- `read_translation_glossary`
- `upsert_translation_glossary_entry`
- `remove_translation_glossary_entry`
- `optimizer.describe_surfaces`
- `optimizer.read_surface`
- `optimizer.validate_surface`
- `optimizer.write_surface`
- `validator.describe_surfaces`
- `validator.read_surface`
- `validator.validate_surface`
- `validator.write_surface`
- `corpus_builder.describe_surfaces`
- `corpus_builder.read_surface`
- `corpus_builder.validate_surface`
- `corpus_builder.write_surface`
- `read_revision_candidate_release`
- `inspect_release_revision_context`
- `classify_release_revision`
- `reset_active_corpus_db`
- `activation_preflight`
- `activate_release_on_existing_db`
- `inspect_runtime`
- `read_runtime_settings`
- `write_runtime_settings`
- `reset_runtime_settings`
- `inspect_runtime_credentials`
- `set_runtime_api_key`
- `delete_runtime_api_key`
- `reveal_secret`

Dabei schreibt der MCP keinen fremden State direkt. Er delegiert an:

- `corpus_builder.orchestrator_contract`: `activate_corpus_context`, `create_empty_corpus_db`, `reset_active_corpus_db`, `activate_semantic_release`
- `orchestrator.orchestrator_contract`: `activate_corpus_context` inklusive optionalem `artifact_folder` und `input_folder`,
  `run` fuer aktive Verarbeitung sowie `inspect_source_document_sample` fuer read-only Beispieldokument-Inspektion
- `normalizer_vision.orchestrator_contract`: `export_default_blueprint_release`
- `normalizer_vision.edit_contract`: `list_default_blueprints`, `derive_working_release_from_blueprint`,
  `create_minimal_custom_release`, `create_projection_draft`,
  `create_locale_scaffold`, `generate_locale_translation_payload`,
  `translate_release_locale`, `read_release_package`, `list_projections`,
  `read_projection`, `validate_release_package`, `compile_release_package`,
  `preview_impact`, `create_release_package`, `export_semantic_release`,
  `read_translation_glossary_locale`
  sowie Owner-Surface-Validate/Write fuer explizite atomare Authoring-,
  Build- und Glossary-Schritte
- `ingestion_layer_vision.edit_contract`: `describe_surfaces`,
  `read_surface`, `validate_surface` und `write_surface` fuer Optimizer-
  Owner-Surfaces ohne MCP-eigene Surface-Wahrheit
- `validator_vision.edit_contract`: `describe_surfaces`, `read_surface`,
  `validate_surface` und `write_surface` fuer Validator-Surfaces; der MCP
  fuehrt keine eigene Validator-Regel- oder Schema-Wahrheit
- `corpus_builder.edit_contract`: `describe_surfaces`, `read_surface`,
  `validate_surface` und `write_surface` fuer Corpus-Builder-Authoring-
  Surfaces unter `config/`; DB-, Runtime-, Export-, Cache- und Debug-Artefakte
  bleiben ausserhalb dieser editierbaren Wahrheit
- `orchestrator.admin_contract`: `inspect_runtime`, owner-interne
  `manage_runtime_settings`/`manage_credentials` fuer die atomaren MCP-Tools
  `read_runtime_settings`, `write_runtime_settings`, `reset_runtime_settings`,
  `inspect_runtime_credentials`, `set_runtime_api_key` und
  `delete_runtime_api_key`, sowie `reveal_secret`

`reset_active_corpus_db` bleibt confirmation-pflichtig. `reveal_secret` ist nur
mit der expliziten Unlock-Phrase `REVEAL_SECRET:<target>` ausfuehrbar und wird
im Orchestrator-Audit protokolliert.

Semantic-Release-Exports sind keine MCP-eigene Dauerwahrheit. Standalone-Export
ueber `export_default_blueprint_release` braucht deshalb einen expliziten
`output_path` ausserhalb von `state/`. Blueprint-Workspace-Sequenzen schreiben ihren
Release unter den jeweiligen Corpus-/Workspace-Root, nicht nach
`state/semantic_releases`.

`prepare_pipeline_workspace_root` ist nur der lokale Dateisystem-Schritt fuer
"diesen Ordner als Pipeline-Artefakt-Root vorbereiten". Das Tool erstellt die
Standardstruktur `Input/`, `Corpus/`, `Documents/`,
`Documents/normalized`, `Documents/structured`, `Documents/validation`,
`Documents/page_images`, `Documents/raw_extracts`, `Documents/requests`,
`Documents/logs`, `Documents/originals` und `Error Cases/`. Es erzeugt keine
DB, registriert keinen Kontext, exportiert keinen Release und aktiviert nichts.

Leere Workspace-DBs entstehen als atomare Sequenz:

```text
prepare_pipeline_workspace_root -> create_empty_corpus_db -> activate_corpus_context
```

Allgemeine Default-Blueprint-Archive entstehen als atomare Sequenz:

```text
prepare_pipeline_workspace_root -> create_empty_corpus_db -> export_default_blueprint_release -> activation_preflight -> activate_release_on_existing_db -> activate_corpus_context
```

Neue DBs aus einem bereits exportierten Release entstehen als atomare Sequenz:

```text
create_empty_corpus_db -> activation_preflight -> activate_release_on_existing_db -> activate_corpus_context
```

Neue DBs aus vorhandenen Pipeline-Artefakten entstehen als atomare Sequenz:

```text
create_empty_corpus_db -> activation_preflight -> activate_release_on_existing_db -> activate_corpus_context -> rebuild_corpus_from_artifacts(replace_existing=false)
```

`activate_corpus_context` ist nur ein Kontext-Switch fuer Pfade und aktive DB.
Es aktiviert kein Extraktionspaket, keine Sprache und kein Dokumentprofil.
Spezialarchive werden aus atomaren Schritten zusammengesetzt:

```text
prepare_pipeline_workspace_root -> create_empty_corpus_db -> create_working_release_package -> export_working_release -> activation_preflight -> activate_release_on_existing_db -> activate_corpus_context -> verify_workspace_active_release
```

Revisionsentscheidungen fuer bestehende Custom-Archive bleiben ebenfalls
atomar:

```text
create_working_release_package -> export_working_release -> read_revision_candidate_release -> inspect_release_revision_context -> activation_preflight -> classify_release_revision
```

Wenn `activation_preflight` fuer eine bestehende DB eine Bestaetigung verlangt,
schreibt `write_workspace_release_change_confirmation` nur das noetige
Confirmation-Artefakt. Bei bewusstem Reset schreibt
`write_workspace_db_reset_confirmation` nur das Reset-Confirmation-Artefakt;
der eigentliche Reset bleibt der getrennte Schritt `reset_active_corpus_db`.

## Semantic Control Kernel Cutover

Seit Phase 14 ist die kanonische Kernel-Surface im MCP die Semantic Control
Kernel Bridge. Der MCP Server startet das Kernel-Modul ueber den lokalen
Subprocess-Contract `python -m semantic_control_kernel.orchestrator_contract`
und importiert das Schwester-Package nicht direkt.

- Normales `tools/list` exponiert nur die 16 permanenten Semantic Control
  Kernel Workflow-/Support-Namen. Alle Schemas sind leer, ausser
  `kernel_continue_resumable_workflow`, das nur das opaque
  `resume_option_ref` aus `kernel_resume_state.resume_options[]` akzeptiert.
- Event-scoped Recovery-Tools bleiben fuer normale Agentenaufrufe unsichtbar
  und werden nur mit aktiver Kernel-Mirror-Event-Scope akzeptiert.
- Host-only Client-Frontend-Bridge-Operationen sind keine Agent-Tools. Sie
  laufen ueber `semantic_control_kernel_client_frontend_bridge.py` und werden
  im `stdio`-Transport nur akzeptiert, wenn der lokale Frontend-Host den beim
  MCP-Start gesetzten `VISION_MCP_HOST_BRIDGE_TOKEN` als opaque
  `host_bridge_token` mitsendet. Der Token wird nicht an den Kernel
  weitergereicht.
- `kernel_submit_user_interaction_response` laesst kurze
  Ziel-Sammeldialoge inline weiterlaufen, startet lange Kernel-Fortsetzungen
  aber nicht inline im `stdio`-MCP-Call. Der Kernel persistiert die Antwort,
  schreibt einen sichtbaren Background-Continuation-Progress-Eintrag, startet
  die Hintergrund-Continuation und gibt sofort eine kleine
  `background_continuation`-Referenz zurueck, damit
  `kernel_list_client_frontend_events` waehrend LLM-Calls weiter pollbar bleibt.
  Der Background-Child darf keine vom MCP-Contract-Subprozess geerbten
  Capture-Handles offen halten.
- Die fruehere MCP-hosted Legacy-Surface ist retired. Runtime, Registry,
  Permissions, Produktsemantik und Manifest tragen nur noch die Semantic
  Control Kernel Bridge und ihre kanonischen Tool-Namen.
- Die Produktsemantik fuehrt
  `empty_database_default_taxonomy_no_projections` als oeffentlichen
  "Default-Taxonomie jetzt, Custom-Projections danach"-Setup-Pfad. Empfehlungen
  duerfen diesen Workflow nennen, aber die Fortsetzung zu
  `create_custom_projection_path` bleibt Kernel-governed ueber
  `kernel_resume_state` und `kernel_continue_resumable_workflow`.

## Tool-Familien und normaler Agentenpfad

Normale Agentenarbeit nutzt die Semantic Control Kernel Workflow-Surface;
atomare Owner-Tools bleiben darunterliegende MCP-Primitives. Die frueheren
Scope-Surfaces
`inspect_extraction_packs`, `check_working_release_readiness`,
`broaden_custom_release` und `normalizer_source_action` sind retired und stehen
nicht mehr im sichtbaren MCP-Katalog.

- Orientation/Lesen: `list_default_blueprints`, `read_working_release`,
  `list_working_release_profiles` und `read_working_release_profile` liefern die
  frueher gebuendelten Informationen als getrennte read-only Schritte.
- Working-Release lesen/pruefen/bauen/exportieren:
  `read_working_release`, `list_working_release_profiles`,
  `read_working_release_profile`, `validate_working_release`,
  `compile_working_release`, `preview_working_release_impact`,
  `create_working_release_package` und `export_working_release` sind getrennte
  Schritte.
- Authoring: `derive_working_release_from_blueprint`,
  `create_minimal_custom_release`, `create_projection_draft`,
  `create_locale_scaffold`, `generate_locale_translation_payload` und
  `translate_working_release_locale` schreiben oder erzeugen nur ihren
  benannten Authoring-Schritt.
- Review/Apply: Bootstrap- und data-informed Refinement bleiben in Review- und
  Apply-Tools getrennt.
- Glossary: `read_translation_glossary`,
  `upsert_translation_glossary_entry` und
  `remove_translation_glossary_entry` ersetzen das fruehere
  Sammelwerkzeug. Es gibt keine `operation`-Union mehr im sichtbaren Katalog.
- Workspace/Activation: Workspace-, Export-, Preflight-, Aktivierungs-,
  Reset-, Backfill- und Run-Tools bleiben eigene operative Schritte.
- Admin/Debug: Es gibt keinen sichtbaren generischen Normalizer-Source-
  Escape-Hatch mehr. Neue MCP-Surfaces muessen dedizierte atomare Tools sein.

Fuer Working-Releases gibt es atomare Authoring-Tools. Sie ersetzen fuer Lesen,
Pruefen, Bauen, Impact-Vorschau und Export den generischen
Normalizer-Source-Contract im normalen Agentenfluss:

- `read_working_release` liest nur das Release-Paket.
- `list_working_release_profiles` listet nur Profile.
- `read_working_release_profile` liest genau ein Profil.
- `validate_working_release` validiert, kompiliert aber nicht.
- `compile_working_release` kompiliert, exportiert aber nicht.
- `preview_working_release_impact` liest nur die gespeicherte Source-Auswirkung.
- `create_working_release_package` ruft genau `create_release_package` im
  workspace-lokalen Normalizer-Home auf.
- `export_working_release` exportiert an einen expliziten `output_path`, aktiviert aber nicht.

Alle diese Tools verlangen `artifact_folder` und arbeiten ueber das
workspace-lokale Normalizer-Home `<artifact_folder>/.vp/n`. Export-Ziele unter
MCP-`state/semantic_releases` sind gesperrt, weil der MCP dort keine
Semantic-Release-Dauerwahrheit fuehren darf.

Bootstrap- und data-informed Refinement sind strikt in Review und Apply
getrennt:

- `review_bootstrap_release` prueft `goal`, `must_keep` und
  `noise_tolerance` gegen das gespeicherte Working Source Package. Es ruft nur
  die Normalizer-Owner-Action `review_bootstrap_release` auf.
- `apply_bootstrap_release` schreibt den Bootstrap-Draft nach
  `user_confirmed=true`. Es ruft nur `bootstrap_release_package` auf.
- `review_data_informed_release` prueft `structured_sample_path` und
  `expected_normalized_path`, optional mit `original_reference_path` und
  `sample_label`. Es ruft nur `review_data_informed_release` auf.
- `refine_working_release_from_sample` schreibt sample-basierte Refinements nach
  `user_confirmed=true`. Es ruft nur `refine_release_package` auf.

Der sichere Ablauf ist:

```text
Review -> Apply -> Validate -> Compile -> Export
```

Keines dieser vier Review-/Apply-Tools validiert, kompiliert, exportiert oder
aktiviert. Review-Tools schreiben keinen Normalizer-Source-State. Apply-Tools
akzeptieren optional `expected_candidate_fingerprint`; wenn dieser Wert gesetzt
ist, muss ein passender MCP-Support-Checkpoint aus dem vorherigen Review unter
`state/support/release_review_checkpoints.jsonl` existieren. Dieser Checkpoint
enthaelt nur Workflow-Schutzdaten wie Candidate-Fingerprint, Artifact-Folder und
Input-Hash. Er ist keine zweite fachliche Wahrheit. Ohne Fingerprint ist Apply
mit `user_confirmed=true` weiterhin moeglich, aber der MCP kann dann nicht
beweisen, dass exakt derselbe Candidate angewendet wird, den der Agent zuvor
geprueft hat.

`inspect_active_workspace_status` ist der schlanke operative Vorcheck fuer "was
ist gerade los?". Es liest den gespeicherten Orchestrator-Kontext, zaehlt den
registrierten `Input/`-Ordner, fasst den letzten MCP-gestarteten Lauf knapp
zusammen und liefert genau einen `next_action`-Hinweis. Es ersetzt keine
Run-Details und keine Governance-Introspection.

`start_active_pipeline_run` ist der normale Startknopf fuer "Verarbeitung
starten" im Chat. Es liest den gespeicherten Orchestrator-Kontext, prueft den
registrierten `Input/`-Ordner, startet den Batch im Hintergrund und gibt sofort
eine `run_id` zurueck. `inspect_active_pipeline_run` liefert danach
Zwischenstand, Laufzeit, Log-Auszug und das finale Ergebnis. `run_active_pipeline`
bleibt als synchroner, blockierender Run fuer Tests oder bewusst wartende
Automationen verfuegbar. Damit muss der Agent nicht aus einer leeren DB
schliessen, dass keine Quelldateien vorhanden sind.

Wenn der MCP-Server nach einem Hintergrundstart neu gestartet wurde und keinen
live verwalteten Prozess mehr besitzt, markieren
`inspect_active_pipeline_run` und `cancel_active_pipeline_run` den Lauf als
`interrupted`. Der MCP versucht dann keinen PID-Reattach und behauptet keinen
erfolgreichen Cancel; die sichere naechste Aktion ist Log-Inspektion oder ein
bewusster Neustart des Runs.

Fuer neue User soll der Pipeline Manager vor einer DB-Erstellung immer zwischen
drei Startarten unterscheiden:

- Leere DB: technische Sammlung ohne aktives Extraktionspaket.
- Allgemeines Dokumentenarchiv: Default-Blueprint mit den Standardprofilen.
- Spezialarchiv: eigenes Working-Extraktionspaket, optional mit neuen
  Dokumentprofilen, danach Export, Preflight, ggf. Confirmation, Aktivierung,
  Kontextwechsel und `verify_workspace_active_release` als getrennte Schritte.

Die Hilfswerkzeuge dafuer sind bewusst flach:

- Fuer Defaultpakete, aktive Working-Struktur, Sprachen und Dokumentprofile gibt
  es kein Sammel-Uebersichtstool mehr. Nutze `list_default_blueprints`,
  `read_working_release`, `list_working_release_profiles` und bei Bedarf
  `read_working_release_profile`.
- `inspect_source_document_sample` kopiert ein einzelnes User-Beispieldokument in
  einen temporaeren Orchestrator-Inspection-Bereich, laesst den Optimizer lokal
  darauf laufen und gibt kompakte Auszuege, Ueberschriften, feldartige Hinweise
  und Kandidatenmarker zurueck. Es importiert nichts in die DB und aktiviert kein
  Extraktionspaket. Fuer Spezialarchive soll der Agent damit weniger raten und
  seine vorgeschlagenen Profile/Felder aus dem Beispiel ableiten.
- `list_default_blueprints` liest nur immutable Default-Blueprints; es leitet
  keinen Working-Draft ab.
- `derive_working_release_from_blueprint` kopiert genau einen Blueprint in das
  workspace-lokale Working Source Package. Es validiert, kompiliert, exportiert
  und aktiviert nichts.
- `create_minimal_custom_release` ersetzt nur das workspace-lokale Custom Source
  Package. Es inspiziert keine Samples, exportiert nicht und aktiviert nichts.
- `create_projection_draft` legt ein neues Dokumentprofil an, z. B. fuer
  Story-/Fantasy-/Lore-Archive oder andere projektspezifische Inhalte, und darf
  keine neuen Master-Terme erfinden.
- `create_working_release_package` baut nur das workspace-lokale Release-Package
  aus vorhandenen Source-Dateien und optionalen `projection_ids`; fuer
  technische Readiness danach getrennt `validate_working_release` und
  `compile_working_release` nutzen.
- Fuer Broadening-Flows gibt es kein `broaden_custom_release` mehr. Nutze
  `create_minimal_custom_release` oder `create_projection_draft`, danach
  `create_working_release_package`, `export_working_release` und bei Bedarf
  `read_revision_candidate_release`, `inspect_release_revision_context`,
  `activation_preflight` und `classify_release_revision` als separate Schritte.
- `create_locale_scaffold` legt Locale-Dateien an, uebersetzt aber nicht.
- `generate_locale_translation_payload` erzeugt nur einen pruefbaren
  Uebersetzungsvorschlag fuer Labels/Hinweise; es schreibt nichts.
- `translate_working_release_locale` wendet nur einen expliziten
  `translation_payload` auf eine scaffolded Locale an; es generiert keinen
  Payload und aktiviert nichts.

Glossary-Arbeit ist ebenfalls atomar:

- `read_translation_glossary` liest nur die Eintraege einer Locale.
- `upsert_translation_glossary_entry` liest die Locale, validiert die
  aktualisierte Owner-Surface und schreibt genau einen hinzugefuegten oder
  ersetzten Eintrag.
- `remove_translation_glossary_entry` liest die Locale, validiert die
  aktualisierte Owner-Surface und schreibt genau einen entfernten Eintrag. Wenn
  der Eintrag nicht existiert, wird nichts geschrieben und `entry_status:
  not_found` gemeldet.

Alle drei Glossary-Tools akzeptieren optional `artifact_folder`, damit
Custom-Archive unter `<artifact_folder>/.vp/n` bleiben. Die globale Default-Line
wird fuer Custom-Archive nicht direkt beschrieben.

## Admin und Nicht-Schreibregeln

`normalizer_source_action` ist retired und bleibt nicht als sichtbarer
generischer Escape-Hatch im MCP-Katalog. Normalizer-Source-Actions muessen ueber
dedizierte atomare MCP-Tools exponiert werden; ein neues Sammel- oder
Payload-Tool ist kein Ersatzpfad.

Der MCP schreibt nie direkt:

- fremden Owner-State ausserhalb manifestierter Owner-Contracts
- die globale Normalizer-Source-Line fuer Custom-Archive
- Corpus-DB-Rohzustand oder Corpus-Sidecars
- Orchestrator-Credentials oder Runtime-State als eigene MCP-Wahrheit
- Semantic-Release-Dauerwahrheit unter MCP-`state/`

Persistente fachliche Wahrheit bleibt beim jeweiligen Owner. MCP-eigene
mutable Wahrheit beschraenkt sich auf Permission-Policy und Support-/Run-
Hilfsstate.

## Semantic Control Kernel Build Status

Die sichtbare Kernel-Surface im MCP ist jetzt ausschliesslich die Semantic
Control Kernel Bridge aus Phase 14:

- `tool_catalog.py` aggregiert die 16 permanenten Semantic Control Kernel
  Workflow-/Support-Tools.
- `tool_handler_registry.py` registriert nur die Bridge-Handler aus
  `tool_handlers_semantic_control_kernel.py`; die alte action-catalog/open/
  inspect/execute-Surface ist nicht mehr registriert.
- `tool_visibility.py` und `semantic_control_kernel_visibility.py` blocken
  legacy Namen vor Registry-Lookup fail-closed mit
  `legacy_kernel_surface_retired`.
- `permission_defaults.py` und `config/agent_permissions.json` behandeln die
  16 permanenten Kernel-Workflow-/Support-Namen als eine gemeinsame
  Kernel-Transport-Surface. Das ist bewusst keine MCP-seitige
  Read/Write-Klassifizierung der einzelnen Kernel-Workflows: Der MCP
  transportiert die eine kanonische Kernel-Surface, waehrend der Kernel
  Authority, Dialoge, Locks, Resume, Recovery und Receipt-State erzwingt.
  Event-scoped Recovery-, Host-only-Bridge- und Internal-Namen bleiben
  ausserhalb der normalen Agent-Toolliste.
- `runtime/runtime-manifest.json` paketiert nur noch die Bridge-Dateien, nicht
  das alte MCP-hosted Kernel-Package.

Der MCP baut damit keine zweite Business-Logic-Welt. Workflow-Entscheidungen,
Locks, Receipts, Recovery und Resume gehoeren dem Semantic Control Kernel;
Owner Truth bleibt bei den Owner-Contracts und deren atomaren MCP-Primitives.
Ein historischer MCP-Legacy-State-Ordner kann seit Phase 15 nur noch als
Support-Evidence bestehen. Aktiver Kernel-State liegt ausschliesslich im
Kernel-Modul unter:

```text
../08 - Semantic Control Kernel/state
```

Threat Boundary: Der Kernel erzwingt Authority auf der MCP-Fassade und auf den
internen Kernel-Syscall-Pfaden. Er ist keine OS-, Shell-, Dateisystem- oder
Python-Direktimport-Sandbox und behauptet keinen Schutz gegen out-of-band
Eingriffe ausserhalb dieser MCP-Grenzen.

## Agent Permissions

Der Server besitzt jetzt eine eigene Edit-Suite-Surface:

```text
mcp_server.agent_permissions
```

Sie schreibt ausschliesslich `config/agent_permissions.json` im MCP-Server-Modul.
Die Policy wird vor jedem Tool-Call ausgewertet, bevor ein Owner-Contract
gestartet wird. Die Level sind:

- `L0_READONLY`: Inspektion, Read-Surfaces, read-only Corpus-Diagnostik und
  die gemeinsame Semantic-Control-Kernel-Transport-Surface. Effekt und
  Workflow-Authority dieser Kernel-Tools werden im Kernel entschieden, nicht
  durch eine zweite MCP-seitige Workflow-Klassifizierung.
- `L1_AUTHOR`: atomare Working-Release-Reads, Validierung, Compile, Export,
  Glossary-Read und sichere Authoring-Checks ohne Runtime-State-Wechsel
- `L2_OPERATOR`: Source-Authoring-Apply, Glossary-Upsert/Remove,
  Corpus-Kontext, Release-Aktivierung, Rebuild, Merge, Reset und Embeddings
- `L3_ADMIN`: Owner-Surface-Writes, Runtime-Settings, Credentials und
  auditiertes Secret-Reveal

Der aktive Level kommt aus `VISION_MCP_AGENT_LEVEL`; ohne Environment-Wert gilt
`default_agent_level`. `maximum_agent_level` ist eine harte Obergrenze, damit ein
Agent seinen Level nicht ueber die Edit-Suite-Policy hinaus anheben kann.
Die mitgelieferte Policy startet konservativ mit `default_agent_level:
L1_AUTHOR`; Operator- und Admin-Sessions muessen ihren Level bewusst per Policy
oder Environment anheben.

In der Edit Suite erscheint diese Surface als gefuehrter Permission-Editor:
Level koennen per `Activate ...`-Button umgestellt werden, ohne JSON zu
bearbeiten. Die Maximalstufe kann separat als Sicherheitskappe gesetzt werden.

## Support Monitor und Bug Reports

Installierte Runtime-Builds patchen keinen Produktcode direkt und brauchen keine
Git-Anbindung. Die fruehere Sammel-Surface `support_incident_workflow` ist im
sichtbaren MCP-Katalog retired. Die Ersatzsequenz ist atomar:

```text
assess_support_incident -> preview_support_bug_report -> build_support_bug_report -> queue_support_bug_report
```

Ergaenzend gibt es `list_support_incidents` fuer die Uebersicht und
`dismiss_support_incident` fuer das Ausblenden eines bekannten Incidents.

Die erste Stufe ist immer `assess`. Nicht reportable sind `missing_path`,
`invalid_user_input`, `missing_configuration`, `expected_preflight_failure`,
`permission_denied`, `external_dependency_failure` und `unknown`. Diese Klassen
sollen dem User als Setup-, Eingabe- oder Umgebungsproblem erklaert werden.

Nur `unexpected_exception`, `contract_regression`,
`repeatable_product_failure` und `data_corruption_risk` duerfen eine
reportable `assessment_id` erzeugen. `preview_support_bug_report`,
`build_support_bug_report` und `queue_support_bug_report` akzeptieren nur eine
solche `assessment_id`; `queue_support_bug_report` verlangt zusaetzlich
`user_confirmed=true` und legt weiterhin nur lokal unter `state/support/outbox/`
ab. Ein spaeterer Connector kann diese Outbox in Git-Issues oder ein anderes
Development-Ticketing ueberfuehren.

Die Edit Suite zeigt den Support Monitor als read-only Surface:

```text
mcp_server.support_monitor
```

Sobald aktive Incidents vorhanden sind, erscheinen dort pro Incident direkte
atomare Aktionen:

- `Assess`: klassifiziert den Incident und erzeugt ggf. eine `assessment_id`
- `Preview`: zeigt den Report-Inhalt nur fuer reportable Assessments an
- `Build Report`: schreibt die JSON-Datei nach `state/support/bug_reports/`
- `Queue Report`: legt den Report nach User-Bestaetigung in `state/support/outbox/`
- `Dismiss`: blendet den Incident aus der aktiven Liste aus

## Start

```bat
run.bat
```

Der Server spricht MCP ueber `Content-Length`-geframte JSON-RPC-Nachrichten auf stdin/stdout.

Tool-Katalog ohne Serverloop:

```bat
run.bat --list-tools
```

Runtime-Preflight:

```bat
check-runtime.bat
```

`check-runtime.bat` laeuft strikt gegen die gebuendelte Runtime. Das Tool
`mcp_server.healthcheck` kann denselben Check mit `strict_runtime=true`
erzwingen; ohne diesen Schalter bleibt es fuer Dev- und Handover-Diagnostik aus
der lokalen Test-venv nutzbar und meldet im Runtime-Block, ob die aktuelle
Python-Exe self-contained ist.

## Mutable Artefakte

Servereigener mutable State liegt unter:

```text
state/
```

Der Server schreibt dort nur eigene Arbeitsartefakte, z. B. temporare
Contract-Call-Dateien, Pipeline-Run-Metadaten oder Support-Reports. Semantic
Release Bundles gehoeren in explizite User-, Corpus- oder Workspace-Zielpfade.

## Dev-Tests

```bat
dev-tests\bootstrap.bat
dev-tests\run-tests.bat
```

Die Suite prueft Katalog-Governance, MCP-Framing, Owner-Delegation und den pfadstabilen Healthcheck-Contract.

## Abweichungslog

- `SHOULD: Ergebnisdateien bleiben ungefaehr bei 200 LOC oder darunter`
  - Aktueller Stand: einige pfadstabile MCP-Surfaces und Regressionstests liegen weiterhin oberhalb der Richtgroesse, insbesondere `mcp_server/product_semantics_support.py`, `mcp_server/semantic_control_kernel_client.py`, `mcp_server/tool_handler_source_fit_review.py`, `dev-tests/tests/test_agent_permissions.py`, `dev-tests/tests/test_semantic_control_kernel_host_only_client_bridge.py`, `dev-tests/tests/test_tool_handlers_source_fit.py` und `dev-tests/tests/tool_contract_matrix_recorder.py`.
  - Grund: diese Dateien bilden jeweils eine zusammenhaengende Surface oder einen bewusst dichten Regression-Block; ein rein numerischer Split waere aktuell mehr Umverteilung als echte Vereinfachung.
  - Risiko wenn offen: weitere Aenderungen koennen Ownership und Reviewbarkeit erschweren, bis ein spaeterer pfadstabiler Schnitt die Verantwortung klarer trennt.
