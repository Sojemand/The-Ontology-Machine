export const MAX_TOOL_ROUNDS = 16;
export const PIPELINE_RESPONSE_RESERVE_TOKENS = 12_000;

export const PIPELINE_HISTORY_TOKEN_CAP = 24_000;
export const PIPELINE_TOOL_RESULT_CHAR_LIMIT = 24_000;
export const PIPELINE_HISTORY_ENTRY_CHAR_LIMIT = 12_000;
export const KERNEL_HISTORY_PREFIX = "Kernel mirror event. This is Kernel state, not a user message.";

export const TERMINAL_PROGRESS_STATUSES = new Set(["completed", "cancelled", "failed"]);
export const TERMINAL_KERNEL_MIRROR_EVENT_TYPES = new Set(["workflow_completed", "workflow_cancelled", "workflow_failed"]);
export const TRANSIENT_KERNEL_MIRROR_EVENT_TYPES = new Set([
  "progress",
  "input_dialog_opened",
  "selection_dialog_opened",
  "confirmation_dialog_opened"
]);

export const USER_VISIBLE_RESULT_FIELDS = new Set([
  "schema_version",
  "status",
  "tool_name",
  "effect",
  "workflow_run_id",
  "user_visible_summary",
  "resume_state",
  "active_state",
  "cancel_status",
  "error",
  "reason",
  "implemented_by_phase"
]);
