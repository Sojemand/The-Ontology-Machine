# Optimizer

`01 - Optimizer` ist das zusammengefuehrte Optimizer-Modul der Vision Pipeline.
Es besitzt genau einen oeffentlichen Modulslot mit `module_key = "optimizer"`
und verarbeitet Dokumente ueber zwei Profile:

- `vision`: bild- und scanlastige Dokumente, LLM-OCR ueber `optimizer_ocr`, fail-closed
  `runtime_policy_path`
- `file`: born-digital PDF, Office, Mail, Text und andere dateibasierte
  Extraktionspfade

## Package-Struktur

Die drei sichtbaren Package-Namen sind aktuelle Architektur, keine Legacy-Reste:

- `ingestion_layer_vision` ist der Bearbeitungspfad fuer Scan-, Bild- und
  visuell gerenderte Inputs. Dieser Pfad besitzt den oeffentlichen
  Orchestrator-Contract und entscheidet ueber Profilwahl und Dispatch.
- `ingestion_layer_file` ist der Bearbeitungspfad fuer born-digital Files:
  native PDF-Texte, Office-Dateien, Mailformate, Markdown/Text und Plugin-
  Extraktion.
- `optimizer_ocr` ist der Vision-Layer-Port fuer den Modell-/Vision-Call. Er
  kapselt die LLM-OCR-Normalisierung und wird vom Vision-Pfad fuer Page-Assets,
  Scan-Backup-OCR und eingebettete Bildrouten genutzt.

Historisch waren Vision- und File-Pfad getrennte Module. Sie sind in diesem
Modul zusammengefuehrt, weil Classification, Artifact-Policy, Runtime-
Packaging, Debug-Vertrag und Downstream-Raw-Surface im Kern dieselbe
Optimizer-Verantwortung sind. Die Trennung bleibt deshalb intern als zwei
Bearbeitungspfade sichtbar, waehrend der Foederationsslot nach aussen genau
`optimizer` bleibt.

## Contract

- Entry-Point: `ingestion_layer_vision.orchestrator_contract`
- Actions:
  - `classify_document`
  - `extract_document`
  - `healthcheck`
  - `scan_debug_input`
  - `debug_run`
- Kanonischer Raw-Output:
  - Vision-Profil: `schema_version = "optimizer_raw_v2"`
  - Vision-Raw enthaelt nur `source`, `extraction`, `metadata`, `context`
    und `ocr_reference.blocks`
  - Pflichtfeld `optimizer_profile = "vision" | "file"`

`classify_document` ist das oeffentliche Profil-Gate. Die Action prueft den
`source_path` und liefert das empfohlene `optimizer_profile` fuer den folgenden
`extract_document`-Run zurueck: Bilddateien gehen ins `vision`-Profil,
Scan-PDFs gehen ins `vision`-Profil, born-digital PDFs und dateibasierte
Formate gehen ins `file`-Profil. `extract_document` dispatcht intern auf das
passende Profil. Der Vision-Pfad erzwingt `runtime_policy_path` fail-closed; der
File-Pfad benoetigt diesen Wert nicht. In produktiven `extract_document`-
Aufrufen werden `source_path`, `raw_output_path` und `page_assets_dir` strikt
innerhalb der vom Orchestrator uebergebenen Root-Pfade gehalten. Im
`debug_run`-Single-Modus ist `source_path` die alleinige Eingabewahrheit; ein
staler oder fehlender `input_root` darf diesen isolierten Debuglauf nicht
blockieren. Scan- und Batch-Debug benoetigen weiterhin einen gueltigen
`input_root`. Single-Debug-Zielpfade fuer Raw-JSON und Page-Assets werden fuer
Windows-Pfadgrenzen budgetiert; Stage-Verzeichnisse verwenden kurze
`.stage.*.tmp` Namen und duerfen den Dokumentnamen nicht wiederholen.
`runtime_policy_path` zeigt auf ein `runtime_semantic_assets_v1`-Bundle; der
Optimizer konsumiert daraus im Vision-Profil nur Scan-, Vision-Route- und
Renderentscheidungen. Die produktive OCR-Engine kommt nicht mehr aus der
Runtime-Policy, sondern aus dem Orchestrator-Env-Overlay `optimizer_ocr`.

Der Vision-Response liefert:

- `document_raw_path`
- `page_raw_paths`
- `page_asset_paths`

`page_asset_paths` sind working paths fuer den laufenden Interpreter-Durchlauf
und werden nicht in den persistenten Raw-Dateien serialisiert.

Im File-Profil bleibt nativer Extractor-Text die einzige Textautoritaet.
Renderer- und Zwischen-PDF-Texte duerfen nur fuer Page-Assets und
textneutrale `position.page`/`page_span`-Zuordnung verwendet werden. Wenn ein
Renderer grobe Seiten-Textbloecke liefert, werden native Absatzbloecke anhand
normalisierter Textenthaltung bzw. benachbarter Seitenreferenzen zugeordnet;
der native `value` wird dabei nicht ersetzt.

## Runtime

- Immutable Payload:
  - `ingestion_layer_vision/`
  - `ingestion_layer_file/`
  - `runtime/`
  - `plugins/`
  - `tools/`
  - `module-manifest.json`
- Mutable Laufzeitdaten:
  - `%OPTIMIZER_HOME%`
  - `%LOCALAPPDATA%\Enterprise Stack\Optimizer`
  - Quellslot-Fallback `.appdata/`
- Erwartete mutable Pfade:
  - `config/`
  - `state/`
  - `output/`
  - `logs/`

`runtime/python` ist die lokale portable CPython-Runtime. `check-runtime.bat`
validiert den Runtime-Vertrag. `tools/build-runtime.bat` ist nur Dev- und
Packaging-Tooling. Das Modul bleibt headless; es gibt keinen lokalen
Produktlauncher.

## Edit Suite

Owner-lokale Surfaces fuer `06 - Edit Suite`:

- `optimizer.settings`
- `optimizer.ocr_prompt`
- `optimizer.output_contract_preview`
- `optimizer.debug_capabilities`

`optimizer.settings` wird als gruppierte Form angezeigt: Processing
(`max_file_size_mb`, `max_blocks_per_file`, `max_cell_text_length`,
`processing_order`, `plugin_timeout_seconds`, `parallel_workers`) und
Rendering/Layout (`render_dpi`, `render_width_px`, `render_height_px`,
`page_margin_pt`, `default_font_size_pt`, `code_font_size_pt`,
`heading_font_size_pt`).
`optimizer.ocr_prompt` editiert `config/optimizer_ocr_prompt.md`; der Prompt
muss `{page_count}` behalten und kann `{source_filename}` oder
`{source_filename_sentence}` nutzen.
`optimizer.output_contract_preview` ist read-only und spiegelt Raw-Schema,
Profil-Selector, Response-Pfade, Page-Asset-Policy und die `optimizer_ocr`
Owner-Grenze. Runtime-Policy im Vision-Profil transportiert nur technische
Scan-, Route- und Renderparameter. Projection-Kataloge, fachliche
Routing-Signale, Provider-/Modellwahl und OCR-Secrets bleiben orchestrator-
bzw. downstream-owned.

## LLM-OCR

Produktive OCR laeuft zentral ueber `optimizer_ocr`:

- Vision-Bildrouten, Scan-Backup-OCR, Mail-Child-OCR und DOCX Embedded Image OCR
  nutzen denselben Port `optimizer_ocr.extract_page_assets`.
- Der Port erwartet gerenderte Page-Assets und normalisiert den Modelloutput in
  den bestehenden OCR-Result-Payload (`status`, `blocks`, `metadata`, `errors`,
  `processing_time_ms`, `needs_ocr`).
- Persistente `ocr_reference.blocks` bleiben token-schlank: `id`, `type`,
  `value`, optionale Layout-/Confidence-Hints und `formatting` nur bei
  `bold=true`; `position` und `value_type=text` werden nicht ausgeschrieben.
- Lokale OCR-Pluginordner, GPU-/CPU-Pfade und die alte Runtime-Readiness fuer
  lokale OCR sind entfernt.
- Provider, Modell, Tokenbudget, Timeout und Secret kommen ausschliesslich
  ephemer ueber `OPTIMIZER_OCR_*` aus dem Orchestrator.
- Bei OpenAI-OAuth nutzt `optimizer_ocr` denselben ChatGPT/Codex-SSE-Backendcall
  wie der Interpreter. API-Key-Modi nutzen weiterhin den konfigurierten
  Provider-Endpunkt (`/responses` oder `/chat/completions`).

## Packaging

- Per-user-Installationsziel:
  - `%LOCALAPPDATA%\Enterprise Stack\Optimizer\app`
- Installer und Runtime pruefen Quellslot und Zielinstallation ueber
  `installer.bat`, `check-runtime.bat` und `build-installer.bat`.
- OCR ist eine LLM-Abhaengigkeit des `vision`-Profils (`optimizer_ocr`).
  Der Installer prueft nur noch den portablen Runtime-Vertrag; es gibt keine
  lokale GPU-/OCR-Pruefung mehr.
- `.pst` und `.ost` laufen bevorzugt ueber die gebuendelte
  `mail-outlook-store`-Plugin-Runtime mit `pypff`; Outlook/MAPI bleibt nur
  ein optionaler Fallback des `file`-Profils.

## Tests

```bat
dev-tests\bootstrap.bat
dev-tests\run-tests.bat
```

Die Dev-Suite prueft Contract, Packaging, Runtime und ausgewaehlte
Raw-/Routing-Invarianten des vereinten Moduls.
