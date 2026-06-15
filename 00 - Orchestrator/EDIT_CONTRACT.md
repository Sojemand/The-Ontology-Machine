# Orchestrator Edit Contract

- Entry-Point: `python -m orchestrator.edit_contract --request <request.json> --response <response.json>`
- Produkt-Contract und `module-manifest.json` bleiben unveraendert; `read_bundle` ist nur eine additive Owner-Action fuer `06 - Edit Suite`
- Sichtbare Actions:
  - `describe_surfaces`
  - `read_bundle`
  - `read_surface`
  - `validate_surface`
  - `write_surface`
- Sichtbare Surfaces:
  - `orchestrator.route_intake_policy`
  - `orchestrator.execution_policy`
  - `orchestrator.health_dependency_policy`
  - `orchestrator.artifact_publication_policy`
- `read_bundle` liefert dieselben Descriptoren wie `describe_surfaces` plus inline `value` oder per-surface `load_error`
- `summary_cards` und `module_summary` bleiben im bestehenden `{"status": "ok", ...}`-Envelope sichtbar
