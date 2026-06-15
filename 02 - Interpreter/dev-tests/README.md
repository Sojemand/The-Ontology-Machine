# Dev Tests

Local development test suite for `02 - Interpreter`.

The suite checks the shared API/OAuth provider path, the removed local auth
surfaces and the runtime/packaging contract. Module-local `.env` files are
treated only as non-sensitive runtime configuration. Mutable home follows
`%INTERPRETER_HOME%`, `%LOCALAPPDATA%\Enterprise Stack\Interpreter` or the
source-slot fallback `.appdata\`.

```bat
bootstrap.bat
run-tests.bat
```
