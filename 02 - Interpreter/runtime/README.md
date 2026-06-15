# Interpreter Runtime

Portable module runtime for `02 - Interpreter`.

- `runtime/python` is the immutable core CPython runtime of the module.
- `runtime/runtime-manifest.json` describes the checkable core contract.
- `check-runtime.bat` validates portable Python provenance, the lockfile and
  required contract files.
- `tools/build-runtime.bat` updates the runtime only for development/packaging
  runs and validates it immediately afterward.
- The finalized runtime intentionally remains headless and ships no Tcl/Tk,
  no `Scripts/` and no `Lib/ensurepip/`.
- Per-user configuration lives under
  `%LOCALAPPDATA%\Enterprise Stack\Interpreter\config\.env` or
  `%INTERPRETER_HOME%\config\.env`. Without environment or Windows home, the
  source slot falls back to `.appdata\config\.env`.
