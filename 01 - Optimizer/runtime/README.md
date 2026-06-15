Portable module runtime for `01 - Optimizer`.

- `runtime/python` ist die immutable Core-CPython-Runtime des Moduls.
- `runtime/runtime-manifest.json` beschreibt den pruefbaren Core-Vertrag.
- `check-runtime.bat` validiert die portable Python-Provenance, das Lockfile, die erforderlichen Contract-Dateien und den Import des oeffentlichen Optimizer-Contracts inklusive File-Profil.
- `tools/build-runtime.bat` aktualisiert die Runtime nur fuer Dev-/Packaging-Laeufe und validiert danach sofort.
- Mutable Laufzeitdaten leben unter `%OPTIMIZER_HOME%` oder `%LOCALAPPDATA%\Enterprise Stack\Optimizer`.
- Fuer schlanke Installer-Layouts darf das Wheelhouse als `runtime/wheelhouse.zip` vorliegen; `runtime/wheelhouse/` ist kein Laufzeitvertrag.
