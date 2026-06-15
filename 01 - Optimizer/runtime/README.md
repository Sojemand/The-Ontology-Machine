# Optimizer Runtime

Portable module runtime for `01 - Optimizer`.

- `runtime/python` is the immutable core CPython runtime of the module.
- `runtime/runtime-manifest.json` describes the checkable core contract.
- `check-runtime.bat` validates portable Python provenance, the lockfile,
  required contract files and import of the public Optimizer contract including
  the file profile.
- `tools/build-runtime.bat` updates the runtime only for development/packaging
  runs and validates it immediately afterward.
- Mutable runtime data lives under `%OPTIMIZER_HOME%` or
  `%LOCALAPPDATA%\Enterprise Stack\Optimizer`.
- Slim installer layouts may ship the wheelhouse as `runtime/wheelhouse.zip`;
  `runtime/wheelhouse/` is not a runtime contract.
