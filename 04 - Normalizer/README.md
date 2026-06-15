# 04 - Normalizer
`04 - Normalizer` liest `*.structured.json`, waehlt eine Taxonomie-Projektion und schreibt pro Eingabedatei genau eine `*.structured.normalized.json`.
## Zweck
- kanonische Zweitsicht fuer Retrieval, Validation und Corpus-Building
- release-owned Projection-Routing aus lokalen Projection-Assets
- Semantic Release und Runtime Semantic Assets fuer nachgelagerte Module
- headless Betrieb ueber den Orchestrator-Contract

## Projection Release Contract
- `SPEC_Projection_Release.md` ist die Root-Ausfuehrungsgrundlage fuer das release-getriebene Projection-Routing.
- Die release-owned Routingmarker liegen in den Projection-Dateien unter `routing.surface_signals`.
- `surface_signals` fuehrt genau `text_markers`, `domain_markers`, `section_roles` und `party_roles`.
- `build_semantic_release` validiert diese Projection-Signale fail-closed.
- `build_runtime_semantic_assets` kompiliert daraus `semantic_extraction_policy_v2`, ohne das Top-Level-Format `runtime_semantic_assets_v1` zu aendern.
- Die OCR-Defaults des Runtime-Bundles deklarieren nur den Orchestrator-gefuehrten LLM-OCR-Port `optimizer-llm-ocr` sowie Scan-, Vision-Route- und Renderparameter; lokale Paddle-, GPU-/CPU- und Device-Fallback-Policies sind ungueltige Altlasten.
- `projection_routing` steuert die Arbitration zwischen lokaler Evidenz und
  Interpreter-Hints.
- `projection_hint_mode=advisory` bleibt der Default.
- `projection.selection.reason` ist die sichtbare Begruendungssurface fuer lokale Score-Lage, Hint-Prior und Rejection-Grund.

## Public Contract
`module-manifest.json` exponiert diese Actions:

- `normalize_document`
- `build_projection_catalog`
- `build_runtime_semantic_assets`
- `publish_semantic_release`
- `list_default_blueprints`
- `export_default_blueprint_release`
- `create_zero_shot_working_release`
- `healthcheck`
- `debug_run`

Wesentliche Invarianten:

- keine Manifest- oder Action-Drift
- unbekannte Request-Felder werden fuer alle Public-Contract-Actions abgelehnt
- `normalize_document`, `healthcheck` und `debug_run` verlangen `runtime_settings`
- `normalize_document.structured_path` muss auf `*.structured.json` enden; `normalized_output_path` muss eine JSON-Datei sein
- `debug_run` akzeptiert keine Debug-Roots auf `config/`, `runtime/`, `vendor/` oder dem Modulroot
- `build_runtime_semantic_assets` akzeptiert nur `action` plus vollstaendigen Semantic-Release-Payload
- `publish_semantic_release` exportiert ausschliesslich aus gespeicherten Owner-Dateien
- `create_zero_shot_working_release` leitet das Working Package aus einem immutable Blueprint ab, kompiliert es und exportiert ein Release-Bundle ohne Corpus- oder Orchestrator-State zu schreiben
- Kernel-owned detached custom releases werden nicht ueber `publish_semantic_release` gebaut. Der Edit-Contract action `materialize_semantic_release_candidate` schreibt aus Kernel-`release_ref`, Base-Release und Projection-Update-State ein vollstaendiges `release.json` inklusive `projection_catalog` und `runtime_semantic_assets`. Das Bundle enthaelt top-level `fingerprint` und den aliasgleichen `release_fingerprint`, damit Merge- und Rebuild-Kernelpfade dieselbe Release-Identitaet pruefen koennen.
- Kernel-owned database merges verwenden `merge_semantic_release_candidates`
  mit vollstaendigen `source_release_refs`. Die Action dedupliziert gleiche
  Taxonomy-/Projection-Identitaeten mit gleichem Fingerprint, meldet gleiche
  IDs mit abweichendem Fingerprint als Collision und fuehrt unterschiedliche
  Taxonomien additiv zu einem reconciled `taxonomy_ref` zusammen. Das Ergebnis
  enthaelt `reconciled_taxonomy_ref` und `reconciled_projection_refs` top-level
  sowie dieselben Refs im `semantic_merge_package`, damit der Kernel daraus
  ohne Chat-Pfade eine neue Custom Semantic Release bauen kann.
- Preview-, Single-Run- und Batch-Routing nutzen dieselbe Arbitration-Logik
- Modellantworten muessen die Top-Level-Sektionen `processing`, `classification`, `context` und `content` als JSON-Objekte liefern; fehlende Sektionen werden nicht still auf `{}` normalisiert

Schema-Modi:

- API-Key Provider nutzen `json_schema` mit `strict=true`, wenn das aktive Schema strict-kompatibel ist.
- Wenn strict Schema vom Transport nicht angenommen wird, faellt der Provider fuer diesen Versuch auf `json_object` zurueck; der lokale Parser bleibt trotzdem hart gegen fehlende Top-Level-Sektionen.
- OpenAI OAuth laeuft ueber den orchestrator-owned Backend-Transport aktuell mit `json_object`; Auth, Modell und Tokenbudget bleiben request-owned und werden nicht lokal persistiert.

## Lokale Config und Assets
`config/config.yaml` enthaelt nur projektlokale Werte:

- `timeout_seconds`
- `max_retries`
- `retry_delay_seconds`
- `structured_outputs`
- `default_workers`
- `max_structured_bytes`
- `max_batch_files`
- `max_batch_workers`
- `taxonomy_profile_id`
- `projection_hint_mode`
- `projection_routing.*`

Lokale Assets unter `config/`:

- `prompt_bundle.json`
- `prompt_overrides.json`
- `taxonomy_sources/<release_id>/`
- `semantic_release.recipe.json`

Release-bezogene Aussagen:

- `config/taxonomy_sources/<release_id>/` ist die neue source-first Authoring-Primarschicht fuer Release, Master und Projection-Texte/Core.
- Schritt 3 kompiliert dieses Source-Paket fail-closed zu release-faehigen Payloads im Speicher.
- Die release recipe bleibt die Legacy-Aktivierungssurface; `release_id`, `release_version` und `projection_ids` muessen zum aktiven `release.yaml` passen.
- Runtime-Felder wie `model`, `max_output_tokens` und Auth bleiben request-owned und werden nicht lokal gespeichert.

## Edit Contract
Entry-Point:

```bat
python -m normalizer_vision.edit_contract --request <request.json> --response <response.json>
```

Sichtbare Surfaces:

- `normalizer.settings`
- `normalizer.prompt_overrides`
- `normalizer.prompt_bundle`
- `normalizer.taxonomy_master`
- `normalizer.taxonomy_profiles`
- `normalizer.translation_glossary`
- `normalizer.semantic_release_authoring`
- `normalizer.debug_capabilities`

Owner-Regeln:

- `normalizer.settings` owns `projection_hint_mode` und `projection_routing.*`
- `config/taxonomy_sources/<release_id>/` ist die Authoring-Wahrheit fuer release-getriebene Builds.
- `normalizer.taxonomy_master` schreibt `master.core.yaml` plus `master.text.en.yaml`; `normalizer.taxonomy_profiles` schreibt `projections/<projection_id>.core.yaml` plus `.text.en.yaml`.
- `normalizer.translation_glossary` schreibt optional `translation_glossary.en.yaml` als eigene `authoring_only` Surface fuer englische Control-Terminologie.
- `normalizer.semantic_release_authoring` schreibt `release.yaml` und synchronisiert additiv `config/semantic_release.recipe.json`; Export bleibt damit kompatibel, und `activate_semantic_release` ist als Edit-Contract-Proxy verfuegbar, waehrend die Aktivierungs-Ownership fachlich bei `05` bleibt.
- `Export Semantic Release` und `Activate Semantic Release` validieren zuerst das Source-Paket, kompilieren dann release-faehige Payloads im Speicher und uebergeben nur exportierte `.json`-Release-Bundles an `05 - Corpus Builder`.
- Taxonomie-Surfaces zeigen source-layer Slot-Metadaten und triggern `Preview Impact`, `Review Bootstrap`, `Bootstrap Package`, `Review Data-Informed`, `Refine From Sample`, `Validate Package`, `Compile Package` und `Export Semantic Release`; die Semantic-Release-Surface bietet additiv `Activate Semantic Release` mit `release_path` und `corpus_db_path`.
- `Review Bootstrap` und `Review Data-Informed` bleiben read-only; sie laufen auf derselben Draft-Planungslogik wie `Bootstrap Package` und `Refine From Sample`, schreiben aber nichts.
- `Bootstrap Package` und `Refine From Sample` mutieren strikt source-first nur `config/taxonomy_sources/<release_id>/`; exportierte Semantic-Release-Artefakte aendern sich erst nach `Validate Package` und `Compile Package`.
- `create_projection_draft` erstellt aus einer Template-Projection in einem Schritt einen gespeicherten Draft fuer Core-Coverage, Routing-Text und Routing-Lexikon; der Draft bleibt source-first lokal, bis spaeter validiert und kompiliert wird.
- `set_locale_text` und `set_routing_lexicon` arbeiten nur auf der kanonischen Control-Locale `en`; andere Taxonomy-/Runtime-Locales werden fail-closed abgewiesen.
- `compile_release_package(target_locale?: str)` und `export_semantic_release(target_locale?: str)` akzeptieren nur `en` als expliziten Override. Ohne Override verwenden beide `default_runtime_locale` aus dem Source Package, aktuell `en`. Diese Locale ist die interne Control-Sprache fuer Labels, Guidance und Runtime Assets, nicht die Sprache jedes Quelldokuments; mehrsprachige Dokumente werden in diese Control-Sprache normalisiert.
- `create_minimal_custom_release` ersetzt das aktive Working Source Package bewusst durch ein kleines Custom Package fuer ein Spezialarchiv; danach sind Validate, Compile, Export und Corpus-Aktivierung weiterhin getrennte Schritte.
- `materialize_semantic_release_candidate` ist die Kernel-Owner-Aktion fuer detached Custom-Release-Bundles. Sie liest ein bereits geschriebenes Base-Release, materialisiert die Custom Projection aus Kernel-Update-State und schreibt ein Corpus-Builder-faehiges Release-Bundle, ohne das aktive Working Source Package zu ersetzen.
- Custom Projection Materialisierung konsumiert `projection_precursors` aus dem Kernel-Update-State als Identitaets- und Include-Quelle. Phase-19-Platzhalter wie `projection_phase19` duerfen nur in Tests auftauchen, wenn sie explizit im Payload stehen, nicht als erzwungener Runtime-Fallback.
- `create_and_activate_new_corpus_db` exportiert ein validiertes Release-Bundle und delegiert fail-closed an `05 - Corpus Builder`; ohne dessen gebuendelte Runtime gibt es keinen Fallback auf den Normalizer-Python.
- `normalizer.debug_capabilities` bleibt read-only

## Debug- und Orchestrator-Pfade
- Der produktive Betrieb laeuft ausschliesslich ueber `normalizer_vision.orchestrator_contract`.
- `debug_run` ist die einzige Run-/Debug-Surface fuer den Orchestrator-Host.
- `build_projection_catalog` bleibt ein lokaler Legacy-/Admin-/Debug-Pfad fuer source-backed Release-Analysen.
- Der generische Debug-Host entdeckt die Capabilities rein ueber
  `module-manifest.json`.

## Runtime und Packaging
- `build-runtime.bat` baut `runtime/python` offline aus mitgelieferten Artefakten.
- `check-runtime.bat` validiert Runtime und Modulvertrag.
- `installer.bat` installiert den Modulslot unter `%LOCALAPPDATA%\Programs\Vision Pipeline\04 - Normalizer`.
- Mutable Daten bleiben `config/config.yaml`, `output/` und `state/`.
- `runtime/` ist kein Owner fuer Projection-Routing und wird von diesem Umbau nicht manuell gepflegt.

## Production Readiness
- `check-runtime.bat` und `dev-tests\run-tests.bat` bilden die Runtime-/Dev-Gates.
- LOC-Governance haelt Produkt-, Test- und dev-tool-Python-Dateien unter 200 LOC.
- Lokale mutable Artefakte unter `output/`, `state/`, `.tmp` und pytest-Cache-Ordnern sind nicht Teil des Installer-/Runtime-Vertrags und werden nicht automatisch geloescht.

## Tests
```bat
dev-tests\bootstrap.bat && dev-tests\run-tests.bat
```

Direkt mit dem Suite-Python:

```bat
dev-tests\.venv\python.exe -m pytest dev-tests\tests
```

Die Suite deckt ab:

- Semantic Release, Runtime Semantic Assets, Projection Routing und Hint-Arbitration
- Edit Contract sowie Contract-/Packaging-Grenzen

Cross-Module-Ratchets in `tools/dev-tests` pruefen zusaetzlich:

- `04`-Compiler-Ergebnis gegen die eingecheckte `01`-Fixture und die publizierten `05`-Release-Spiegel
- Terminologie- und LOC-Drift zwischen SPEC, README und Edit Contract

## Governance
- README, Edit Contract, Slot-Summary und Tooling verwenden dieselbe Begriffswelt: `routing.surface_signals`, `semantic_extraction_policy_v2`, `projection_routing`, `projection_hint_mode=advisory`, `projection.selection.reason`.
- `runtime/` und andere Spiegel bleiben fuer diese Routing-Semantik unberuehrt.
- Solange die Cross-Module-Ratchets fuer `04 -> 01` oder `04 -> 05` rot sind, gelten spaetere Robustheits-, Verifizierungs- oder Ratchet-Claims nicht als freigegeben.
- Schwester-Module konsumieren nur `runtime_semantic_assets_v1`, `projection_catalog`, `context.projection_hint` und `projection.selection`.

## Abweichungslog
| Modul | Regel | Abweichung | Grund | Owner | Follow-up Datum | Risiko wenn offen |
| --- | --- | --- | --- | --- | --- | --- |
| 04 - Normalizer | SHOULD: lokale Maintenance-Pfade bleiben minimal | `build_projection_catalog` bleibt als Legacy-/Admin-/Debug-Surface sichtbar, obwohl der Normalpfad ueber Semantic Release und Runtime Assets laeuft | Orchestrator, Debug-Host und Owner-Workflows brauchen einen gespeicherten Discovery-Pfad ohne Run | Codex | 2026-05-08 | lokale Maintenance und Produktpfad koennen sonst begrifflich auseinanderlaufen |
| 04 - Normalizer | SHOULD: Modellwahl bleibt voll owner-lokal editierbar | produktive Runtime-Felder bleiben request-owned und sind bewusst nicht Teil des Edit Contracts | Modellwahl und Auth sind orchestrator-owned, nicht normalizer-owned | Plattform | 2026-05-08 | lokale Konfigurationswahrheit wuerde wieder in Richtung Hidden Runtime Defaults driften |

## Phase 19 Semantic Release Domain Service
- The Phase 19 owner lives only in `normalizer_vision`.
- No `normalizer_file` owner exists and no database attach/activate step moved into the Normalizer.
- Edit-contract owner actions:
  - `materialize_custom_taxonomy_artifact`
  - `materialize_custom_projection_artifact`
  - `apply_taxonomy_update_state`
  - `apply_projection_update_state`
  - `remove_taxonomy_from_release`
  - `remove_projection_from_release`
  - `validate_projection_binding`
  - `compile_semantic_release_candidate`
  - `merge_semantic_release_candidates`
- Creation precursor payloads are accepted only by `materialize_*`; executable mutation payloads only by `apply_*_update_state`.
- Family-confused payloads fail closed; Normalizer owner outputs return detached refs, diagnostics and fingerprints only and do not mutate Corpus Builder database state.
- `compile_semantic_release_candidate` returns the complete custom release identity in nested `release_ref`. Top-level `semantic_release_id` and `semantic_release_version` are compatibility aliases; Kernel merge finalization must treat `release_ref` as the canonical proof so taxonomy/projection refs survive materialization.
