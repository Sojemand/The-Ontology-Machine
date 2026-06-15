# Edit Suite

Eigenstaendige Windows-Desktop-App der Vision Pipeline fuer Readiness-, Drift- und spaetere Config-Surfaces.

## Rolle

- Federation-Modul unter `06 - Edit Suite`
- user-facing Desktop-App
- generische Edit-Shell, kein Run-/Debug-Host
- startet bewusst auch ohne migrierte `edit_contract`-faehige Module
- Governance-Archetyp: `frontend_module` / owner-lokale Desktop-Control-Surface

## Runtime Build

- Zielplattform: Windows x64
- gebuendelte Runtime: CPython 3.11 x64
- Offline-Quelle fuer Runtime-Pakete: `runtime/wheelhouse`
- Runtime-Vertrag: `runtime/runtime-manifest.json`
- Runtime-Preflight: `run.bat` prueft vor dem GUI-Start die gebuendelte Runtime-Provenance.
- Owner-Contract-Timeout: Standard `1800` Sekunden, ueberschreibbar mit `EDIT_SUITE_OWNER_CONTRACT_TIMEOUT_SECONDS`.

```bat
build-runtime.bat
check-runtime.bat
```

## Per-User Installation

- Installationsziel: `%LOCALAPPDATA%\Programs\Vision Pipeline\06 - Edit Suite`
- keine Adminrechte erforderlich
- kein Host-Python fuer den Betrieb erforderlich
- `state/` bleibt mutable und upgrade-stabil

```bat
build-installer.bat
build-installer.bat --compile
```

## Verhalten in Welle 1

- Live-Discovery unmittelbarer Sibling-Module `00` bis `07`; `06 - Edit Suite` und `Client Frontend` werden bewusst ausgeschlossen
- cached-first Start aus `state/registry_cache.json` plus suite-lokalem Bundle-Cache unter `state/bundles/*.json`
- Live-Discovery und owner-lokales Surface-Refresh laufen asynchron im Hintergrund; die Shell bleibt beim ersten Klick renderbar
- `read_bundle` wird owner-lokal bevorzugt und faellt fuer Legacy-Module automatisch auf `describe_surfaces` plus `read_surface` zurueck
- echte `read_bundle`-Contract-Fehler bleiben sichtbar und werden nicht als Legacy-Fallback versteckt
- sichtbare Readiness-/Drift-Zustaende plus lazy geladene owner-provided Edit-Surfaces fuer `ready`-Module
- Optimizer wird in der neuen Owner-Form wie der Interpreter abgebildet: vollstaendige gruppierte `optimizer.settings`-Form, editierbarer `optimizer.ocr_prompt`, read-only `optimizer.output_contract_preview`, read-only `optimizer.debug_capabilities`
- Contract-/Bundle-Fehler werden sichtbar im GUI gerendert statt als leerer Tab-Zustand verborgen
- keine Fremdmodul-Writes
- suite-lokale Persistenz nur unter `state/`
- Scrollen ist auf das gehoverte Scroll-Fenster begrenzt; verschachtelte Tabs scrollen nicht mehr gleichzeitig mit
- Owner-Aktionen laufen als UI-Background-Jobs mit Token-basiertem Stale-Result-Schutz; die harte Laufzeitgrenze bleibt der Owner-Contract-Timeout.
- Lange UI-Scans, insbesondere Semantic-Release-Artifact-Scans, laufen bounded/asynchron und melden Scan-Grenzen sichtbar statt die Shell zu blockieren.

## Entwicklung

```bat
dev-tests\bootstrap.bat
dev-tests\run-tests.bat
```

Alternativ:

```bat
..\run-dev-tests.bat --module "06 - Edit Suite"
```

## Mutable Truths

- `state/ui_state.json`: runtime truth fuer Fensterzustand, Auswahl und operationale Formular-Kontexte.
- `state/registry_cache.json`: runtime truth fuer cached-first Discovery; bei korruptem JSON wird live neu aufgebaut.
- `state/bundles/*.json`: runtime truth fuer cached owner bundles; bei korruptem JSON wird live neu geladen.
- `state/corpus-db-confirmations/` und `state/merge-confirmations/`: owner-action Confirmation-Artefakte, suite-lokal und pfadvalidiert.
- `state/edit-contract-*`: temporaere Contract-I/O-Verzeichnisse; alte Reste werden best-effort bereinigt.

## Golden-Path Evidence

- Contract-Surface: `dev-tests/tests/test_contract.py`
- Runtime/Installer: `dev-tests/tests/test_packaging.py`
- Live Registry: `dev-tests/tests/test_registry.py`
- Owner-Bundles: `dev-tests/tests/test_as_built_blueprint.py`, `test_orchestrator_contract.py`, `test_interpreter_vision_contract.py`, `test_validator_contract.py`, `test_normalizer_contract.py`, `test_corpus_builder_contract.py`, `test_mcp_server_contract.py`
- UI Action/State Safety: `test_operation_runner.py`, `test_repository.py`, `test_surfaces_read_bundle.py`

## Abweichungslog

| Regel | Abweichung | Grund | Follow-up | Risiko wenn offen |
| --- | --- | --- | --- | --- |

Aktuell keine offenen Edit-Suite-Abweichungen gegen den Blueprint.
