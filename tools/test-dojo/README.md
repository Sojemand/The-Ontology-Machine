# Vision Pipeline Test Dojo

The Test Dojo is the planned root surface for production-near end-to-end, GUI,
contract, MCP and browser tests of The Ontology Machine pipeline.

Current status: skeleton. The entrypoint can list suites, validate suite
manifests and produce dry-run reports. Target architecture and acceptance
criteria live in `SPEC.md`.

## Entry

```bat
tools\run-test-dojo.bat list
tools\run-test-dojo.bat inspect --suite all
tools\run-test-dojo.bat run --suite orchestrator-ui
```

Reports are written under:

```text
.tmp/test-dojo/reports/<run_id>/
```
