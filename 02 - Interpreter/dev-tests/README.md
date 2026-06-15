# Dev Tests

Lokale Dev-Test-Suite fuer `02 - Interpreter`.

Die Suite prueft den Shared-API-/OAuth-Providerpfad, die entfernten lokalen
Auth-Surfaces und den Runtime-/Packaging-Vertrag. Modul-lokale `.env`-Dateien
werden dabei nur als nicht-sensitive Runtime-Konfiguration behandelt; das
Mutable-Home folgt `%INTERPRETER_HOME%`, `%LOCALAPPDATA%\Enterprise Stack\Interpreter`
oder dem Quellslot-Fallback `.appdata\`.

```bat
bootstrap.bat
run-tests.bat
```
