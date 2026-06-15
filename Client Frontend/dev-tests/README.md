# Dev Tests

Gekapselte Node-Test-Suite fuer das Client Frontend.

- Oeffentliche Test-Seams bleiben `src/*`, `src/main_app/*`, `src/ui/render.ts`, `server/*`, `server/chat_store/surface.js` sowie `client_frontend/runtime_paths.js` und `client_frontend/runtime_paths/*`.
- Die eigentliche Implementierung liegt unter `client_frontend/`; Tests duerfen die pfadstabilen Wrapper und die explizit dokumentierten Runtime-Pfad-Seams weiter direkt importieren.
- Die Suite ist nach Verhaltensclustern organisiert:
  - Browser-App und Render-Surfaces
  - Config- und Provider-Contract-Surfaces
  - HTTP-, Security- und Session-Workflows
  - Memory- und Minimal-Agent-Regressionspfade
  - Runtime-, Deploy- und Installer-Vertrag
