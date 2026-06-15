# Phase 15 Legacy State Policy

- drift_preflight: build_plan_authority_applied
  - `SPEC_Semantic_Control_Kernel_Build.md` Phase 15 and the live MCP visibility API now agree on `tool_visibility(...)->legacy_hidden` for retired old-Kernel names. Phase 15 keeps the Phase 14 bridge contract stable and unlinks dependencies around it.

## Observed Legacy State

- Observed root path: `07 - MCP Server/state/semantic_kernel/`
- Observed child paths:
  - `events/`
  - `funnels/`
  - `locks/`
  - `sessions/`
  - `.store.lock`

## Phase 15 Handling

- Result: removed; legacy MCP Kernel state is no longer expected in this repository.
- No files were migrated into the Semantic Control Kernel module.
- No files were copied into a new archive location during Phase 15.
- Stale legacy locks, sessions, funnels or events are not active runtime truth.

## Runtime Truth Boundary

- `07 - MCP Server/state/semantic_kernel/` is not a supported runtime or historical fixture after the cleanup decision.
- Active Semantic Control Kernel state lives only under `08 - Semantic Control Kernel/state/`.
- MCP bridge code must not read the legacy state path to authorize, resume, block, unblock or recover Kernel workflows.

## Support-Only Use

- Support must use committed migration reports for cleanup evidence instead of relying on a mutable legacy state folder.
- No test or runtime path may require `07 - MCP Server/state/semantic_kernel/` to exist.
