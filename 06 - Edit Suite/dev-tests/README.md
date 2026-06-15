# Edit Suite Dev Tests

- Bootstraps a suite-local `.venv` from `../runtime/python`.
- Installs `pytest` offline from `wheelhouse/`.
- Uses `python_path = [".."]` so module code imports directly from product
  source.
- Freezes the productive owner-contract state of `01 - Optimizer` under
  `fixtures/as_built/` as a migration reference.
- Checks runtime/installer preflight, live registry, owner bundles and failure
  classes such as corrupt cache, timeout and state path escape.

## Refresh As-Built Fixtures

After intentional contract changes in `01 - Optimizer`:

```bat
dev-tests\.venv\Scripts\python.exe dev-tests\tools\refresh_as_built_fixtures.py
```
