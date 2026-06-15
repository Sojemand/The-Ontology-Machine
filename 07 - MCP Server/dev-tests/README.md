# MCP Server Dev Tests

Lokale Python-Suite fuer den Tool-Katalog, das MCP-Framing und die fail-closed Governance des Moduls.

`tests/test_tool_contract_matrix.py` ist die vollstaendige MCP-Handler-Matrix.
Sie erzwingt fuer jedes sichtbare Tool einen Golden Path auf der MCP-Schicht,
nutzt echte Temp-Dateien fuer DBs, Semantic-Release-Bundles,
Confirmation-Artefakte und Artifact-Ordner, und prueft Regressionen fuer
Allowlists, Pflichtfelder, Typen, Pfadgrenzen und sichtbare
Owner-Orchestrierungen. Die Owner-Aufrufe werden dabei kontrolliert ersetzt,
damit der Test keine fremden Modul-States beschreibt oder echte Secrets beruehrt.
Neue Catalog-Tools muessen dort explizit als Golden Path auftauchen. Die Matrix
haelt die Normalizer-Schritte getrennt: Lesen, Planen/Review, Schreiben,
Validieren, Kompilieren, Exportieren und Aktivieren duerfen nicht still in
einem generischen L2-Tool verschwinden.

Echte Owner-Subprocess-Integration gehoert in einen separaten Test-Layer. Dort
duerfen nur owner-sichere Read-/Temp-File-Pfade laufen; mutierende Aktionen wie
workspace-lokale Working-Release-Authoring-Writes, Corpus-Reset,
Credential-Admin, Secret-Reveal oder L3-Source-Debug-Escape-Hatches muessen
entweder ueber modul-lokale Temp-Roots getestet werden oder im jeweiligen
Owner-Modul bleiben.

`tests/test_tool_subprocess_integration.py` ist dieser L2-Layer. Die Suite kopiert
Orchestrator, Normalizer und Corpus Builder ohne Runtime, State, Output und
Test-Caches in isolierte Temp-Roots, nutzt weiter die echten Owner-Runtimes, und
ruft die MCP-Tools gegen echte `python -m <owner contract>` Subprozesse auf.
Damit werden Release-Bundles, initialisierte Corpus-DBs mit echten Rows,
Artifact-Rebuild-Dateien, Reset-/New-Corpus-Confirmations, Admin-State und
Secret-Audit end-to-end geprueft, ohne den echten Arbeits-State der Owner zu
beschreiben.

Marker:

- `integration`: echte Owner-Subprocess-Tests mit isolierten Modul-Roots.
- `gated`: reserviert fuer Tests, die externe Provider oder echte Credentials
  brauchen und explizit freigeschaltet werden muessen.
