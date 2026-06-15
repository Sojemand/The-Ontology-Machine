const RECOVERY_TOOL_RETIREMENT_ERROR_CODES = new Set([
  "event_scope_missing",
  "event_scope_mismatch",
  "state_snapshot_mismatch",
  "superseded_mirror_event_tool_call"
]);

export function shouldRetireRecoveryTools(response) {
  const errorCode = String(response?.error?.code || "");
  const status = String(response?.status || "");
  return RECOVERY_TOOL_RETIREMENT_ERROR_CODES.has(errorCode) || status === "rejected";
}
