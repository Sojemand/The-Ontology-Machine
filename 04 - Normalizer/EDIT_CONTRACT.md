# Normalizer Edit Contract

- Entry-Point: `python -m normalizer_vision.edit_contract --request <request.json> --response <response.json>`
- Produkt-Contract und `module-manifest.json` bleiben unveraendert; `read_bundle` ist nur eine additive Owner-Action fuer `06 - Edit Suite`
- Sichtbare Actions:
  - `describe_surfaces`
  - `read_bundle`
  - `read_surface`
  - `validate_surface`
  - `write_surface`
  - additive Source-Authoring-Tools:
    `create_release_package`, `read_release_package`, `list_master_terms`,
    `read_master_term`, `upsert_master_term`, `retire_master_term`,
    `list_projections`, `read_projection`, `create_projection_draft`, `upsert_projection`,
    `set_locale_text`, `set_routing_lexicon`, `preview_impact`,
    `list_default_blueprints`, `derive_working_release_from_blueprint`,
    `review_bootstrap_release`, `bootstrap_release_package`,
    `review_data_informed_release`, `refine_release_package`,
    `create_minimal_custom_release`,
    `validate_release_package`, `compile_release_package`,
    `export_semantic_release`, `activate_semantic_release`,
    `create_and_activate_new_corpus_db`,
    Kernel detached-release actions:
    `materialize_custom_taxonomy_artifact`, `materialize_custom_projection_artifact`,
    `validate_projection_binding`, `compile_semantic_release_candidate`,
    `materialize_semantic_release_candidate`, `merge_semantic_release_candidates`
- Sichtbare Surfaces:
  - `normalizer.settings`
  - `normalizer.prompt_overrides`
  - `normalizer.prompt_bundle`
  - `normalizer.taxonomy_master`
  - `normalizer.taxonomy_profiles`
  - `normalizer.translation_glossary`
  - `normalizer.semantic_release_authoring`
  - `normalizer.debug_capabilities`
- `read_bundle` liefert dieselben Descriptoren wie `describe_surfaces` plus inline `value` oder per-surface `load_error`
- `normalizer.settings` bleibt Owner der lokalen Routing-Invarianten `projection_hint_mode` und `projection_routing.*`
- `normalizer.taxonomy_master`, `normalizer.taxonomy_profiles`, `normalizer.translation_glossary` und `normalizer.semantic_release_authoring` arbeiten jetzt direkt auf dem aktiven Source-Paket unter `config/taxonomy_sources/<release_id>/`
- `normalizer.taxonomy_master` mappt auf `master.core.yaml` plus `master.text.en.yaml`
- `normalizer.taxonomy_profiles` mappt auf `projections/<projection_id>.core.yaml` plus `.text.en.yaml`; `routing.surface_signals` bleibt das kompilierte Zielbild
- `set_locale_text` und `set_routing_lexicon` arbeiten nur auf der kanonischen Control-Locale `en`; andere Taxonomy-/Runtime-Locales werden fail-closed abgewiesen.
- `create_projection_draft` erstellt aus einer Template-Projection in einem Schritt einen gespeicherten Draft fuer Projection-Core, Routing-Text und Routing-Lexikon; spaetere Compile-/Export-Schritte bleiben getrennt
- die Laufzeitbegruendung `projection.selection.reason` bleibt der sichtbare Downstream-Routing-Hinweis und wird nicht durch source-lokale Sonderfelder ersetzt
- `normalizer.translation_glossary` mappt auf die optionale `translation_glossary.en.yaml`; die Surface ist `authoring_only` fuer englische Control-Terminologie und erzeugt keinen Runtime-Contract
- `normalizer.semantic_release_authoring` mappt auf `release.yaml`; Writes synchronisieren additiv `semantic_release.recipe.json`, und `activate_semantic_release` validiert plus kompiliert vor dem `.json`-Export und delegiert dann additiv an `05 - Corpus Builder`
- `review_bootstrap_release` und `review_data_informed_release` bleiben read-only Review-Actions fuer das gespeicherte Source-Paket; sie liefern dasselbe strukturierte Draft-Planungsmodell wie die Apply-Pfade, schreiben aber weder Source- noch Export-Artefakte
- `bootstrap_release_package` und `refine_release_package` sind die mutierenden Gegenstuecke; sie schreiben strikt source-first nur unter `config/taxonomy_sources/<release_id>/` und liefern neben dem Standard-Envelope auch `review_payload`, `applied_changes`, `changed_source_files` sowie den Release-Fingerprint-Delta
- Semantic-Release-Bundle und Corpus bleiben unveraendert, bis `validate_release_package`, `compile_release_package` oder spaetere Export-/Activate-Schritte ausgefuehrt werden
- `compile_release_package(target_locale?: str)` und `export_semantic_release(target_locale?: str)` akzeptieren nur `en` als optionalen expliziten Override; die Release-Authoring-Surface zeigt keinen Locale-Umschalter mehr. `en` ist die interne Control-Sprache fuer Labels, Guidance und Runtime Assets, nicht die Sprache jedes Quelldokuments; `activate_semantic_release` bleibt ohne zusaetzlichen Locale-Input artefaktbasiert
- `list_default_blueprints` und `derive_working_release_from_blueprint` sind die Blueprint-Golden-Path-Actions fuer ein neues Working Source Package
- `create_minimal_custom_release` ist der explizite Spezialarchiv-Pfad, der das aktive Working Source Package durch ein kleines Custom Package ersetzt
- `materialize_semantic_release_candidate` ist der Kernel-Pfad fuer detached Custom Releases; er schreibt ein vollstaendiges Release-Bundle aus Base-Release, Custom-Refs und Projection-Update-State, ohne das aktive Source Package zu ersetzen. Das geschriebene `release.json` muss top-level `release_fingerprint` als Alias von `fingerprint` enthalten.
- `merge_semantic_release_candidates` akzeptiert `projection_merge_mode`; `preserve_source_projections` behaelt Source-Projections nebeneinander, `merge_to_single_projection` kompiliert die Source-Projection-Refs deterministisch zu einer Ziel-Projection.
- `create_and_activate_new_corpus_db` delegiert nach Validate/Compile/Export an `05 - Corpus Builder` und faellt ohne dessen Runtime geschlossen fehl
- Schema-Modus: API-Key Provider verwenden strict `json_schema`, wenn moeglich, und fallen transportbedingt auf `json_object` zurueck; OpenAI OAuth nutzt `json_object`, waehrend der lokale Parser die erforderlichen Top-Level-Sektionen hart prueft
- Descriptoren fuer diese vier Surfaces liefern source-layer Slot-Metadaten wie `machine_stable` vs. `control_text`, `compile_relevant`, `allowed_values` oder `reference_types` sowie Validator-/Downstream-Hinweise
- Taxonomie-, Prompt- und Semantic-Release-Writes bleiben owner-lokal unter `config/`; Runtime-Felder wie `model`, `max_output_tokens` und Auth bleiben read-only bzw. request-owned
- Solange die Phase-0-Cross-Module-Ratchets fuer `04 -> 01` oder `04 -> 05` rot sind, gelten spaetere Robustheits-, Verifizierungs- oder Ratchet-Claims nicht als freigegeben
