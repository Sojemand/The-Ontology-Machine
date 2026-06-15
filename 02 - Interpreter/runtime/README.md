Portable module runtime for `02 - Interpreter`.

- `runtime/python` ist die immutable Core-CPython-Runtime des Moduls.
- `runtime/runtime-manifest.json` beschreibt den pruefbaren Core-Vertrag.
- `check-runtime.bat` validiert die portable Python-Provenance, das Lockfile
  und die erforderlichen Contract-Dateien.
- `tools/build-runtime.bat` aktualisiert die Runtime nur fuer Dev-/Packaging-
  Laeufe und validiert danach sofort.
- Die finalisierte Runtime bleibt bewusst headless und shippt kein Tcl/Tk,
  kein `Scripts/` und kein `Lib/ensurepip/`.
- Per-user-Konfiguration lebt unter `%LOCALAPPDATA%\Enterprise Stack\Interpreter\config\.env`
  oder `%INTERPRETER_HOME%\config\.env`; ohne Env-/Windows-Home faellt der
  Quellslot auf `.appdata\config\.env` zurueck.
