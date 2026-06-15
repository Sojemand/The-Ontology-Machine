# Edit Suite Runtime

- `runtime/python`: gebuendelte CPython-Runtime
- `runtime/wheelhouse`: Offline-Quelle fuer Rebuilds
- `runtime/requirements.lock.txt`: reproduzierbare Runtime-Pins
- `runtime/runtime-manifest.json`: Runtime- und Provenance-Vertrag
- `run.bat`: fuehrt vor dem GUI-Start einen Runtime-Provenance-Preflight aus
- `EDIT_SUITE_OWNER_CONTRACT_TIMEOUT_SECONDS`: optionaler Override fuer owner-lokale Contract-Aufrufe, Standard `1800`
