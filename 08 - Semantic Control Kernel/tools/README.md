# Tools

Reserved for module-local development and verification helpers.

Helpers in this folder must not become hidden product entry points. Any helper
that affects runtime, state, contract actions or generated artifacts must be
documented in the README, manifest or build spec.

Visible operator helpers:

- `visible_logged_runner.py` mirrors a child command's stdout/stderr both into
  the current console and into explicit log files.
- `run_go_live_bundle_visible.cmd` starts `generate_go_live_bundle.py` with a
  visible console while still writing persistent stdout/stderr logs under
  `.tmp/` by default.
- `generate_go_live_bundle.py` is the path-stable CLI facade; implementation
  responsibilities live under `tools/go_live_bundle/`.
