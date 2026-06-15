# Dev Tests

Encapsulated Node test suite for the Client Frontend.

- Public test seams remain `src/*`, `src/main_app/*`, `src/ui/render.ts`,
  `server/*`, `server/chat_store/surface.js`,
  `client_frontend/runtime_paths.js` and `client_frontend/runtime_paths/*`.
- The actual implementation lives under `client_frontend/`; tests may keep
  importing the path-stable wrappers and explicitly documented runtime-path
  seams directly.
- The suite is organized by behavior clusters:
  - Browser app and render surfaces
  - Config and provider contract surfaces
  - HTTP, security and session workflows
  - Memory and Minimal Agent regression paths
  - Runtime, deploy and installer contract
