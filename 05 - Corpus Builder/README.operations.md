# README.operations

Ergaenzende Betriebs- und Build-Hinweise fuer `05 - Corpus Builder`.

## Runtime und Build

Lokaler Modulstart:

```bat
check-runtime.bat
runtime\python\python.exe -m corpus_builder --help
```

Portable Runtime bauen oder validieren:

```bat
build-runtime.bat
build-runtime.bat --validate-only
..\tools\build-runtimes.bat --module "05 - Corpus Builder"
..\tools\build-runtimes.bat --module "05 - Corpus Builder" --validate-only
```

Erwartete Runtime-Pfade:

- `runtime/python`
- `runtime/runtime-manifest.json`
- mutable Produktdaten in `state/` und `output/`

## Development

Die Produktquelle liegt nur unter dem Modul selbst. Nicht als Primaerquelle
verwenden:

- `dist/`
- `runtime/`
- `.venv/`
- `venv/`
- `__pycache__/`
- `.pytest_cache/`
- `.pytest-tmp/`
- `.tmp/`

Tests lokal mit CPython `3.11.x`:

```bat
dev-tests\bootstrap.bat
dev-tests\run-tests.bat
```

Die Suite nutzt pro Lauf ein eigenes kurzes Basetemp unter `%TEMP%\om-cb-pytest-*`.
`PYTEST_BASETEMP` kann diesen Pfad fuer gezielte lokale Diagnose ueberschreiben.

## Semantic Release

- `load-release` staged nur einen exportierten `.json`-Release-Bundle
- `apply-release` aktiviert den bereits publizierten Bundle-Stand fuer genau
  diese `corpus.db`
- Kernel-gestuetzte Attach-/Activation-Aufrufe koennen
  `write_global_mirrors=false` setzen. Dann prueft der Corpus Builder den
  uebergebenen Release und schreibt nur die zielbezogene DB-Aktivierung; die
  owner-lokalen Published/Active/Report-Mirrors bleiben unveraendert.
- `semantic_status` und `read_active_semantic_release` zeigen zusaetzlich, ob
  aktive Release-Datei und `installation_state` der Datenbank zusammenpassen
- bei Fingerprint-Aenderungen werden aktive Dokumente als `stale` markiert
- danach sollte `backfill-stale` oder ein kompletter Rebuild folgen

Harte Schutzregeln:

- kein Stage- oder Apply-Pfad fuer Verzeichnisse, YAML-Dateien oder andere
  Nicht-`.json`-Release-Quellen
- kein Stage- oder Apply-Pfad fuer Release-Bundles mit Fingerprint-Drift gegen
  ihren Inhalt
- kein `apply-release` fuer aktive Dokumente ohne `projection_id`
- kein `apply-release` bei fehlenden Projectionen im neuen Release
- kein `apply-release` ueber unterschiedliche Master-Taxonomy-Linien
- normalized-first Loads werden ohne kompatiblen aktiven Release blockiert

## Rebuild aus Artefakten

Bevorzugter Rebuild-Pfad:

- Artefaktordner mit `normalized/`, `structured/`, `validation/`
- optional sibling `page_images/` fuer DB-Bildpersistenz
- rekursiver Scan ueber Pipeline-Cluster wie `vision/...`

Wichtige Regeln:

- `normalized` ist die primaere Rebuild-Basis
- `structured` und `validation` werden nur als vollstaendiges Evidence-Paar
  mitgenommen
- `runtime\python\python.exe -m corpus_builder rebuild` bleibt der direkte CLI-Rebuild-Pfad
- der Orchestrator Debug Host nutzt fuer dasselbe Artefaktmodell
  `scan_debug_input` und `debug_run`
- `debug_run` mit `mode=single` laedt genau ein
  `*.structured.normalized.json` in eine frische Session-DB
- `debug_run` mit `mode=batch` baut `outputs/corpus.db` aus einem
  Artefaktordner neu auf

## Edit Suite Surface

Die lokale GUI ist entfernt. Modulnahe Arbeitsflaechen fuer:

- `Semantik`
- `Suche`
- `Statistiken`
- `Export`
- `Artefakt-Rebuild`

werden ueber den Corpus-Builder-Slot in `06 - Edit Suite` bereitgestellt.
Der Orchestrator Debug Host bleibt fuer `scan_debug_input` und `debug_run`
zustaendig. Die Edit Suite exponiert dabei nur noch die Surfaces
`corpus_builder.settings`, `corpus_builder.embeddings_policy` und
`corpus_builder.search_policy`; Semantic-Stage und -Aktivierung laufen als
Actions ueber `Settings`.

## Installer

```bat
build-installer.bat
build-installer.bat --compile
```

Der Installer bleibt auf user-writable Pfade unter
`%LOCALAPPDATA%\Programs\Corpus Builder Vision` ausgelegt.
