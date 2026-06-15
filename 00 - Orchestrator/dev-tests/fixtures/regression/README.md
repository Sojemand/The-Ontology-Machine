# Regression Fixtures

Replay-basierte End-to-End-Regressionsfaelle fuer `00 - Orchestrator`.

- `happy_path`
  - Ein erfolgreicher Ein-Dokument-Run auf Basis eines anonymisierten radiologischen Ein-Seiten-Befunds mit Golden-Erwartungen fuer State, Artefakte und `corpus.db`.
- `receipt_live`
  - Ein erfolgreicher Replay-Fall auf Basis eines echten Live-Captures eines synthetischen Kassenbons mit echten Schwester-Modulen.
- `validator_fail`
  - Ein wiederholter Validator-Fehler auf Basis einer anonymisierten Ein-Seiten-Rechnung, der nach drei Versuchen in ein finales Error-Bundle laeuft.
- `interpreter_review`
  - Ein synthetischer Interpreter-Review-Fall, der den fruehen Review-/Error-Pfad inklusive Retry-Logik abdeckt.
- `normalizer_review`
  - Ein synthetischer Normalizer-Review-Fall, der drei Normalizer-Retries und das finale Bundle mit `normalized`-Artefakt abdeckt.
- `synthetic_scan_pdf_multipage`
  - Ein synthetischer, aus Produktions-Artefaktformen abgeleiteter Mehrseiten-Scan-PDF-Fall mit page-scoped Raw-, Request-, Structured-, Validation- und Normalized-Artefakten.
- `synthetic_born_digital_pdf_table`
  - Ein synthetischer born-digital PDF-Tabellenfall fuer das `file`-Profil.
- `synthetic_docx_file_profile`
  - Ein synthetischer DOCX-Fall fuer den file-basierten Dokumentpfad.
- `synthetic_msg_thread_file_profile`
  - Ein synthetischer MSG/E-Mail-Thread-Fall mit mehreren Seitenassets.
- `synthetic_text_file_profile`
  - Ein synthetischer TXT-Fall mit mehrseitiger File-Profil-Struktur.
- `synthetic_png_vision_profile`
  - Ein synthetischer PNG-/Rasterbildfall fuer das Vision-Profil.
- Reset-Roundtrip
  - Wird in `test_pipeline_regression.py` bewusst auf Basis von `validator_fail` geprueft, damit der Reset nur `Error Cases` entfernt, Quellen ins Input zuruecklegt und Erfolgsablage plus `corpus.db` unberuehrt laesst.

Die Fixtures enthalten:

- `input/`
  - realistisch benannte Eingabedateien
- `replay/`
  - versionierte Stage-Artefakte wie `raw.json`, `structured.json`,
    `*.vision_validation_report.json` oder `*.files_validation_report.json`,
    `normalized.json`
  - Inhalte sind strukturerhaltend anonymisiert, nicht 1:1 aus dem Quelldokument uebernommen
  - `synthetic_*`-Faelle enthalten keine Produktionsinhalte und uebernehmen nur Format-, Profil-, Seitenzahl- und Artefaktstruktur-Muster aus einem lokalen Artefaktordner
- `case.json`
  - Stage-Szenario und Golden-Erwartungen

Die zugehoerigen Tests laufen unter `dev-tests/tests/test_pipeline_regression.py`.
