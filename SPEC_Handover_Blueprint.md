# Vision Pipeline Handover Blueprint

**Erstellt:** 2026-03-25  
**Status:** Governance Blueprint
**Zweck:** Moduluebergreifender Leitfaden fuer Senior-Dev-Handover, Drift-Kontrolle und finalen Pipeline-Cleanup.

## Zweck und Pflegegrenze

- Diese SPEC ist ein dauerhafter Handover- und Governance-Blueprint, kein Umbau-Tagebuch.
- Sie beschreibt die stabile Foederationsform der Pipeline: Modulgrenzen, Contract-Denke, Runtime-Disziplin, Truth-Kategorien, Refactor-Regeln und Audit-Fragen.
- Laufende Reparaturen, konkrete Run-IDs, Phase-Labels, Tagesentscheidungen und Bughistorie gehoeren in Modul-READMEs, PR-Beschreibungen, Fortschrittsdateien oder Tickets.
- Eine Erkenntnis darf nur dann in diese SPEC, wenn sie als zeitlose Regel fuer mehrere Module oder fuer einen dauerhaften Modul-Archetyp gilt.
- Aenderungen an dieser Datei `MUST` vorhandene Abschnitte verstaerken oder ersetzen; neue datierte Update-Bloecke am Kopf sind unzulaessig.

## Kanonische Vertragsinvarianten

- Die aktive Dokument-Hauptlinie ist `00 - Orchestrator -> 01 - Optimizer -> 02 - Interpreter -> 03 - Validator -> 04 - Normalizer -> 05 - Corpus Builder`.
- `06 - Edit Suite`, `07 - MCP Server`, `08 - Semantic Control Kernel` und `Client Frontend` sind governance-pflichtige Owner-, Control- oder Frontend-Surfaces, aber keine weiteren Dokument-Transformationsstufen der Hauptlinie.
- Orchestratorgebundene Module sind headless. Ihre oeffentliche Surface ist der Contract-Entry-Point plus dokumentierte Runtime-Hilfen; lokale GUI-Surfaces und `run.bat` sind kein Pflichtumfang.
- Nach dem Optimizer wird die aktive Dokumentarbeit page-scoped behandelt: Page-Artefakte, Debug-Belege und Retries behalten ihre Page-Identitaet; Dokumentaggregation, Publikation und finale Disposition bleiben beim Orchestrator.
- Office-Mehrseiter verwenden die gerenderte PDF-Surface als kanonische page-wise Raw-Surface, wenn native Office-Extraktion keine belastbare Seitenwahrheit liefert.
- Semantic Releases werden vom `04 - Normalizer` als vollstaendige Release-Bundles materialisiert. Default-Mirror, Custom Releases, Promotion-Surface und Runtime Assets duerfen nicht zu parallelen editierbaren Wahrheiten auseinanderlaufen.
- `05 - Corpus Builder` bindet page-scoped Materialisierung strikt an die jeweilige `source_page` und behandelt Semantic-Release-Aktivierung, Datenbankinhalt und Artefaktkopien als owner-lokale Persistenzgrenzen.
- `07 - MCP Server` bleibt eine lokale `stdio`-Control-Plane. Schreibende Arbeit laeuft ueber owner-lokale Contracts; MCP-eigene Permission- und Support-State-Dateien sind keine Business-Logic-Wahrheiten.
- `08 - Semantic Control Kernel` besitzt Workflow-Semantik, Dialog-/Mirror-/Progress-/Resume-/Recovery-/Receipt-State und owner-klare Adapter-Delegation. Er ist weder UI-Renderer noch MCP-Transport noch zweite Fachlogik-Welt.
- Kernel-LLM- und Langlaeufer-Transparenz ist Workflow-Governance: Fortschritt, Retrybarkeit, Blocker und terminale Ergebnisse muessen als Kernel-State erklaerbar sein, ohne owner-lokale Fachwahrheiten zu ueberschreiben.
- `Client Frontend` ist eine lokale Browser-/HTTP-Produktoberflaeche. Provider-I/O, Credentials, OAuth-State, Config, lokaler State und Pipeline-Operationen bleiben ueber dokumentierte Server-, MCP- oder Owner-Contract-Grenzen getrennt.
- Permanente Tool- und Surface-Inventare werden in den jeweiligen Modul-Manifests, READMEs, Preflights und Exports konsistent gehalten; diese Root-SPEC haelt keine kurzlebigen Toolzaehler oder entfernten Workflow-Familien fest.

## Zielbild

- Die Vision Pipeline ist ein Verband aus eigenstaendigen, self-contained Modulen mit gemeinsamem Foederationsvertrag.
- Alle durch den Orchestrator geladenen Pipeline-Module sind headless und werden nicht mehr als lokal startbare GUI- oder Desktop-Apps verstanden.
- User-facing Produktflaechen ausserhalb der headless Hauptlinie, insbesondere `Client Frontend`, bleiben ebenfalls governance-pflichtig, auch wenn ihre oeffentliche Surface nicht als Orchestrator-Action-Contract modelliert ist.
- Workflow-Governance- und Control-Plane-Module ausserhalb der Dokument-Hauptlinie, insbesondere `07 - MCP Server` und `08 - Semantic Control Kernel`, bleiben ebenfalls governance-pflichtig und duerfen keine lokale Sonderarchitektur ausserhalb des Foederationsvertrags aufbauen.
- Single-module Builds, Einzelmodulexperimente und lokale Refactorings sind erlaubt.
- Nicht erlaubt ist strukturelle Drift gegen das gemeinsame Zielbild der Pipeline:
  - gleiche Grundform
  - gleiche Contract-Denke
  - gleiche Runtime-Disziplin
  - gleiche Dev-Test-Disziplin
  - gleiche Handover-Erwartung
- Ein spaeter uebernehmender Senior Developer soll jedes Modul isoliert verstehen koennen, ohne das Gesamtbild aus Zufallswissen oder Reverse Engineering rekonstruieren zu muessen.
- Gleichzeitig soll er den gesamten Verband als zusammenhaengendes System lesen koennen, statt pro Modul ein anderes Architekturmodell zu lernen.

## Aktueller Architekturstand

- `00 - Orchestrator` bleibt die steuernde Host-Surface fuer Routing, Request Enrichment, Laufzeit-Credentials und Debug-Hosting der headless Schwester-Module.
- `01 - Optimizer` ist der vereinte Upstream-Slot fuer beide Produktprofile und erzeugt das kanonische Raw-/Asset-Evidence fuer die Hauptlinie.
- `02 - Interpreter` ist ebenfalls ein vereinter Slot und konsumiert den bereits angereicherten kanonischen Request statt modulinterner Raw-Adaption.
- `03 - Validator` und `04 - Normalizer` bleiben die formale bzw. semantische Mittelstrecke zwischen `structured` und `normalized`.
- `05 - Corpus Builder` ist der Integrationspunkt der Hauptlinie: normalized-first Load, Artefakt-Rebuild, Suche, Export, Embeddings und Semantic-Release-Aktivierung laufen hier zusammen.
- `06 - Edit Suite` ist eine user-facing Owner-Surface oberhalb dieser Hauptlinie; sie ist keine zusaetzliche Dokument-Transformationsstufe.
- `07 - MCP Server` ist die lokale MCP-Control-Plane fuer Agenten- und Tool-Zugriffe. Er ist keine Dokument-Transformationsstufe und kein zweiter Business-Logic-Host; er exponiert einen Tool-Katalog ueber lokales `stdio`-MCP und delegiert reale Arbeit an owner-lokale Contracts.
- `08 - Semantic Control Kernel` ist das headless Workflow-Governance-Modul des Verbands. Er ist keine Dokument-Transformationsstufe, kein zweiter MCP-Transport und kein zweiter Owner-Fachhost; er besitzt Workflow-Semantik, Statusuebergaenge, Dialog-/Mirror-/Progress-Vertraege, Resume-/Recovery-/Receipt-State und owner-klare Adapter-Delegation.
- `Client Frontend` ist die lokale Browser-/HTTP-Produktoberflaeche mit Provider-I/O, Config-Surface, Credential-/OAuth-Ownership, lokaler Persistenz und optionalem Minimal-Agent. Es gehoert zum Governance-Verband, bleibt aber als Frontend-Surface ausserhalb der headless Dokument-Hauptlinie.

## Normative Sprache

- `MUST` bedeutet: verbindliche Foederationsregel. Abweichungen muessen im `Abweichungslog` dokumentiert werden.
- `SHOULD` bedeutet: erwarteter Standard. Abweichungen sind moeglich, muessen aber technisch begruendet und fuer den Handover sichtbar gemacht werden.
- `MAY` bedeutet: optionaler Standard, sofern er dem Modul hilft und keine Drift gegen Foederationsregeln erzeugt.
- Diese SPEC ist absichtlich kein loses Best-Practice-Dokument. Sie ist ein persistenter Governance-Anker fuer den finalen Pipeline-Cleanup.

## Geltungsbereich und Freiheitsgrade

- Diese SPEC standardisiert keine fachliche Logik einzelner Module.
- Diese SPEC standardisiert die Uebernehmbarkeit, Vergleichbarkeit und Wartbarkeit des Modulverbands.
- Modul-lokale Implementierungsfreiheit bleibt erhalten bei:
  - Fachlogik
  - Prompt-Inhalt
  - Provider-spezifischen Details
  - UI-Details separater Frontend-Clients ausserhalb orchestratorgebundener Module, solange ihre Runtime-, State-, Credential- und Handover-Vertraege sichtbar bleiben
  - Modul-eigenen Hilfsdateien und Konfigurationen
- Foederationsweite Invarianten muessen trotzdem erhalten bleiben bei:
  - Modulstruktur
  - Contract-Semantik
  - Runtime-Layout
  - Dev-Test-Einbindung
  - Nachvollziehbarkeit von Datenfluss und Fehlern
  - sichtbarer Dokumentation von Risiken und Abweichungen

## Erfasste Schnittstellen- und Governance-Standards

- Diese SPEC fuehrt keine Code- oder API-Aenderung ein.
- Diese SPEC standardisiert die erwartete Bedeutung von:
  - `module-manifest.json`
  - Contract-Entry-Points
  - Action-Namensmustern
  - `runtime/`
  - `dev-tests/`
  - Root-Tooling fuer Runtime-Build und Dev-Test-Ausfuehrung
  - Handover-Evidenz fuer technische Reife
  - Frontend-Surfaces, Runtime-/Installer-Pfade, Config-/Credential-State und Browser-/Server-Entry-Points, sofern ein Modul eine user-facing Oberflaeche ist
  - MCP-/Control-Plane-Toolkataloge, sofern ein Modul Agenten- oder Automationszugriffe exponiert
  - Kernel-Workflow-Surfaces, Mirror-/Progress-/Receipt-/Resume-/Recovery-Vertraege, sofern ein Modul Workflow-Governance und owner-klare Delegation exponiert
- Diese SPEC standardisiert fuer orchestratorgebundene Module explizit kein lokales `run.bat` und keine modulinterne GUI mehr.
- Jedes Modul `MUST` fuer einen uebernehmenden Engineer erklaeren:
  - was die oeffentliche Eintrittsflaeche ist
  - woher Inputs kommen
  - welche Zwischentransformationen existieren
  - wie Outputs entstehen
  - wie Fehler analysiert werden
  - wo bewusste Risiken dokumentiert sind

## Warum Vibe-Coded Module schwer zu uebernehmen sind

- Vibe-coded Module wirken oft lokal produktiv, aber global instabil.
- Das Hauptproblem ist selten ein einzelner offensichtlicher Bug.
- Das Hauptproblem ist, dass Wissen ueber das Modul an vielen kleinen, unausgesprochenen Stellen steckt:
  - Prompt-Regeln
  - implizite JSON-Contracts
  - lokale Dateipfade
  - versteckte Runtime-Annahmen
  - Tests mit kuenstlichen Fixtures
  - historisch gewachsene Helper
  - halb-vereinheitlichte UI- und CLI-Muster
- Fuer einen Senior Developer ist das nicht primaer ein Coding-Problem, sondern ein Rekonstruktionsproblem.
- Je mehr Rekonstruktion noetig ist, desto teurer werden:
  - Refactorings
  - Regression-Debugging
  - Cross-Module-Vergleiche
  - Production-Haertung
  - Handover an Dritte

## Senior Dev Pain List and Remedies

### 1. Hidden Contracts

**Pain**

- Das Modul haelt mehr Vertrag ein, als formell dokumentiert ist.

**Warum das bei Handover weh tut**

- Der Uebernehmer muss die echten Regeln aus Code, Tests, Prompts und Fehlerbildern zusammensammeln.
- Dadurch wird jede Aenderung riskant, weil unklar ist, welcher implizite Vertrag bereits von Nachbarmodulen oder Daten erwartet wird.

**Woran man es im Code erkennt**

- Contract-Logik sitzt verteilt ueber CLI, GUI, Orchestrator-Adapter, Prompt-Builder und Tests.
- Feldnamen, Action-Namen, Dateinamen oder Statuswerte tauchen mehrfach in leicht anderer Form auf.
- Die README beschreibt nur den Idealpfad, nicht die operative Wirklichkeit.

**Remedy vor dem Handover**

- Explizites Request-/Response-Schema dokumentieren.
- Contract-Adapter von Fachlogik trennen.
- Contract-Invarianten in Tests, README und Manifest konsistent spiegeln.
- Pro Modul einen klaren Contract-Entry-Point halten.

**Minimaler Nachweis**

- `module-manifest.json` ist konsistent.
- README, Contract-Code und Tests beschreiben dieselben Action-Namen und Output-Erwartungen.

### 2. Schema Softness

**Pain**

- Das Modul behauptet Strukturhaerte, verarbeitet aber faktisch best-effort JSON oder flexible Payloads.

**Warum das bei Handover weh tut**

- Ein Senior Developer kann Fehler nicht an einer harten Grenze festmachen.
- Jede Downstream-Anomalie wird zu einer forensischen Suche durch mehrere Heuristiken.

**Woran man es im Code erkennt**

- JSON-Reparatur, Fallback-Parsing, stille Defaults, nachtraegliche Shape-Korrektur.
- "Structured" Output wird erst nach dem LLM-Call heuristisch passend gemacht.

**Remedy vor dem Handover**

- Entweder wirklich striktes Schema durchsetzen oder bewusst als best-effort deklarieren.
- Extensions-Zonen explizit machen.
- Heuristische Reparaturen sichtbar loggen oder debug-bar persistieren.

**Minimaler Nachweis**

- Dokumentierter Unterschied zwischen hartem Contract und optionalen Extensions.
- Tests fuer gueltige und ungueltige Contract-Pfade.

### 3. Debug-Unfriendly Pipelines

**Pain**

- Der Datenfluss hat mehrere Transformationsstufen, aber kaum sichtbare Zwischenartefakte.

**Warum das bei Handover weh tut**

- Falsche Werte koennen nicht schnell auf eine konkrete Stufe eingegrenzt werden.
- Der Uebernehmer sieht nur Input und finalen Fehler, nicht den Weg dazwischen.

**Woran man es im Code erkennt**

- Prompt-Building, Provider-I/O, Parsing, Enrichment und Persistence sind ineinandergezogen.
- Debugging erfordert Breakpoints oder Ad-hoc-Prints.

**Remedy vor dem Handover**

- Pipeline in klar benannte Stufen schneiden.
- Optionales Debug-Bundle vorsehen:
  - normalisierter Input
  - kompakter Prompt
  - rohe Provider-Antwort
  - reparierte Antwort
  - finale Persistenz
  - Validierungsstatistiken

**Minimaler Nachweis**

- Ein falscher Feldwert kann innerhalb weniger Minuten einer konkreten Stufe zugeordnet werden.

### 4. Runtime Packaging Opacity

**Pain**

- Das Modul laeuft nur mit einer speziellen lokalen Runtime- oder Packaging-Annahme.

**Warum das bei Handover weh tut**

- Uebernahme scheitert nicht am Code, sondern am Starten, Deployen oder Reproduzieren.

**Woran man es im Code erkennt**

- `run.bat`, `build-runtime.bat`, `runtime/`, portable Python, GUI-Bundles, Host-spezifische Abhaengigkeiten.
- Produktcode und Runtime-Wissen sind nicht sauber getrennt.

**Remedy vor dem Handover**

- Runtime-Policy explizit dokumentieren.
- Start-, Build- und Packaging-Pfade zentralisieren.
- Runtime-Layout testen.

**Minimaler Nachweis**

- Ein neuer Engineer kann das Modul ohne Rateversuche starten oder die Runtime policy lesen und sofort verstehen.

### 5. Test Realism Gaps

**Pain**

- Die Tests sind gruen, aber beweisen nur lokale Logik mit synthetischen Fixtures.

**Warum das bei Handover weh tut**

- Refactoring fuehlt sich sicher an, obwohl echte Dokumente oder echte Service-Antworten nicht abgesichert sind.

**Woran man es im Code erkennt**

- Hoher Anteil an Mocks, Monkeypatches und Testdoubles.
- Kaum Golden Files oder reale Dokument-Regressionsfaelle.

**Remedy vor dem Handover**

- Unit-Tests behalten, aber durch Regressions-Corpus ergaenzen.
- Mindestens einige echte oder realistische End-to-End-Faelle versioniert abbilden.
- Zwischen "Code korrekt" und "Produkt korrekt" unterscheiden.

**Minimaler Nachweis**

- Es gibt neben Unit-Tests eine kleine, kuratierte Regressionsebene mit echten Modul-Outputs.

### 6. Uncontrolled Concurrency and Cost

**Pain**

- Das Modul kann mehr Parallelitaet, API-Last oder Kosten erzeugen, als operativ kontrollierbar ist.

**Warum das bei Handover weh tut**

- Probleme treten erst unter Last, im Batch oder im echten Betrieb auf.

**Woran man es im Code erkennt**

- Worker-Fan-out ohne globale Steuerung.
- lokale Retries ohne globales Backpressure.
- keine Kosten-, Token- oder Groessenlimits.
- kein Cancel, Resume oder Fail-Fast fuer problematische Batches.

**Remedy vor dem Handover**

- Globale Grenzen fuer Parallelitaet, Input-Groesse, Seitenzahl und Kosten definieren.
- Rate-Limits und Fehlerpolitik dokumentieren.
- Batch-Verhalten nachvollziehbar und kontrollierbar machen.

**Minimaler Nachweis**

- Das Modul kann erklaeren, wie es unter Last reagiert und wo es sauber stoppt.

### 7. Config, Log and Output Sprawl

**Pain**

- Konfiguration, Logs, Secrets und Outputs liegen unsystematisch im Modulpfad oder wachsen lokal ohne Governance.

**Warum das bei Handover weh tut**

- Betrieb, Packaging und Debugging vermischen sich.
- Der Uebernehmer weiss nicht, welche Dateien Artefakte, Inputs, Secrets oder Build-Reste sind.

**Woran man es im Code erkennt**

- `.env`, Logs und Default-Output im Produktordner.
- mutable und immutable Artefakte liegen durcheinander.

**Remedy vor dem Handover**

- Mutable Pfade klar definieren.
- Secrets, Logs und Outputs konsistent platzieren.
- Standardpfade dokumentieren und nicht erraten lassen.

**Minimaler Nachweis**

- Ein neuer Engineer kann auf Anhieb sagen, wo Konfiguration, Logs, Outputs und Runtime-Artefakte hingehoeren.

### 8. Module Boundary Violations

**Pain**

- Module sind formal getrennt, nutzen aber implizit Wissen oder Abhaengigkeiten von Schwesterordnern.

**Warum das bei Handover weh tut**

- Lokale Aenderungen erzeugen Seiteneffekte in anderen Modulen.
- Der Verband verliert Vergleichbarkeit und Austauschbarkeit.

**Woran man es im Code erkennt**

- Imports aus Nachbarmodulen.
- gemeinsamer Code ohne klares Shared-Layer-Modell.
- Copy-and-paste mit spaeterer Drift.

**Remedy vor dem Handover**

- Keine Code-, Config- oder Runtime-Abhaengigkeiten auf Schwesterordner.
- Wiederverwendung nur durch bewusstes Kopieren mit lokaler Verantwortung oder spaeteren echten Shared-Layer.

**Minimaler Nachweis**

- Jedes Modul kann fuer sich gebaut, getestet und verstanden werden, ohne Schwesterordner zu importieren.

### 9. Drift Through Parallel Module Evolution

**Pain**

- Module entwickeln sich einzeln weiter und verlieren gemeinsame Form, Begriffe und Vergleichbarkeit.

**Warum das bei Handover weh tut**

- Ein Senior Developer kann kein Muster einmal lernen und dann uebertragen.
- Finales Debugging wird blindes, lokales Herumbauen statt systematisches Foederations-Tuning.

**Woran man es im Code erkennt**

- gleiche Konzepte mit unterschiedlichen Dateinamen, Action-Namen, Logging-Mustern, Runtime-Regeln oder Teststrukturen.

**Remedy vor dem Handover**

- Gemeinsames Modulraster definieren.
- Abweichungen sichtbar dokumentieren.
- Neue lokale Optimierungen gegen das Gesamtmodell pruefen, nicht nur gegen die lokale Testlage.

**Minimaler Nachweis**

- Zwei beliebige Module lassen sich entlang desselben Review-Rasters vergleichen.

## Worked Example: 02 - Interpreter

- `02 - Interpreter` ist ein gutes erstes Beispiel, weil das Modul bereits viele sinnvolle Schutzmassnahmen hat, aber gleichzeitig typische Handover-Schmerzen eines produktnahen Vibe-Coding-Moduls zeigt.
- Dieses Beispiel ist nicht als Einzelkritik gedacht, sondern als Referenzmuster fuer die Behandlung aller weiteren Module.
- Architekturstand fuer den Handover: Das aktive Foederationsbild ist heute `Optimizer -> Request Enrichment -> Interpreter -> Validator -> Normalizer -> Corpus Builder`; der Interpreter konsumiert den kanonischen Request der Hauptlinie.
- Die folgenden Pain-Punkte sind deshalb als Worked Example eines historisch gewachsenen Review-Musters zu lesen, nicht als vollstaendige Beschreibung der aktuellen Gesamt-Topologie.

### A. Soft Output Contract

**Pain**

- Das Modul verspricht strukturierte Ausgaben, arbeitet aber faktisch mit weichem Schema und heuristischer Nachbearbeitung.

**Warum das bei Handover weh tut**

- Der Uebernehmer weiss nicht sofort, ob ein fehlerhafter Wert aus dem Modell, aus einer JSON-Reparatur oder aus nachgelagerter Anreicherung stammt.

**Woran man es im Code erkennt**

- `llm_interpreter/prompts.py` erlaubt flexible Felder in `context`, `fields` und `rows`.
- `llm_interpreter/providers/openai_provider.py` faellt bei nicht strikt kompatiblem Schema auf `json_object` zurueck.
- `llm_interpreter/interpreter.py` parst, repariert und fuellt Defaults nach.

**Remedy vor dem Handover**

- Harte und weiche Contractbereiche explizit trennen.
- Reparaturpfade debug-bar machen.
- Fuer Downstream relevante Invarianten dokumentieren und hart testen.

**Minimaler Nachweis**

- Ein Engineer kann fuer jedes persistierte Feld sagen, ob es schema-hart, schema-weich oder heuristisch abgeleitet ist.

### B. Trusted Local Paths and Full In-Memory Asset Loading

**Pain**

- Seitenbilder werden als vertrauenswuerdige lokale Dateipfade behandelt, komplett gelesen und als Base64 weitergereicht.

**Warum das bei Handover weh tut**

- Sicherheits-, Speicher- und Lastprobleme zeigen sich spaet und schwer reproduzierbar.

**Woran man es im Code erkennt**

- `llm_interpreter/prompts.py` liest `page_assets[].path` direkt.
- Es gibt Validierung fuer Bildsignaturen, aber keine Foederationsgrenzen fuer erlaubte Pfade, Dateigroessen oder Gesamtlast.

**Remedy vor dem Handover**

- erlaubte Input-Wurzeln
- Max-Pages
- Max-Bytes pro Asset
- Max-Bytes pro Request
- klares Fail-Fast-Verhalten

**Minimaler Nachweis**

- Das Modul hat dokumentierte Last- und Sicherheitsgrenzen fuer Input-Artefakte.

### C. Mostly Synthetic Test Confidence

**Pain**

- Die Dev-Suite ist stark, aber ueberwiegend fixture- und mock-basiert.

**Warum das bei Handover weh tut**

- Refactorings sind gegen lokale Logik gut abgesichert, gegen echte Dokumentwirklichkeit aber nur begrenzt.

**Woran man es im Code erkennt**

- `dev-tests/tests/conftest.py` nutzt kuenstliche Beispielseiten und `MockProvider`.
- Viele Tests sichern Fehlerrouten, Shapes und UI-Helfer, aber keine echten Produktionsdokumente.

**Remedy vor dem Handover**

- Kleine Golden-Regressionsebene aufbauen.
- Reale Dokumente oder anonymisierte Persistenzfaelle in kuratierter Form einfuehren.

**Minimaler Nachweis**

- Mindestens einige reale Interpreter-Regressionen laufen reproduzierbar.

### D. Per-Worker Provider Fan-Out

**Pain**

- Batch-Verarbeitung erzeugt bei Parallelitaet pro Worker eigene Provider-Pfade ohne globale Steuerschicht.

**Warum das bei Handover weh tut**

- Rate-Limit-, Kosten- und Throughput-Probleme muessen spaeter unter Echtlast verstanden werden.

**Woran man es im Code erkennt**

- `process_batch()` in `llm_interpreter/interpreter.py` erstellt pro Worker neue Provider.
- Backoff ist lokal pro Request.
- Die GUI erlaubt mehrere Worker, aber keinen echten Cancel-Pfad.

**Remedy vor dem Handover**

- globale Concurrency-Grenzen
- dokumentierte Retry-Politik
- Kosten- und Groessenleitplanken
- klarer Betriebsmodus fuer Batch

**Minimaler Nachweis**

- Das Modul kann unter Lastverhalten beschrieben und begrenzt werden.

### E. Desktop-Centric Local State

**Pain**

- `.env`, Logs und Standard-Output liegen im Modulpfad und sind eng mit lokaler Desktop-Nutzung verbunden.

**Warum das bei Handover weh tut**

- Packaging, Benutzerrechte und Betriebskontext werden zu stillen Voraussetzungen.

**Woran man es im Code erkennt**

- `llm_interpreter/main.py` schreibt Logs lokal.
- `llm_interpreter/ui/app.py` speichert `.env` im Modulkontext.
- README empfiehlt benutzerschreibbare Installationspfade wegen mutabler Dateien.

**Remedy vor dem Handover**

- Mutable Dateien sauber von Produktcode trennen.
- Installations- und Laufzeitkontext explizit dokumentieren.

**Minimaler Nachweis**

- Das Modul benennt klar, was immutable Produktartefakt und was mutable Laufzeitdaten sind.

### F. Raw Adaptation Inside the Module

**Pain**

- Die Adaption des Upstream-Raw-Formats passiert im Interpreter-Modul selbst.

**Warum das bei Handover weh tut**

- Modulgrenzen werden unscharf.
- Aenderungen am Upstream-Format koennen still in den Produktkern hineinragen.

**Woran man es im Code erkennt**

- `llm_interpreter/orchestrator_contract.py` transformiert Optimizer-Raw in das modulinterne Request-Schema.

**Remedy vor dem Handover**

- Adapter explizit als Boundary Layer behandeln.
- Kernlogik und Foederationsadaption sauber unterscheiden.

**Minimaler Nachweis**

- Ein neuer Engineer kann produktinterne Logik und Foederationsadaption getrennt benennen.

## Modulraster fuer den gesamten Verband

- Jedes Modul `MUST` als eigener Projektordner im Pipeline-Root leben.
- Jedes Modul `MUST` eine lokal verantwortete Produktstruktur haben.
- Das erwartete Basisskelett ist:

```text
<modul>/
|- <lokales_package>/
|- dev-tests/
|- runtime/
|- README.md
|- requirements.txt
|- module-manifest.json
```

- `Client Frontend` ist eine dokumentierte Ausnahme vom Manifest-Bestandteil dieses Basisskeletts. Die Ausnahme `MUST` lokal in README/SPEC und im Abweichungslog sichtbar bleiben und darf nicht als Freibrief gegen Package-Root, Runtime, Dev-Tests, Installer-/Startpfade oder Handover-Evidenz gelesen werden.
- Ein Modul `MAY` zusaetzlich enthalten:
  - `config/`
  - `tools/`
  - `installer/`
  - `server/`
  - `src/`
  - `shared/`
  - `plugins/`
  - `assets/`
  - weitere modul-lokale Hilfsordner
- Jedes Modul `MUST` einen klaren lokalen Package-Root haben:
  - `orchestrator/`
  - `ingestion_layer_vision/`
  - `ingestion_layer_file/`
  - `llm_interpreter/`
  - `validator_vision/`
  - `normalizer_vision/`
  - `corpus_builder/`
  - `mcp_server/`
  - `semantic_control_kernel/`
  - `client_frontend/`
- Jedes Modul `MUST` lokal besitzen:
  - Models
  - Contract-Entry-Point
  - Runtime-Hilfen
  - Build-/Check-/Installer-Hilfen, falls relevant
  - Prompt-/Provider-/Validation-Helfer, falls relevant
- Ein oeffentlicher Standalone-Launcher wie `run.bat` gehoert fuer orchestratorgebundene Module nicht mehr zum Basiskontrakt.
- Modulinterne GUI-Surfaces gehoeren fuer orchestratorgebundene Module ebenfalls nicht mehr zum Pflichtumfang; Interaktion lebt zentral im Orchestrator oder in separaten Frontend-Clients ausserhalb des Modulvertrags.
- Jedes Modul `MUST NOT` Code, Config oder Runtime direkt aus Schwesterordnern importieren.
- Wiederverwendete Muster duerfen uebernommen werden, aber die Verantwortung bleibt lokal beim Modul.

## Pflichtregeln gegen Drift

- `MUST` Jedes Modul hat ein `module-manifest.json` mit konsistenter Bedeutung von:
  - `module_key`
  - `display_name`
  - `contract_version`
  - `runtime_dir`
  - `contract_module`
  - `actions`
  - `external_dependencies`
- `MUST` Contract-Aktionen folgen einem erkennbaren Namensmuster wie `<verb>_document` oder `healthcheck`.
- `MUST` Jedes Modul hat eine lokale `dev-tests/`-Suite, die ueber das Root-Tooling discoverbar und ausfuehrbar ist.
- `MUST` Jedes Modul folgt derselben Runtime-Grundidee:
  - lokale Runtime unter `runtime/`
  - dokumentierte Build-Pfade
  - dokumentierte mutable vs immutable Artefakte
- `MUST` Orchestratorgebundene Module bleiben headless:
  - kein `run.bat` als Pflichtoberflaeche
  - keine modulinterne GUI als Standardbetriebsweg
  - oeffentliche Eintrittsflaeche ist der Contract-Entry-Point plus dokumentierte Runtime-Hilfen
- `MUST` Jedes Modul dokumentiert seine Laufzeitannahmen sichtbar in README oder SPEC:
  - Plattform
  - externe Services
  - native Abhaengigkeiten
  - Rechtebedarf
  - headless Betrieb unter dem Orchestrator, sofern das Modul orchestratorgebunden ist
- `MUST` Jedes Modul trennt Boundary Layer und Produktkern logisch:
  - Orchestrator-/Raw-Adapter
  - Fachlogik
  - Persistence
  - separate Frontend- oder Bedienlayer, falls ein solcher ausserhalb des Modulvertrags existiert
- `MUST` Control-Plane-Module wie `07 - MCP Server` bleiben duenne Delegationsflaechen:
  - keine zweite Business-Logic-Welt neben den Owner-Modulen
  - keine direkten Raw-State-, Config- oder Runtime-Writes in Schwesterordner
  - schreibende Cross-Modul-Operationen nur ueber manifestierte owner-lokale Contracts
  - MCP-Toolkatalog, Owner-Delegation, Permissions und Fail-Closed-Verhalten sind in README, SPEC, Manifest und Tests sichtbar
- `MUST` Workflow-Governance-Module wie `08 - Semantic Control Kernel` bleiben owner-klare Orchestrierungs- und Zustandsmodule:
  - Workflow-Semantik, Statusuebergaenge, Dialog-/Mirror-/Progress-Vertraege, Resume-/Recovery-/Receipt-State und policy-getriebene Delegation liegen im Modul
  - owner-lokale Fachmutationen bleiben ausserhalb und werden nur ueber Adapter und owner-lokale Contracts erreicht
  - keine zweite editierbare Fachwahrheit fuer Datenbank, Semantic Release, Artifact Tree oder Frontend-Dialogzustand
  - kein UI-Rendering, kein MCP-Transport und keine versteckte Schwester-Modul-Fachlogik im Kernel
  - der erste saubere Seed fuer nachfolgende Kernel-Flows ist `empty_database_no_semantic_release`; Shared Provisioning-, Interaction-, State- und Notice-Bausteine muessen dort sichtbar wiederverwendbar statt workflow-lokal dupliziert sein
- `MUST` Frontend-Module wie `Client Frontend` bleiben governance-pflichtige Produktmodule:
  - kanonische Produktquelle, pfadstabile Browser-/Server-Surfaces und gebaute Artefakte sind unterscheidbar
  - mutable Config-, State-, Log-, Credential- und Token-Artefakte liegen ausserhalb des immutable Payloads oder sind als Legacy-/Snapshot-Pfad explizit klassifiziert
  - Browser-Surfaces duerfen keine Secrets, OAuth-Tokens oder internen Runtime-Pfade persistieren oder ausgeben
  - Provider-I/O, Credential-Resolver, Config, Vault, Chat-/Memory-State, Minimal-Agent und HTTP-Surface bleiben als interne Ownership-Grenzen benennbar
  - direkte Eingriffe in Pipeline-Schwester-State sind unzulaessig; Pipeline-Operationen laufen ueber dokumentierte lokale Server-, MCP- oder Owner-Contract-Grenzen
  - Manifestfreiheit ist eine dokumentierte Abweichung, keine Befreiung von Runtime-, Dev-Test-, Installer-, Security- oder Handover-Regeln
- `MUST` Jedes Modul hat eine erklaerbare Fehler- und Debug-Strategie.
- `MUST` Jedes Modul hat dokumentierte mutable Pfade fuer:
  - Konfiguration
  - Logs
  - Outputs
  - Runtime-Zwischenstaende
- `MUST` Jedes Modul hat sichtbare Evidenz fuer seine Produktguete, nicht nur fuer seine lokale Codeform.
- `MUST` Jede bewusste Abweichung gegen diese SPEC steht im `Abweichungslog`.
- `SHOULD` Gleichartige Modultypen nutzen vergleichbare Dateinamen, Action-Namen und Hauptentrypoints.
- `SHOULD` Contract-, Debug- und Runtime-Helfer gleichartiger Module folgen denselben Bedienmustern.
- `SHOULD` Root-Tooling fuer Build, Installer und Dev-Tests bleibt die erste Referenz, nicht modul-lokale Sonderwege.
- `MAY` Ein Modul strengere lokale Regeln einfuehren, wenn diese die Foederation nicht fragmentieren.

## Driftanker fuer semantische Wahrheiten

- `MUST` Jedes Modul, das dieselbe fachliche Aussage in mehr als einer persistenten Form fuehrt, diese Formen explizit als genau eine der folgenden Kategorien benennen:
  - `authoring truth`
  - `compiled truth`
  - `runtime truth`
  - `compatibility artifact`
- `MUST` Pro fachlichem Fakt existiert genau eine editierbare `authoring truth`.
- `MUST NOT` Zwei unterschiedliche persistente Repräsentationen denselben fachlichen Fakt gleichzeitig als editierbare Produktwahrheit beanspruchen.
- `MUST` `compiled truth` aus einer benannten `authoring truth` deterministisch oder kontrolliert regenerierbar sein.
- `MUST NOT` `compiled truth` direkt von Hand oder ueber GUI-/Agentenabkuerzungen editiert werden, ausser diese Bearbeitung ist selbst wieder der definierte Authoring-Pfad.
- `MUST` `runtime truth` als operativer Zustand erkennbar, resetbar und von fachlicher Langzeitwahrheit getrennt bleiben.
- `MUST NOT` `runtime truth` heimlich zur dauerhaften Produktwahrheit werden.
- `MUST` Workflow-Run-, Resume-, Lock-, Mirror-, Progress-, Receipt- und Recovery-Dateien eines Workflow-Governance-Moduls als `runtime truth` behandelt werden, nie als editierbare fachliche `authoring truth`.
- `MUST` `compatibility artifact` als one-way abgeleitete Kompatibilitaetsbruecke behandelt werden.
- `MUST NOT` `compatibility artifact` in die `authoring truth` zuruecksynchronisieren oder als primaere Edit-Surface verwendet werden.
- `MUST` Neue persistente Dateien, Tabellen, JSON-Felder oder Cache-Artefakte vor ihrer Einfuehrung gegen diese Truth-Kategorien geprueft werden.
- `MUST NOT` Ein Build, Refactor oder Feature eine zweite mutable Wahrheit einfuehren, nur um lokalen Komfort, Legacy-Kompatibilitaet oder Debug-Bequemlichkeit zu gewinnen.
- `MUST` Jede Domain mit mehrfachen Repräsentationen sichtbar dokumentieren:
  - welcher semantische Fakt gemeint ist
  - wo die `authoring truth` liegt
  - welche Formen nur compiled/runtime/compatibility sind
  - wie abgeleitete Formen neu erzeugt werden
- `MUST` UI-State, Debug-State, Cache-Dateien, Bundle-Caches und Report-Artefakte explizit als nicht-fachliche Wahrheiten behandeln, sofern nicht das Gegenteil dokumentiert und begruendet ist.
- `MUST NOT` Readme-, SPEC-, Contract- oder Test-Text eine abgeleitete Form so beschreiben, als waere sie die primaere Wahrheit.
- `SHOULD` Module mit komplexen Repräsentationsketten eine kleine lokale Truth-Map in README, SPEC oder owner-lokaler Governance-Datei pflegen.
- `SHOULD` Fuer `compiled truth` und `compatibility artifact` ein Delete-and-Rebuild-Drill existieren, der beweist, dass keine versteckte zweite Wahrheit noetig ist.
- `SHOULD` Review und CI sichtbare Drift-Warnungen ausloesen, wenn neue persistente Repräsentationen ohne benannte Truth-Kategorie auftauchen.

## Runtime- und Installer-Driftanker fuer Windows-Module

- `MUST` Jedes installierbare Pipeline-Modul eine modul-lokale Runtime unter `runtime/` besitzen.
- `MUST NOT` Ein Modul zur Laufzeit Host-Python, `py`, globale Shared-Runtimes oder moduluebergreifend installierte Laufzeitkopplungen voraussetzen.
- `MUST` `runtime/runtime-manifest.json` als sichtbaren Runtime-Vertrag fuehren.
- `MUST` Launcher und Contract-Entry-Points einen harten Runtime-Preflight ausfuehren, der fehlende Runtime-Bestandteile, ungueltige mutable Pfade oder fehlerhafte Installation frueh und erklaerbar stoppt.
- `MUST` Die Runtime offline reproduzierbar baubar sein:
  - versionierte Abhaengigkeiten
  - Lockfile oder gleichwertige pinningfaehige Quelle
  - Wheelhouse, Wheelhouse-Zip oder gleichwertiges lokales Build-Artefakt
- `MUST` mutable und immutable Artefakte explizit trennen:
  - installierter Payload bleibt read-only denkbar
  - per-user State, Config, Logs und Outputs leben ausserhalb des immutable Payloads
- `MUST NOT` stille mutable Dateien im Payload fuehren, wenn diese nicht sichtbar gelistet, begruendet und upgrade-sicher behandelt werden.
- `MUST` Ein per-user Installer oder gleichwertiger Installationspfad ohne Adminrechte moeglich sein, sofern das Modul als installierbares Produktmodul ausgeliefert wird.
- `MUST` Installer, Upgrade und Runtime-Pruefung sowohl Quelllayout als auch Zielinstallation validieren, wenn das Modul einen Installer- oder Packaging-Pfad besitzt.
- `MUST` Upgrades mutable State erhalten oder explizit und sichtbar migrieren.
- `MUST` Signier- und Vertrauenskette sichtbar dokumentieren:
  - was lokal signiert wird
  - welche Vendor-Binaries oder Drittartefakte uebernommen werden
  - welche Signaturannahmen oder Ausnahmen gelten
- `MUST NOT` README, Launcher, Installer, Runtime-Manifeste und Tests unterschiedliche Aussagen zum Start- oder Installationsweg machen.
- `MUST NOT` Endnutzer fuer den regulaeren Produktstart auf `python`, `py`, Host-venvs oder `build-runtime.bat` verweisen.
- `MUST` Runtime-, Installer- und Packaging-Pfade durch lokale Tests oder gleichwertige Verifikation abgesichert werden.
- `SHOULD` Ein Modul auf frischem User-Profil oder frischer VM ohne Reverse Engineering installierbar und startbar sein.
- `SHOULD` Runtime-Checks pruefen, dass keine Host-Pfade in den Produktstart hineinleaken.

## Refactor-Driftanker fuer modulweite Umbauten

- `MUST` Jeder modulweite Refactor mit einer expliziten Einordnung des primaeren Modul-Archetyps beginnen:
  - `control_module`
  - `mcp_control_plane_module`
  - `frontend_module`
  - `optimizer_module`
  - `interpreter_module`
  - `validation_module`
  - `normalization_module`
  - `corpus_module`
  - `placeholder_module`
  - `mixed_legacy_module`
- `MUST` `mixed_legacy_module` als Drift-Diagnose und Uebergangszustand behandelt werden, nicht als dauerhaft akzeptierte Zielarchitektur.
- `MUST` `placeholder_module` keine halluzinierte Produktlogik erhalten; erlaubt sind hoechstens minimales Foederationsskelett und sichtbar dokumentierte Blocker.
- `MUST` Modulweite Refactors nur an echter Produktquelle arbeiten.
- `MUST NOT` generierte, gebaute, vendored oder reine Runtime-/Packaging-Spiegel als primaere Refactor-Zielflaeche behandeln, insbesondere:
  - `dist/`
  - `runtime/`
  - `node_modules/`
  - `venv/`
  - `.venv/`
  - `site-packages/`
  - `__pycache__/`
  - `.pytest_cache/`
  - `.pytest-tmp/`
  - `.tmp/`
- `MUST` Vor einem modulweiten Umbau eine Preflight-Inventur durchfuehren, die mindestens sichtprueft:
  - `README.md` oder kanonische lokale Doku
  - `module-manifest.json`, falls vorhanden
  - lokalen Package-Root
  - `dev-tests/`
  - `runtime/`
  - `requirements.txt`
  - Runtime-Build- und Check-Helfer
  - relevante mutable Pfade wie `state/`, `output/`, `config/`, `.env`
  - oeffentliche Entry-Points und Contract-Flaechen
  - naheliegende Schwester-Module derselben Familie
  - beruehrtes Root-Tooling
- `MUST` Fehlendes `module-manifest.json` als Drift behandeln.
- `MUST NOT` fehlende `actions`, Entry-Points oder Contract-Flaechen ohne belastbare Evidenz aus Code, README, Tests oder Schwester-Modul erfinden.
- `MUST` unklare oder unvollstaendige Vertragsannahmen sichtbar im `Abweichungslog` dokumentieren.
- `MUST` Vor groesseren Schnitten eine Stufenkarte erstellen, in der groessere Dateien, Komponenten oder Entry-Points genau einer oder hoechstens zwei dieser Stufen zugeordnet werden:
  - `surface`
  - `adapter`
  - `workflow`
  - `domain`
  - `repository`
  - `validation`
  - `policy`
  - `types`
  - `debug`
- `MUST` `surface` als duenne, pfadstabile oeffentliche Fassade behandeln.
- `MUST` `domain` seiteneffektfrei halten.
- `MUST` externe I/O, Datei-, Prozess-, Queue-, Cache- oder DB-Zugriffe in `adapter` oder `repository` halten, nicht in `domain`.
- `MUST` `validation` und `policy` trennbar bleiben.
- `MUST` Jede neue oder geschnittene Datei eine Hauptverantwortung und hoechstens eine dominante Stufe haben.
- `SHOULD` Catch-all-Dateien wie `utils`, `helpers`, `misc`, `common2`, `part2` oder `extra` vermeiden.
- `SHOULD` Ergebnisdateien grundsaetzlich bei ungefaehr `200 LOC` oder darunter halten, ausser ein klar begruendeter, pfadstabiler Surface-Wrapper ist das kleinere Uebel.
- `MUST` Contract- und Einstiegspfade stabil halten oder im selben Refactor konsistent migrieren, insbesondere:
  - `contract_module`
  - `launcher_module`
  - `actions`
  - CLI- oder GUI-Entry-Points
  - Runtime-Build-Helfer
  - Root-discoverbare Testpfade
- `MUST` private Test-Seams, Monkeypatch-Pfade und root-tooling-relevante Test-Discoverability erhalten oder im selben Refactor bewusst mitmigrieren.
- `MUST` Vor Abschluss pruefen, dass Schwester-Modul-Vergleichbarkeit, Root-Tooling-Kompatibilitaet und Foederationsbegriffe intakt bleiben.
- `MUST` Ein modulweiter Refactor am Ende mindestens die beruehrten Contract-, Workflow-, Runtime- oder Regression-Pfade verifizieren oder die Luecke explizit als Restrisiko benennen.
- `SHOULD` Ein Refactor vereinfachen statt bloss Komplexitaet umzuverteilen.
- `MUST` Dateiweite Refactors vor dem Umbau mindestens sichten:
  - Zieldatei
  - direkte Aufrufer und Exporte
  - betroffene Tests
  - README-, SPEC- oder Manifest-Verweise
  - naheliegende Schwesterdatei desselben Modultyps
- `MUST` Dateiweite Refactors einen expliziten Datei-Archetyp benennen:
  - `pipeline_monolith`
  - `ui_monolith`
  - `policy_monolith`
  - `types_monolith`
  - `test_monolith`
  - `generated_artifact`
- `MUST NOT` `generated_artifact` direkt refactoren; stattdessen ist zur kanonischen Quelldatei zu wechseln.
- `MUST` `policy_monolith`, `types_monolith` und `test_monolith` entlang ihrer fachlichen Verantwortung schneiden statt sie kuenstlich in einen Workflow-Schnitt zu pressen.
- `MUST` Bei Datei-Splits direkte Dateipfad-Abhaengigkeiten stabil halten oder im selben Refactor vollstaendig und sichtbar migrieren, insbesondere:
  - `orchestrator_contract`-Entry-Points
  - direkte Python-, JS- oder TS-Dateiimporte
  - `package.json`-Script-Ziele
  - dokumentierte CLI- oder GUI-Dateipfade
- `SHOULD` Wenn eine Datei unter bestehendem Pfad erreichbar bleiben muss, eine duenne pfadstabile Fassade oder Re-Export-Datei behalten und die neue Logik dahinter verschieben.
- `SHOULD` Gleichnamige Python-Dateien bei groesseren Schnitten bevorzugt in einen gleichnamigen Unterordner mit pfadstabiler `__init__.py`-Surface ueberfuehren.
- `MUST` Rohes `dict`-, JSON- oder Objekt-Passing zwischen mehr als einer Pipeline-Stufe nicht still fortschreiben, wenn benannte `types` die Stufengrenzen klarer und stabiler machen.

## Kernel Workflow Seed Blueprint

- Der erste funktionale Seed fuer die Workflow-Haertung des `08 - Semantic Control Kernel` ist `empty_database_no_semantic_release`.
- Dieser Seed `MUST` nicht nur den Happy Path demonstrieren, sondern auch die Governance-Grundform fuer alle folgenden Kernel-Workflow-Fixes vorgeben.
- Das bedeutet fuer jeden nachfolgenden Kernel-Workflow:
  - Shared Schritte wie Target-Aufloesung, Provisioning, Repository-Schreiben, Transition-Checks, Resume-Aufbau und Notice-Erzeugung werden nicht workflow-lokal neu gebaut, wenn sie schon als wiederverwendbarer Kernel-Baustein existieren.
  - Workflow-spezifische Semantik, Next-Step-Erklaerung oder user-facing Completion-Details duerfen nicht den generischen Shared-Layer verschmutzen.
  - `surface`, `workflow`, `repository`, `policy`, `validation` und `types` bleiben benennbar; der Seed darf kein monolithisches "routes.py macht alles"-Muster als Standard setzen.
  - Interaction-Ports muessen den benannten Shared-Contract voll oder fail-closed erfuellen; Folge-Flows duerfen nicht an fehlenden Methoden oder impliziten UI-Annahmen haengen.
  - Mirror-/Progress-/Receipt-/Resume-State bleibt Kernel-owned `runtime truth`; owner-lokale Fachwahrheiten bleiben ausserhalb.
  - Follow-up-Flows orientieren sich am Seed, indem sie vorhandene Shared-Bausteine uebernehmen oder bewusst erweitern, statt neue parallele Hilfsschichten zu erfinden.
- Ein Kernel-Workflow gilt deshalb erst dann als "guter Fix", wenn er:
  - funktional laeuft,
  - die Governance-Schnitte sichtbar wahrt,
  - bestehende Shared-Bausteine uebernimmt,
  - und selbst wieder als lesbares Vergleichsmuster fuer spaetere Flows dienen kann.

## Optimierungs- und Hardening-Driftanker

- `MUST` Optimierungen Modularitaet, Contract-Sichtbarkeit, Self-Containment und Foederationsvergleichbarkeit erhalten; reine Code-Ersparnis rechtfertigt keine strukturelle Regression.
- `MUST` Aenderungen an output-praegender Logik die betroffene Testsuite als Regression nachziehen oder erweitern.
- `MUST` Regressionen bevorzugt gegen Fehlerklassen und Invarianten formulieren, nicht nur gegen glueckliche Positivfaelle.
- `SHOULD` Negative Tests, Break-Tests und Fehlerrouten explizit dort ausbauen, wo sie Edge Cases, Race Conditions, Security-Flanken oder Formatgrenzen absichern.
- `SHOULD` Reale Einzelartefakte nur dann direkt als Testfixture dienen, wenn sie eine kanonische Regression tragen; generische Schutztests bleiben die erste Wahl.
- `MUST` Kalibrierungen oder Optimierungen, die nur eine Datenklasse, ein Dokumentmuster oder ein Extraction-Format betreffen, ihren Geltungsbereich sichtbar begrenzen.
- `MUST NOT` Eine lokale Kalibrierung still andere Datenklassen, Formate oder Schwesterpfade verschlechtern, ohne dass dies getestet oder offen als Restrisiko dokumentiert ist.
- `MUST` Bestehende Testabdeckung fuer weiterhin relevante Funktionen erhalten oder gleichwertig ersetzen; Testabbau ohne Funktionsabbau ist Drift.
- `SHOULD` Produktionsnaehe explizit gegen Edge Cases, frische Umgebung, Fehlerpfade und reale Betriebsannahmen beurteilt werden, nicht nur gegen synthetisches Testgruen.
- `SHOULD` Produktpfade nicht ausschliesslich auf IDE- oder ad-hoc-Shell-Verhalten angewiesen sein; Build- oder Wrapper-Skripte sind Hilfen, nicht die einzige erklaerbare Betriebswirklichkeit.

## Audit Checklist

### Struktur

- [ ] `MUST` Modul hat klaren lokalen Package-Root.
- [ ] `MUST` Modul hat `README.md`, `module-manifest.json`, `runtime/`, `dev-tests/`; dokumentierte Ausnahmen wie `Client Frontend` ohne Manifest sind im Abweichungslog sichtbar, `run.bat` ist kein Pflichtbestandteil mehr.
- [ ] `MUST` Produktcode, Runtime-Artefakte und mutable Laufzeitdaten sind unterscheidbar.
- [ ] `SHOULD` Datei- und Ordnernamen folgen den etablierten Mustern des Verbands.

### Refactor Discipline

- [ ] `MUST` Primaerer Modul-Archetyp ist benannt oder eine Placeholder-/Legacy-Drift explizit gemacht.
- [ ] `MUST` modulweite Refactors arbeiten an Produktquelle statt an Runtime-, Build- oder Packaging-Spiegeln.
- [ ] `MUST` Preflight-Inventur fuer Manifest, README, Entry-Points, Runtime, Tests, mutable Pfade und Schwester-Modul ist erfolgt.
- [ ] `MUST` dateiweite Refactors haben direkten Caller-/Export-/Test-/Doc-Abgleich und einen benannten Datei-Archetyp.
- [ ] `MUST` groessere Dateien, Komponenten oder Entry-Points sind ueber eine Stufenkarte auf `surface`, `adapter`, `workflow`, `domain`, `repository`, `validation`, `policy`, `types` oder `debug` abbildbar.
- [ ] `MUST` `surface`, `domain`, `validation` und `policy` sind sauber geschnitten.
- [ ] `MUST` Contract-, Launcher-, Runtime-Build- und Test-Discoverability-Pfade sind stabil oder konsistent migriert.
- [ ] `MUST` direkte Dateiimporte, `orchestrator_contract`-Pfade und Script-Ziele bleiben pfadstabil oder werden bewusst mitmigriert.
- [ ] `SHOULD` mehrstufige rohe Datenuebergaben werden durch benannte `types` ersetzt, wenn sie sonst Stufengrenzen verschleiern.
- [ ] `SHOULD` Refactor reduziert Komplexitaet sichtbar statt sie nur neu zu verteilen.

### Contract

- [ ] `MUST` Contract-Entry-Point ist eindeutig.
- [ ] `MUST` Action-Namen sind dokumentiert und in Code, Tests und Manifest konsistent.
- [ ] `MUST` Input- und Output-Invarianten sind erkennbar.
- [ ] `SHOULD` harte vs weiche Contract-Bereiche sind explizit beschrieben.
- [ ] `MUST` Control-Plane-/MCP-Module delegieren schreibende Operationen owner-klar und blockieren unklassifizierte Tools fail-closed.
- [ ] `MUST` Workflow-Governance-Module wie `08 - Semantic Control Kernel` halten Workflow-Semantik, Runtime-State und owner-klare Delegation im Modul, ohne UI-Rendering, MCP-Transport oder zweite Fachwahrheiten aufzubauen.
- [ ] `MUST` Frontend-Module haben pfadstabile Browser-/Server-/Config-Surfaces und klare interne Grenzen fuer Provider, Credentials, Vault, State, Minimal-Agent und HTTP.

### Runtime

- [ ] `MUST` Runtime-Build-Pfad ist dokumentiert.
- [ ] `MUST` Runtime-Layout ist reproduzierbar und testbar.
- [ ] `MUST` Plattform- und Rechteannahmen sind sichtbar.
- [ ] `MUST` Modul startet ohne Host-Python oder globale Shared-Runtime.
- [ ] `MUST` `runtime/runtime-manifest.json` ist vorhanden und beschreibt den Runtime-Vertrag.
- [ ] `MUST` Launcher/Entry-Points fuehren einen harten Runtime-Preflight aus.
- [ ] `MUST` mutable und immutable Artefakte sind klar getrennt.
- [ ] `SHOULD` Runtime-Checks weisen Host-Pfad-Leaks sichtbar nach oder schliessen sie aus.
- [ ] `SHOULD` Runtime-spezifische Sonderfaelle sind vom Produktcode getrennt.

### Installer and Packaging

- [ ] `MUST` Installierbare Produktmodule lassen sich ohne Adminrechte per-user installieren oder sichtbar begruendet nicht.
- [ ] `MUST` Installer-, Upgrade- und Packaging-Pfade pruefen Quelllayout und Zielinstallation konsistent.
- [ ] `MUST` Upgrades erhalten mutable State oder migrieren ihn sichtbar.
- [ ] `MUST` Offline-rebuildbare Runtime-Artefakte, Locking-Strategie und lokale Dependency-Quelle sind benannt.
- [ ] `MUST` Signierliste oder gleichwertige Vertrauenskette fuer lokale und uebernommene Artefakte ist dokumentiert.
- [ ] `MUST` Tests oder gleichwertige Drills decken Runtime-, Installer- oder Packaging-Pfade ab.

### Config and Secrets

- [ ] `MUST` Konfigurationsquellen sind klar benannt.
- [ ] `MUST` Secrets liegen nicht zufaellig zwischen Produktartefakten.
- [ ] `MUST` Default-Pfade fuer mutable Daten sind dokumentiert.
- [ ] `SHOULD` Config-Ladevorgang ist zwischen Contract, Debug-Surfaces und Runtime-Hilfen konsistent.
- [ ] `MUST` Frontend-Credential- und OAuth-State bleibt serverseitig oder app-home-lokal; Browser-Storage, Query-Parameter und oeffentliche Config-Payloads enthalten keine Tokens oder Secrets.

### Truth and Derived Artifacts

- [ ] `MUST` Jede fachliche Aussage mit mehr als einer persistenten Form hat genau eine benannte `authoring truth`.
- [ ] `MUST` Mehrfachrepräsentationen sind als `compiled truth`, `runtime truth` oder `compatibility artifact` klassifiziert.
- [ ] `MUST` Keine zweite editierbare Produktwahrheit ist aus Legacy-, Komfort- oder Debuggruenden entstanden.
- [ ] `MUST` `compiled truth` ist regenerierbar und wird nicht manuell gepflegt.
- [ ] `MUST` `runtime truth` ist resetbar und nicht mit fachlicher Dauerwahrheit vermischt.
- [ ] `MUST` `compatibility artifact` ist one-way abgeleitet und sync’t nicht zurueck in den Authoring-Pfad.
- [ ] `SHOULD` Delete-and-Rebuild-Drills oder gleichwertige Beweise zeigen, dass keine versteckte Zweitwahrheit noetig ist.

### Observability

- [ ] `MUST` Hauptfehler lassen sich einer Pipeline-Stufe zuordnen.
- [ ] `MUST` Logs oder Debug-Artefakte helfen bei Root-Cause-Analyse.
- [ ] `SHOULD` grosse Transformationen koennen optional nachvollzogen werden.

### Test Quality

- [ ] `MUST` lokale Dev-Suite deckt Kernlogik und Fehlerrouten ab.
- [ ] `MUST` Contract-Pfade sind getestet.
- [ ] `MUST` output-praegende Aenderungen ziehen Regressionstests nach sich.
- [ ] `MUST` weiterhin relevante Funktionen verlieren keine Testabdeckung ohne gleichwertigen Ersatz.
- [ ] `SHOULD` negative Tests, Break-Tests oder Fehlerklassen-Tests decken kritische Edge Cases ab.
- [ ] `SHOULD` es gibt Regressionen mit realistischen oder echten Artefakten.
- [ ] `SHOULD` Testgruen ersetzt nicht die Dokumentation von Rest-Risiken.

### Data Safety

- [ ] `MUST` Pfadeingaben, Dateizugriffe und Schreibpfade haben klare Grenzen.
- [ ] `MUST` Input-Groessen- und Lastannahmen sind sichtbar.
- [ ] `MUST` format- oder datenklassenspezifische Kalibrierungen haben sichtbare Grenzen und keine stillen Nebenwirkungen auf andere Pfade.
- [ ] `SHOULD` gefaehrliche oder teure Pfade fail-fast behandelt werden.

### Concurrency and Cost Control

- [ ] `MUST` Parallelitaet und Retry-Verhalten sind erklaerbar.
- [ ] `MUST` Batch-Verhalten ist nachvollziehbar.
- [ ] `SHOULD` kritische Race-Condition-, Reentrancy- oder Idempotenzrisiken sind geprueft oder sichtbar benannt.
- [ ] `SHOULD` Kosten-, Token-, Seiten- oder Groessenlimits dokumentiert sein.
- [ ] `SHOULD` Langlaeufer und Abbruchverhalten sichtbar geregelt sein.

### Handover Readiness

- [ ] `MUST` Ein neuer Engineer kann das Modul ohne Reverse Engineering starten.
- [ ] `MUST` Der Datenfluss ist in Stufen erklaerbar.
- [ ] `MUST` bewusste Risiken und bekannte Unsauberkeiten sind dokumentiert.
- [ ] `SHOULD` der Modulzustand ist eher "verstehbar und beherrschbar" als "perfekt".

### Cross-Module Alignment

- [ ] `MUST` Keine Code-, Config- oder Runtime-Imports aus Schwesterordnern.
- [ ] `MUST` Modul folgt dem Foederationsvertrag statt einer lokalen Sonderwelt.
- [ ] `SHOULD` Muster und Begriffe sind mit vergleichbaren Modulen abgestimmt.
- [ ] `MAY` begruendete Spezialisierung existieren, wenn sie dokumentiert ist.

## Abweichungslog Template

| Modul | Regel | Abweichung | Grund | Owner | Follow-up Datum | Risiko wenn offen |
| --- | --- | --- | --- | --- | --- | --- |
| 02 - Interpreter | MUST: harte vs weiche Contractbereiche sichtbar | JSON-Reparatur und flexible Extensions noch gemischt | Historisch gewachsene LLM-Guardrail-Logik | <name> | 2026-04-15 | Debugging und Downstream-Vertragsunklarheit |
| <modul> | <regel> | <abweichung> | <grund> | <owner> | <datum> | <risiko> |

## Anwendung auf weitere Module

- Die Pipeline `MUST` nicht nur lokal, sondern in Review-Reihenfolge als Verband aufgeraeumt werden.
- Empfohlene Reihenfolge fuer den Foederationsabgleich:

1. `00 - Orchestrator`
   Foederationszentrum, Registry, Steuerung, Modulverdrahtung.
2. `01 - Optimizer`
   Vereinter Upstream-Slot fuer `vision` und `file`, Raw-Contracts, Asset-Erzeugung, Routing-Hints sowie Sicherheits- und Dateipfadgrenzen.
3. `02 - Interpreter`
   Vereinter LLM-Slot derselben Hauptlinie; kanonischer Request-Contract, Prompt-/Provider-Disziplin, Output-Form und Debuggability.
4. `03 - Validator`
   formale und fachliche Pruefgrenzen zwischen structured und normalized Welt.
5. `04 - Normalizer`
   Taxonomie-, Governance- und Downstream-Invarianten.
6. `05 - Corpus Builder`
   Persistenz, normalized-first Integrationspunkt der Hauptlinie, Artefakt-Rebuild, Such- und Embedding-Grenzen sowie Betriebs- und Datenverantwortung.
7. `06 - Edit Suite`
   Owner-lokale Readiness-, Drift- und Edit-Surfaces fuer die headless Schwester-Module.
8. `07 - MCP Server`
   Lokale `stdio`-Control-Plane fuer Agenten- und Tool-Zugriffe; delegiert an owner-lokale Contracts, besitzt nur MCP-eigene Permission- und Support-State-Wahrheiten und darf keine zweite Business-Logic-Welt aufbauen.
9. `08 - Semantic Control Kernel`
   Headless Workflow-Governance-Modul fuer Semantik, State, Dialog-/Mirror-/Progress-Vertraege, Resume-/Recovery-/Receipt-State und owner-klare Adapter-Delegation; `empty_database_no_semantic_release` ist der erste lesbare Seed, an dem sich folgende Kernel-Workflow-Fixes messen lassen muessen.
10. `Client Frontend`
   Browser-/Server-Surface ausserhalb der headless Dokument-Hauptlinie, aber mit derselben Foederations- und Runtime-Disziplin.

- Jedes Modulreview `MUST` dieselben Fragen beantworten:
  - Ist die Struktur foederationskonform?
  - Ist der primaere Modul-Archetyp plausibel und die Stufenkarte erklaerbar?
  - Ist der Contract sichtbar?
  - Sind dateiweite Schnitte pfadstabil und ohne versteckte Import- oder Script-Drift erfolgt?
  - Ist die Runtime erklaert?
  - Ist die Runtime host-unabhaengig, lokal und upgradefest?
  - Sind Optimierungen gegen Regressionen, Edge Cases und stille Kollateralschaeden abgesichert?
  - Ist die Debugbarkeit ausreichend?
  - Ist pro fachlichem Fakt genau eine `authoring truth` benannt?
  - Sind `compiled truth`, `runtime truth` und `compatibility artifact` sauber getrennt?
  - Delegieren Control-Plane- oder MCP-Surfaces owner-klar, ohne fremden State direkt zu schreiben?
  - Delegieren Kernel-Workflow-Surfaces owner-klar, halten ihre Runtime-Wahrheiten lokal und schneiden shared Workflow-Bausteine so, dass Folge-Flows sie direkt uebernehmen koennen?
  - Bleiben Frontend-Surfaces, Config, Credentials, lokaler State und gebaute Browser-Artefakte governance-konform getrennt?
  - Sind Risiken dokumentiert?
  - Ist die Abweichung gegen andere Module bewusst oder zufaellig?
- Lokale Fixes `MUST` gegen diese SPEC geprueft werden, bevor sie als "pipelineweit guter Standard" gelten.
- Ein Modul darf nicht lokal "verbessert" werden, wenn diese Verbesserung die Vergleichbarkeit mit seinem Modultyp oder dem Foederationsvertrag verschlechtert.

## Done Definition fuer Handover-Prep

- Ein Modul ist handover-friendly, wenn es nicht perfekt, aber beherrschbar ist.
- Handover-Prep ist erreicht, wenn:
  - Struktur und Entry-Points ohne Sucharbeit klar sind
  - Datenfluss in Stufen erklaert werden kann
  - bei groesseren Umbauten Modul-Archetyp, Stufenkarte und Refactorpfad nachvollziehbar bleiben
  - dateiweite Splits ueber pfadstabile Facades, benannte `types` und sichtbare Entry-Points nachvollziehbar bleiben
  - Runtime- und Plattformannahmen sichtbar sind
  - Runtime, Installer und Upgrade-Pfade keinen versteckten Host- oder Shared-Runtime-Bedarf haben
  - output-praegende Aenderungen gegen Regressionen und angrenzende Formate abgesichert sind
  - pro kritischer Domain klar ist, was `authoring truth`, `compiled truth`, `runtime truth` und `compatibility artifact` ist
  - bekannte Risiken offen dokumentiert sind
  - Tests nicht nur lokale Logik, sondern wenigstens einen Teil der Produktwirklichkeit absichern
  - Abweichungen gegen den Foederationsstandard nicht versteckt, sondern protokolliert sind
  - ein Senior Developer das Modul debuggen, refactoren und in den Verband einordnen kann, ohne zuerst implizites Stammeswissen einsammeln zu muessen

## Abschlussgedanke

- Das Ziel dieser SPEC ist nicht, jeden spaeteren Eingriff unnoetig zu machen.
- Das Ziel ist, spaetere Eingriffe berechenbar zu machen.
- Eine saubere Handover-Vorbereitung bedeutet nicht "niemand muss mehr Hand anlegen".
- Sie bedeutet:
  - die naechste Person muss nicht blind anfangen
  - lokale Aenderungen zerstoeren nicht die Foederationsform
  - finaler Debug wird systematisch statt improvisiert
