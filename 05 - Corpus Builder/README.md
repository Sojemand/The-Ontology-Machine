# 05 - Corpus Builder

`05 - Corpus Builder` ist ein `corpus_module` fuer normalized-first Loads in
eine einzelne `corpus.db` mit FTS, optionalen Embeddings und genau einem
aktiven Semantic Release pro Datenbank.

## Zweck

- laedt explizite `*.structured.normalized.json` Bundles in `corpus.db`
- behandelt `normalized.json` als kanonischen semantischen Input
- akzeptiert optional `structured.json` plus Validator-Report als Evidence-Paar
- persistiert Projektion, Materialisierung und Suchdaten in derselben DB
- kann Seitenbilder additiv und blob-separiert in `corpus.db` einbetten

## Oeffentliche Entry-Points

- Headless CLI: `runtime\python\python.exe -m corpus_builder`
- Contract: `corpus_builder.orchestrator_contract`
- Actions: siehe [module-manifest.json](/c:/Users/Norma/Workspace/Enterprise%20Stack/98%20-%20Vision%20Pipeline/05%20-%20Corpus%20Builder/module-manifest.json)
  fuer die kanonische Liste; dazu gehoeren auch `merge_preflight` und
  `merge_corpus_databases`.
- Services: `corpus_builder.services`

Die bestehenden Produkt-Actions bleiben stabil. Die Edit Suite nutzt additiv
die neuen JSON-faehigen Owner-Actions fuer Semantik, Suche, Export und
Artefakt-Rebuild. Semantic-Stage und -Aktivierung akzeptieren nur exportierte
`.json`-Release-Bundles.

`load_semantic_release` kann mit `write_global_mirrors=false` als
target-scoped Kernel-Attach-Pruefung laufen. In diesem Modus wird das
uebergebene Release-Bundle gelesen, validiert und gegen die angegebene
`corpus.db` ausgewertet, ohne `config/semantic_release.default.json`,
`state/semantic_release.active.json` oder `state/semantic_release_report.json`
zu veraendern. Der normale Produkt-Stage-Pfad bleibt der Default und schreibt
weiterhin die owner-lokalen Mirrors. Wenn ein Bundle top-level
`release_fingerprint` enthaelt, muss der Wert dem kanonischen `fingerprint`
entsprechen; aeltere Bundles ohne diesen Alias bleiben gueltig.

`rebuild_from_artifacts` kann fuer Kernel-Rebuilds ebenfalls ein explizites
`release_path` erhalten. Dann validiert der Rebuild die Artefakte gegen dieses
Bundle und schreibt keine module-globalen Semantic-Release-Mirrors. Die
Antwort enthaelt Target-Proof fuer Corpus-DB, Artifact Root und
`release_fingerprint`.

`semantic_status` und `read_active_semantic_release` lesen target-scoped DBs
read-only und aendern dabei keinen Journal-Modus. Wenn eine stabile WAL-mode DB
ohne beschreibbare `-wal`/`-shm` Sidecars gelesen wird, faellt der Read-Pfad auf
einen immutable SQLite-Read zurueck. Mutierende Flows wie Reset, Load oder
Rebuild verwenden weiterhin die normale Schreibverbindung.

Eine initialisierte Merge-Ziel-DB ohne `active_release_fingerprint` gilt fuer
Status, Load und Activation-Preflight als noch nicht aktivierter Initialzustand,
auch wenn die Merge-Route bereits Dokumente eingefuegt hat. Snapshot-Drift
bleibt blockierend, sobald `installation_state` eine aktive Release-Fingerprint
behauptet, aber kein gueltiger `active_snapshot` gelesen werden kann.
Bei der ersten Aktivierung richtet Corpus Builder kopierte
`document_payloads.projection_json`-Header fuer bekannte Projection-IDs auf die
aktivierte Merge-Release aus (`master_taxonomy_id`,
`master_taxonomy_version`, `projection_fingerprint`, `release_fingerprint`).
Fachdaten und Materialisierungstabellen bleiben erhalten; nur die Runtime-Header
wechseln von der Source-Release zur neuen Ziel-Release.

## Corpus-Kontext-Contract

Der Corpus Builder besitzt eine owner-lokale Produkt-Surface fuer seinen
Default-DB-Kontext:

- `activate_corpus_context`
  - setzt `database.corpus_db` in `config/corpus_config.json`
  - akzeptiert nur eine existierende Datei
  - liest den Semantic-Status snapshot-first fuer dieselbe DB
- `create_empty_corpus_db`
  - erzeugt eine leere SQLite-Datei ohne aktiven Release
  - kann mit `activate_context=true` direkt den Corpus-Builder-Default setzen
  - schreibt keine Orchestrator-UI-State-Dateien
- `create_and_activate_new_corpus_db` / `create_and_rebuild_new_corpus_db`
  - verlangen im Confirmation-Artefakt einen expliziten `corpus_root`
  - leiten den Zielordner nicht aus Orchestrator-UI-State ab
  - aktualisieren erst nach erfolgreicher Owner-Mutation `database.corpus_db`
- `reset_active_corpus_db`
  - setzt nach bestaetigtem Confirmation-Artefakt eine initialisierte aktive
    `corpus.db` in einen leeren Content-Zustand zurueck
  - leert Dokument-, Materialisierungs-, Such-, Evidence-, Promotion-,
    Embedding- und FTS-Inhaltstabellen transaktional
  - bewahrt `installation_state`, `semantic_snapshots`, Schema, Views und die
    aktive Semantic-Release-Beziehung
  - fuehrt nach dem Commit eine SQLite-Compaction aus, damit die geleerten
    Content-Seiten nicht nur logisch frei sind
  - entfernt nach geschlossenem DB-Handle leere idle WAL-Sidecars
    (`*.db-wal`, `*.db-shm`) best-effort; ein nicht-leeres WAL wird nie
    geloescht
  - liefert `semantic_release_preserved`, `empty_state_proven`,
    `active_release_ref`, `post_reset_counts`, `cleared_table_counts`,
    `physical_compaction`, `physical_compaction_performed` und
    `wal_sidecar_cleanup`
  - schreibt keine Orchestrator-UI-State-Dateien und keine Release-Mirrors

Der gemeinsame Pipeline-Kontext entsteht erst, wenn der Orchestrator seine
eigene Action `activate_corpus_context` ebenfalls ausfuehrt. Der Corpus Builder
bleibt Owner fuer `database.corpus_db`; der Orchestrator bleibt Owner fuer
`selected_corpus_db_path`.

`reset_active_corpus_db` akzeptiert nur Confirmation-Artefakte mit
`artifact_version=reset_active_corpus_db_confirmation_v1`,
`requested_action=reset_active_corpus_db`, `confirmed=true` und exakt passendem
`corpus_db_path`. Eine fehlende oder nicht initialisierte DB und eine DB ohne
aktiven Snapshot blocken vor der Mutation.

## Loader-Vertrag

- Produktpfad: `adapter -> validation -> workflow -> preparation/document_record`
- `load_document` akzeptiert weiterhin nur
  `structured_path`, `validation_path`, `normalized_path`, `corpus_db_path`
  plus optionale Blob-/Page-Image-Persistenzparameter
- `load_from_file` behaelt den expliziten `validation_path`-Vertrag
- `file_path`, `asset_path`-Semantik und `source_file_path`-Semantik werden
  nicht umgedeutet; es wurden keine neuen Contract-Felder eingefuehrt

## Neuer DB-Bildvertrag

Seitenbilder koennen optional in `corpus.db` gespeichert werden, ohne normale
Dokument-, FTS-, Embedding- oder Listenabfragen auf Blob-Lesezugriffe zu
zwingen.

- Schalter: `source.persist_page_images_in_db`
- Standard: `true`
- Bilder landen nur in `document_page_images`
- `documents` bleibt blob-frei; `document_payloads.original_blob` ist eine
  kalte Originaldatei-Payload und bleibt per Default leer
- `CORPUS_SCHEMA_VERSION` ist `7`

Tabellenvertrag:

- `document_id TEXT NOT NULL`
- `page INTEGER NOT NULL`
- `content_type TEXT NOT NULL`
- `byte_size INTEGER NOT NULL`
- `image_sha256 TEXT`
- `image_blob BLOB NOT NULL`
- `PRIMARY KEY (document_id, page)`
- `FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE`

## Bildquellen und Prioritaet

Wenn `source.persist_page_images_in_db=true` gilt fuer die Bildsuche:

1. explizites `source.page_images_dir`
2. sibling `page_images/` neben dem Artefaktordner `normalized/`

Innerhalb eines Roots gilt diese Aufloesung:

1. exakter `file_path`, falls er bereits unter `page_images/` zeigt
2. `<file_name>.<hash8>` nach Orchestrator-Konvention, auch wenn der
   veroeffentlichte Bildordner einen Optimizer-Asset-Hash statt des
   dokumentierten `content_hash` traegt
3. sanitised Variante mit `_` statt Leerzeichen als Drift-Abfang

Fehlende oder partielle Bilder sind fail-soft: Der Dokument-Load bleibt
erfolgreich, die Bildzeilen bleiben leer oder partiell, und der Loader loggt
eine Warnung. SQL- oder FK-Fehler in der Bild-Repository-Stufe bleiben
fail-fast und rollen die Dokument-Transaktion zurueck.

Page-scoped Dokumente mit `source_page` persistieren nur das Seitenbild dieser
einen Quellseite. Vollstaendige Dokumentartefakte ohne `source_page` koennen
weiterhin alle erkannten Seitenbilder bis `page_count` persistieren. Damit
bleibt die Orchestrator-Konvention eines gemeinsamen `page_images/`-Ordners
gueltig, ohne dass page-wise Loads ein Kreuzprodukt aus Dokumentseiten und
Bildseiten in `document_page_images` erzeugen.

## Config

`config/corpus_config.json`:

```json
{
  "database": {
    "corpus_db": "./output/corpus.db"
  },
  "source": {
    "page_images_dir": "",
    "persist_page_images_in_db": true,
    "persist_original_artifact_in_db": false,
    "max_original_artifact_bytes": 52428800,
    "max_page_image_bytes": 10485760,
    "max_page_image_total_bytes": 104857600
  }
}
```

`page_images_dir` ist als Root-Hinweis fuer persistierbare Seitenbilder gedacht.
Bei artefaktbasierten Rebuilds kann der Loader alternativ den sibling
`page_images/`-Ordner neben `normalized/` verwenden.
Originaldateien werden nur dann als `document_payloads.original_blob`
gespeichert, wenn `persist_original_artifact_in_db=true` gesetzt ist und das
Dateigroessenlimit eingehalten wird.

## Suche und Viewer

- FTS-, semantische und hybride Suche lesen weiterhin keine Bild-Blobs
- der Frontend-Viewer kann `document_page_images` direkt verwenden
- Metadaten wie `MAX(page)` bleiben blob-frei
- Corpora ohne `document_page_images` bleiben per Filesystem-Fallback nutzbar

## Laufzeit

```bat
check-runtime.bat
runtime\python\python.exe -m corpus_builder load --input "<doc>.structured.normalized.json" --corpus-db ".\output\corpus.db"
runtime\python\python.exe -m corpus_builder rebuild --pipeline-root "<pipeline-root>" --corpus-db ".\output\corpus.db"
runtime\python\python.exe -m corpus_builder search --query "Schlussrechnung" --corpus-db ".\output\corpus.db"
runtime\python\python.exe -m corpus_builder export --format jsonl --output ".\output\corpus_export.jsonl" --corpus-db ".\output\corpus.db"
```

Weitere Betriebs-, Build-, Runtime- und Installer-Hinweise stehen in
`README.operations.md`.

## Edit Suite und Debug Host

Die lokale Modul-GUI ist entfernt. Die arbeitszentrierte UX fuer:

- `Semantik`
- `Suche`
- `Statistiken`
- `Export`
- `Artefakt-Rebuild`

liegt jetzt im generischen Slot der `06 - Edit Suite`. Der generische
Orchestrator Debug Host bleibt zustaendig fuer:

- Artefakt-Scan ueber `scan_debug_input`
- Single-Load in eine frische Session-DB ueber `debug_run` mit `mode=single`
- Batch-Rebuild in `outputs/corpus.db` ueber `debug_run` mit `mode=batch`
- Host-sichtbare Outputs `outputs/corpus.db`, `outputs/preview_report.json`
  und `outputs/load_report.json`
- Owner-local Edit-Contract: `corpus_builder.edit_contract`
- Additive Fast-Path-Action: `read_bundle` fuer die Edit Suite; Produkt-Contract und Manifest-Actions bleiben unveraendert
- Sichtbare Edit-Surfaces: `corpus_builder.settings`, `corpus_builder.embeddings_policy`, `corpus_builder.search_policy`
- `config/semantic_release.default.json` bleibt die publizierte Bundle-Datei fuer
  Stage/Activate, ist aber keine freie Edit-Surface mehr

## Teststatus

- modul-lokale `dev-tests`: gruen
- neue Regressionen decken Tabelle, Loader, Lifecycle und blob-freie Suche ab
- Frontend-Viewer-Tests bestaetigen den Downstream-Vertrag fuer
  `document_page_images`
- Direct `pytest` from the module root is bounded by the module-root
  `pytest.ini` to `dev-tests/tests` and excludes generated runtime, dist,
  state and pytest temp artefact trees. Semantic Release fixture tests add the
  Normalizer runtime site-packages path explicitly for local test execution.

## Phase 19 Owner Contracts

- `corpus_builder/database_analysis/` exposes the read-only owner action `read_database_analysis_evidence`.
- The action builds the evidence package for `kernel.analyze_database.input.v1` and returns summary, coverage, release-materialization refs, affected-document evidence and optional query-manifest payload without mutating Corpus state.
- It fails closed when the targeted database is missing or empty, when release-materialization refs are absent, or when database/release target identity drifts.

- `corpus_builder/pipeline_batches/` owns batch inspection, sample extraction, original restore, cleanup mutation/journaling and reingest handoff.
- Public owner actions:
  - `inspect_latest_pipeline_batch`
  - `extract_sample_files_for_reingest`
  - `restore_pipeline_batch_originals`
  - `cleanup_pipeline_batch_materialization`
  - `reingest_pipeline_batch`
- Cleanup accepts batch- or selection-scoped cleanup inputs, validates the destructive confirmation and target identity, deletes only the scoped Corpus DB records plus derived artifact files, preserves originals/logs/Input/Semantic Release files, and writes a cleanup journal with post-mutation counts.

- `corpus_builder/semantic_release/` now also exposes the canonical multi-source merge owner actions:
  - `multi_source_merge_preflight`
  - `multi_source_merge_databases`
  - `write_merge_reconciliation_manifest`
  - `backfill_sql_from_merge_artifacts`
- The older pairwise `merge_preflight` and `merge_corpus_databases` remain legacy helpers only; Phase 19 Kernel happy paths are expected to use the `multi_source_merge_*` owner names.
- Filled multi-source merge derives ID maps from actual source SQLite rows, copies source document artifacts plus mergeable source-tree file artifacts into the target Artifact Tree, writes the combined target database, and lets `backfill_sql_from_merge_artifacts` verify/update the target SQL rows from the merge ID map. Copy scope is additive and collision-safe: DB-backed document artifacts keep their mapped target paths, additional source `Documents/` and `Error Cases/` files are copied as tree artifacts, source merge-run logs are imported under `Documents/logs/imported/<source_database_id>/`, and live-control roots (`Corpus`, `Semantic Release`, active `Input`) are not copied over the newly built target truths.
- `backfill_sql_from_merge_artifacts` returns both `database_path_hash` and
  `target_database_path_hash` as target proof for the same target DB path. The
  former is the generic Corpus mutation proof expected by Kernel adapters; the
  latter remains merge-manifest terminology. Both live in `target_identity` /
  owner proof, not as an extra top-level request field.
- `write_merge_reconciliation_manifest` is a closed owner action: it accepts selected resolutions, collision manifest/ref, target paths, target identity and optional confirmation receipt refs. Kernel-owned `kernel.database_merge_reconciliation_receipt.v1` envelopes are audit evidence and are not accepted as owner payload fields.
