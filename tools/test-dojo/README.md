# Vision Pipeline Test Dojo

Das Test Dojo ist die geplante Root-Surface fuer produktionsnahe End-to-End-,
GUI-, Contract-, MCP- und Browser-Tests der Vision Pipeline.

Aktueller Stand: Skelett. Der Einstieg kann Suiten listen, Suite-Manifeste
validieren und Trockenlauf-Reports erzeugen. Die fachliche Zielarchitektur und
die Abnahmekriterien stehen in `SPEC.md`.

## Einstieg

```bat
tools\run-test-dojo.bat list
tools\run-test-dojo.bat inspect --suite all
tools\run-test-dojo.bat run --suite orchestrator-ui
```

Reports entstehen unter:

```text
.tmp/test-dojo/reports/<run_id>/
```
