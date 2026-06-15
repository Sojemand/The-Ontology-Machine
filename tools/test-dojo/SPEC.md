# Vision Pipeline Test Dojo SPEC

**Status:** Draft skeleton
**Stand:** 2026-04-25
**Scope:** `The Ontology Machine/tools/test-dojo`
**Zweck:** Belastbarer Bauplan fuer ein produktionsnahes Test Dojo, das die
Vision Pipeline, ihre Desktop-Oberflaechen, Browser-Oberflaechen, Contracts,
MCP-Control-Plane und Artefakt-/State-Vertraege automatisiert prueft.

## 1. Zielbild

Das Test Dojo ist eine Root-nahe QA-Control-Plane fuer die gesamte Vision
Pipeline. Es ersetzt nicht die bestehenden `dev-tests` der einzelnen Module,
sondern legt eine hoehere, produktionsnaehere Testschicht darueber.

Das Dojo muss spaeter nachweisen koennen:

- dass die headless Hauptlinie von `00 - Orchestrator` bis
  `05 - Corpus Builder` end-to-end laeuft
- dass `00 - Orchestrator` und `06 - Edit Suite` als produktive
  Desktop-Surfaces mit allen Buttons, Tabs, Dialogen und Workflows getestet
  oder explizit klassifiziert sind
- dass `Client Frontend` als Browser-/HTTP-Surface ueber Playwright und API
  Tests abgedeckt ist
- dass `07 - MCP Server` seinen Tool-Katalog, Permission-Policy und delegierte
  Owner-Contracts korrekt exponiert
- dass State-, Credential-, Corpus-, Artefakt- und Runtime-Grenzen eingehalten
  werden
- dass ein spaeterer Engineer aus Reports, Traces und Diffs erkennen kann,
  welche Produktfunktion versagt hat und welche Datei-/State-Aenderung dafuer
  verantwortlich war

Das Dojo darf niemals auf unkontrollierte Weise echte User-Daten,
Produktions-Credentials oder produktive Corpora veraendern. Es startet echte
Produktions-Entry-Points, aber immer in einem isolierten, messbaren
Dojo-Kontext.

## 2. Nicht-Ziele

Das Dojo ist nicht:

- ein Ersatz fuer modulnahe Unit- und Contract-Tests
- eine neue Business-Logic-Schicht
- ein zweiter Orchestrator
- eine Produkt-UI
- eine dauerhafte State-Quelle
- ein Ort fuer Test-spezifische Produktlogik in den Modulen

Produktmodule duerfen kleine Testbarkeits-Hooks anbieten, etwa eine
UI-Action-Inventarliste. Diese Hooks muessen aber read-only sein und duerfen
keinen alternativen Produktpfad implementieren.

## 3. Verzeichnisvertrag

Das Dojo lebt unter:

```text
tools/test-dojo/
```

Die Zielstruktur ist:

```text
tools/
  run-test-dojo.bat
  test-dojo/
    README.md
    SPEC.md
    dojo.config.json
    dojo/
      __main__.py
      cli.py
      manifest.py
      sandbox.py
      runtime.py
      reports.py
      inventory.py
      assertions.py
      artifacts.py
      drivers/
        python_contract.py
        desktop_ctk.py
        windows_ui.py
        browser_playwright.py
        mcp_stdio.py
        filesystem.py
        sqlite_probe.py
    suites/
      orchestrator_ui.json
      edit_suite_ui.json
      client_frontend_ui.json
      pipeline_e2e.json
      mcp_server.json
      governance_inventory.json
    cases/
    fixtures/
    out/
```

`out/` und alle Run-Artefakte sind mutable. Report-Artefakte fuer normale
Laeufe liegen nicht im Produktroot der Module, sondern unter:

```text
.tmp/test-dojo/runs/<run_id>/
.tmp/test-dojo/reports/<run_id>/
```

## 4. CLI-Vertrag

Der stabile Root-Einstieg ist:

```bat
tools\run-test-dojo.bat <command> [options]
```

Der Batch-Launcher muss eine gebuendelte Python-Runtime aus dem Pipeline-Root
verwenden. Er darf keinen produktiven Fallback auf System-Python erzwingen.

Pflichtkommandos:

```text
list
inspect --suite <name|all>
run --suite <name|all> [--mode deterministic|live-canary] [--run-id <id>]
```

Zielverhalten:

- `list` zeigt alle Suite-Manifeste und deren Status.
- `inspect` validiert Manifest-Shape, Cases, Driver, Inventory-Gates und
  geplante Schreiborte.
- `run` erzeugt einen isolierten Sandbox-Run, fuehrt Cases aus, schreibt
  maschinenlesbare und HTML-faehige Reports und gibt einen stabilen Exit-Code
  zurueck.

Exit-Code-Vertrag:

```text
0  erfolgreich
1  Testfehler oder Gate-Verletzung
2  Konfigurations-/Manifestfehler
3  Laufzeit-/Treiber nicht verfuegbar
4  Sicherheitsverletzung, z. B. unerlaubter Schreibpfad
5  interner Dojo-Fehler
```

## 5. Suite-Manifeste

Jede Suite wird als JSON-Datei unter `suites/` beschrieben.

Mindestfelder:

```json
{
  "name": "orchestrator-ui",
  "display_name": "00 - Orchestrator UI",
  "module": "00 - Orchestrator",
  "kind": "desktop_ui",
  "driver": "desktop_ctk",
  "inventory_gate": true,
  "modes": ["deterministic"],
  "sandbox": {
    "state_root": "state/orchestrator",
    "artifact_root": "output/orchestrator-artifacts"
  },
  "cases": [
    {
      "id": "status_run_control",
      "title": "Status tab run controls",
      "type": "button_action",
      "risk": "high",
      "expected_actions": ["start_processing", "abort_processing"]
    }
  ]
}
```

Suite-Manifeste sind der erste Contract fuer spaetere Tests. Neue produktive
Surfaces oder Buttons duerfen nicht nur im Code entstehen. Sie muessen in
Inventory oder Case-Mapping sichtbar werden.

## 6. Inventory-Gate

Das Inventory-Gate ist der zentrale Schutz gegen ungetestete Produktbuttons.

Das Dojo muss fuer jede produktive Surface inventarisieren:

- sichtbarer Button-/Control-Text
- stabiler Action-Key
- gebundene Produktmethode oder Contract-Link
- Surface, Tab, Dialog oder Kontext
- Schreiborte
- erwartete Vorbedingungen
- erwarteter Erfolgs- und Fehlerzustand
- Coverage-Status

Erlaubte Coverage-Status:

```text
tested_click
tested_action
covered_by_contract
covered_by_workflow
manual_only_with_reason
deferred_with_issue
```

Ein produktiver Button ohne Coverage-Status ist ein Dojo-Fehler.

`manual_only_with_reason` ist nur erlaubt, wenn:

- die Aktion nicht sicher automatisierbar ist
- der Grund konkret ist
- ein manueller Abnahmeablauf dokumentiert ist
- ein Follow-up oder ein Testbarkeits-Hook benannt ist

`deferred_with_issue` ist nur temporar erlaubt und muss eine konkrete
Issue-/TODO-Referenz enthalten.

## 7. Testbarkeits-Hooks in Produktmodulen

Fuer Desktop-Surfaces ist reines Pixel-/Klick-Scraping zu fragil. Deshalb
sollen Orchestrator und Edit Suite spaeter read-only Hooks bereitstellen:

```python
def get_ui_action_inventory() -> list[dict]:
    ...
```

Der Hook darf nur deklarieren:

- action_key
- label
- owner_surface
- widget_attr
- command_name
- allowed_write_scopes
- expected_state_effect
- destructive
- confirmation_required

Er darf nicht:

- Produktverhalten umgehen
- Testdaten schreiben
- echte Commands ausfuehren
- Secrets offenlegen

Das Dojo kann zusaetzlich den Widget-Baum introspektieren und pruefen, dass
deklarierte Actions wirklich gerendert werden.

## 8. Treiber

### 8.1 `desktop_ctk`

In-Process-Treiber fuer `customtkinter`-Apps.

Pflichten:

- App mit Dojo-State starten
- Widget-Baum erfassen
- Tabs/Dialoge rendern
- Button-Commands kontrolliert ausloesen
- UI-State vor und nach der Aktion messen
- Screenshots optional erzeugen, sofern verfuegbar

Dieser Treiber ist primaer fuer semantische Button-Tests und schnelle
Workflow-Checks.

### 8.2 `windows_ui`

Out-of-process-Treiber ueber Windows UI Automation, zum Beispiel `pywinauto`.

Pflichten:

- echte `.bat`-Launcher starten
- Fenster finden
- sichtbare Controls anklicken
- Dialoge bestaetigen oder abbrechen
- Screenshots und UIA-Dumps schreiben

Dieser Treiber ist fuer Smoke- und Integrationslaeufe gedacht, nicht fuer jede
kleine Buttonvariation.

### 8.3 `browser_playwright`

Browser-Treiber fuer `Client Frontend`.

Pflichten:

- lokalen Frontend-Server starten
- Health/API pruefen
- DOM-Buttons inventarisieren
- Workflows per Playwright klicken
- Screenshots, Traces und Konsolenfehler sichern
- API-Responses mit UI-State korrelieren

### 8.4 `python_contract`

Contract-Treiber fuer headless Entry-Points.

Pflichten:

- `python -m <contract_module>` mit Request-/Response-Dateien aufrufen
- Exit-Code, Response-Shape und Artefakte pruefen
- stderr/stdout sichern
- Contract-Failures vom Dojo selbst unterscheiden

### 8.5 `mcp_stdio`

MCP-Treiber fuer `07 - MCP Server`.

Pflichten:

- Server ueber stdio starten
- Tool-Katalog lesen
- erlaubte Tools mit Dojo-Fixtures aufrufen
- Permission-Failures pruefen
- keine schreibenden Operationen ausserhalb der Sandbox zulassen

### 8.6 `filesystem`

Diff- und Safety-Treiber.

Pflichten:

- erlaubte Schreiborte pro Case erfassen
- Vorher/Nachher-Diff berechnen
- geloeschte, veraenderte und neue Dateien reporten
- Schreibzugriffe ausserhalb erlaubter Scopes als Gate-Verletzung melden

### 8.7 `sqlite_probe`

DB-Pruefer fuer `corpus.db` und Test-Corpora.

Pflichten:

- SQLite-Datei oeffnen
- erwartete Tabellen und Indizes pruefen
- Dokument-, Page-Image-, Embedding- und Semantic-Release-Zustand validieren
- Integritaetschecks ausfuehren

## 9. Sicherheitsmodell

Das Dojo muss zwischen Produktcode und Produktdaten trennen.

Erlaubt:

- echte Produktmodule importieren
- echte `.bat`-Launcher starten
- echte Contract-Entrypoints aufrufen
- echte UI klicken
- echte Provider optional im Live-Canary-Modus verwenden

Nicht erlaubt:

- echte User-Credentials in Reports schreiben
- Browser-Storage mit Tokens dumpen
- Produktions-Corpora veraendern
- Pfade ausserhalb der Sandbox schreiben, ausser ein Case deklariert den Scope
  explizit und der Scope ist unter dem Pipeline-Root oder einem Dojo-Temp-Root
- Live-Provider als Standardpfad fuer Regressionen verwenden

Jeder Case muss deklarieren:

```text
allowed_write_scopes
secret_handling
destructive
requires_confirmation
live_external
```

Default ist:

```text
destructive = false
live_external = false
secret_handling = none
allowed_write_scopes = sandbox only
```

## 10. Modi

### 10.1 `deterministic`

Standardmodus.

- keine echten externen Provider
- Replay-/Fixture-Antworten
- stabile Outputs
- fuer lokale Regression und CI geeignet

### 10.2 `live-canary`

Expliziter Modus fuer wenige echte Integrationsproben.

- darf echte Provider/OAuth/Netzwerkpfade nur nutzen, wenn Credentials bereits
  sicher eingerichtet sind
- muss Secrets redigieren
- darf nicht als Default in `all` laufen
- muss Kosten-/Rate-Limit-Risiken sichtbar machen

### 10.3 `inventory-only`

Nur Inventar und Coverage-Matrix, keine schreibenden Aktionen.

### 10.4 `smoke`

Kurzer App-Start, Render- und Basisworkflow-Test.

## 11. Orchestrator UI Abdeckung

Die Orchestrator-Suite muss mindestens abdecken:

- App-Start ueber Produkt-Surface
- Status-Tab renderbar
- Pfadfelder: Input, Artefakt-Folder, Corpus-Kontext, Semantic Release
- Run Control: `Verarbeite`, `Abbruch`, `Reset Error Bundle`,
  `Reset Pipeline Logs`, `Open Edit Suite`, `Help`
- Moduswahl `batch`/`single`
- Semantic-Release-Modus
- Credentials-Tab: API-Key-Speichern, Loeschen, OAuth Login/Logout als Fake
  oder Canary
- Model Settings: Provider-Preset, Modellwahl, Refresh Models als Fake oder
  Canary
- Debug Host: Modulwahl, Input/Source-Pfade, Checks, Run/Cancel, Replay,
  Import, Reset Debug Output
- Log-Tab: Render, Append, Reset/Rotation soweit produktiv vorhanden
- Error-Bundle-Reset mit Vorher/Nachher-Diff
- Pipeline-Logs-Reset ohne Artefakt-/Credential-Verlust

Fuer jeden Reset-Button muss ein Filesystem-Diff beweisen, dass nur erlaubte
Pfade veraendert wurden.

## 12. Edit Suite UI Abdeckung

Die Edit-Suite-Suite muss mindestens abdecken:

- App-Start ohne migrierte Module
- cached-first Registry-Start
- `Refresh Registry`
- Sidebar-Modulwahl und `Open`
- Surface-Tabs und lazy Loading
- Readiness-/Drift-Karten
- `Validate` pro editierbarer Surface
- `Save` pro editierbarer Surface
- Owner-Actions aus Surface-Links
- Merge-Interactions und Confirmations
- Corpus-DB-Dialoge
- Taxonomy-, Semantic-Release-, Prompt-Bundle-, Agent-Permission- und
  Support-Monitor-Editoren
- sichtbare Contract-Fehler
- korrupte Cache-Dateien und Recovery
- suite-lokale State-Schreibgrenzen

Besonders wichtig: Die Edit Suite darf keine Fremdmodul-Writes durch eigene
Heuristiken ausfuehren. Schreibende Operationen muessen ueber owner-lokale
Contracts laufen und im Dojo-Report belegbar sein.

## 13. Client Frontend Abdeckung

Die Frontend-Suite muss mindestens abdecken:

- Serverstart ueber produktiven Launcher
- Haupt- und Config-Surface
- Provider-/Model-Catalog-Status
- Credential-/OAuth-Status ohne Secret-Leak
- Corpus-Auswahl
- Chat-Minimal-Agent mit Test-Corpus
- Bild-Endpoint `GET /api/image/<docId>/<page>`
- Config-Editor und Persistenz
- Fehlerzustaende bei fehlendem Corpus
- Browser-Konsole ohne unerwartete Errors
- Screenshots fuer Desktop- und Mobile-Viewport

## 14. Pipeline E2E Abdeckung

Die Pipeline-Suite muss mindestens abdecken:

- ein erfolgreicher Dokumentlauf bis `corpus.db`
- Replay-basierter deterministischer Lauf
- Validator-Failure mit Error-Case-Bundle
- Interpreter-Review-Pfad
- Normalizer-Review-Pfad
- Reset-Roundtrip
- Semantic-Release-Aktivierung
- Page-Image-Persistenz
- Corpus Builder Artefakt-Rebuild
- Embeddings im Fake-/Replay-Modus

Live-Provider-Laeufe sind separate Canary-Cases und duerfen die deterministische
Regression nicht ersetzen.

## 15. MCP Server Abdeckung

Die MCP-Suite muss mindestens abdecken:

- stdio-Start
- Tool-Katalog
- Tool-Schema-Stabilitaet
- erlaubte read-only Tools
- schreibende Tools mit Sandbox-Fixures
- Permission-Denials
- Delegation an Owner-Contracts
- kein Netzwerk-Surface
- keine State-Schreibungen ausserhalb MCP-eigener und owner-deklarierter Scopes

## 16. Reports

Jeder Run muss schreiben:

```text
.tmp/test-dojo/reports/<run_id>/
  index.json
  index.html
  coverage_matrix.json
  inventory.json
  run.log
  state_diff.json
  artifact_diff.json
  failures/
  screenshots/
  traces/
```

Minimaler `index.json`:

```json
{
  "run_id": "20260425-120000",
  "mode": "deterministic",
  "status": "passed",
  "suites": [],
  "started_at": "...",
  "finished_at": "...",
  "report_schema_version": 1
}
```

Reports muessen maschinenlesbar bleiben. HTML ist eine Komfortschicht, nicht
die einzige Wahrheit.

## 17. Akzeptanzkriterien fuer das fertige Dojo

Das Dojo gilt als fertig, wenn:

- `tools\run-test-dojo.bat list` alle Suiten stabil listet
- `inspect --suite all` alle Manifeste validiert
- `run --suite governance-inventory` die Inventory-Gates auswertet
- Orchestrator- und Edit-Suite-Buttons vollstaendig inventarisiert sind
- jeder produktive Button einen gueltigen Coverage-Status hat
- mindestens ein echter Windows-UI-Smoke-Test pro Desktop-App existiert
- mindestens ein semantischer `desktop_ctk`-Workflow pro Haupttab existiert
- Pipeline-E2E deterministisch ohne externe Provider laeuft
- Client Frontend per Playwright Desktop und Mobile prueft
- MCP Server per stdio getestet wird
- alle Schreiboperationen durch Filesystem-Diffs kontrolliert werden
- Reports reproduzierbar und handover-tauglich sind
- Live-Canary-Cases separat markiert und nie Default sind

## 18. Ausbau-Reihenfolge

Empfohlene Reihenfolge:

1. Manifest-Validierung und Report-Schema finalisieren.
2. Filesystem-Sandbox und Diff-Gates bauen.
3. Contract-Treiber fuer Orchestrator/Edit Suite/Owner-Contracts bauen.
4. UI-Action-Inventar-Hooks in Orchestrator und Edit Suite ergaenzen.
5. `desktop_ctk` fuer semantische Button-Tests bauen.
6. Windows-UI-Smoke-Tests ergaenzen.
7. Pipeline-E2E-Replay-Cases integrieren.
8. Playwright-Suite fuer Client Frontend bauen.
9. MCP-stdio-Suite bauen.
10. Live-Canary-Modus mit Secret-Redaction absichern.

## 19. Governance-Regel

Ab dem Zeitpunkt, an dem das Dojo aktiv ist, gilt:

Neue produktive Buttons, neue Owner-Actions, neue MCP-Tools und neue
Frontend-Workflows muessen entweder:

- im Dojo getestet werden
- von einem bestehenden Workflow nachweislich abgedeckt sein
- oder mit konkretem Grund als `manual_only_with_reason` beziehungsweise
  `deferred_with_issue` klassifiziert werden

Unklassifizierte Produktoberflaeche ist ein Regressionsrisiko und muss als
Dojo-Fehler behandelt werden.
