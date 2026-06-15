# MCP Server Dev Tests

Local Python suite for the tool catalog, MCP framing and fail-closed governance
of the module.

`tests/test_tool_contract_matrix.py` is the complete MCP handler matrix. It
requires a golden path for every visible tool at the MCP layer, uses real
temporary files for databases, Semantic Release bundles, confirmation
artifacts and Artifact folders, and checks regressions for allowlists, required
fields, types, path boundaries and visible owner orchestration.

Owner calls are controlled replacements in this layer so tests do not write
foreign module state or touch real secrets. New catalog tools must appear there
explicitly as golden paths. The matrix keeps Normalizer steps separate:
reading, planning/review, writing, validating, compiling, exporting and
activating must not silently collapse into one generic L2 tool.

Real owner subprocess integration belongs in a separate layer. It may run only
through owner-safe read paths or temp-file paths. Mutating actions such as
workspace-local Working Release authoring, Corpus reset, credential admin,
secret reveal or L3 source-debug escape hatches must either use module-local
temp roots or remain in the respective owner module.

`tests/test_tool_subprocess_integration.py` is this L2 layer. It copies
Orchestrator, Normalizer and Corpus Builder without runtime, state, output and
test caches into isolated temp roots, keeps using the real owner runtimes, and
calls MCP tools against real `python -m <owner contract>` subprocesses. This
checks release bundles, initialized Corpus DBs with real rows, artifact rebuild
files, reset/new-corpus confirmations, admin state and secret audit end to end
without writing into the real owner work state.

Markers:

- `integration`: real owner subprocess tests with isolated module roots.
- `gated`: reserved for tests that need external providers or real credentials
  and must be enabled explicitly.
