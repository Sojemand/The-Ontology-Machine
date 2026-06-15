# Edit Suite Dev Tests

- bootstrappt eine suite-lokale `.venv` aus `../runtime/python`
- installiert `pytest` offline aus `wheelhouse/`
- nutzt `python_path = [".."]`, damit der Modulcode direkt aus der Produktquelle importiert wird
- friert den produktiven Owner-Contract-Stand von `01 - Optimizer` unter `fixtures/as_built/` als Migrationsreferenz ein
- prueft Runtime-/Installer-Preflight, Live-Registry, Owner-Bundles und Failure-Klassen wie korrupten Cache, Timeout und State-Pfad-Ausbruch

## As-Built Fixtures refreshen

Nach absichtlichen Contract-Aenderungen an `01 - Optimizer`:

```bat
dev-tests\.venv\Scripts\python.exe dev-tests\tools\refresh_as_built_fixtures.py
```
