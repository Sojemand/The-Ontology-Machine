import type { KernelMirrorEvent } from "../types/index.ts";

const EVENT_SCOPED_RECOVERY_TOOL_NAMES = new Set([
  "kernel_apply_recovery_option",
  "kernel_open_recovery_dialog",
  "kernel_retry_recoverable_workflow",
  "kernel_resolve_stale_lock",
  "kernel_rebind_database_artifact_tree",
  "kernel_discard_or_archive_staged_work",
  "kernel_reconcile_partial_pipeline_run",
  "kernel_open_support_bundle"
]);

export function kernelMirrorAllowedAgentTools(mirrorEvent: KernelMirrorEvent | null | undefined): string[] {
  return Array.isArray(mirrorEvent?.allowed_agent_tools)
    ? mirrorEvent.allowed_agent_tools.map((name) => String(name))
    : [];
}

export function kernelMirrorSummary(mirrorEvent: KernelMirrorEvent | null | undefined): string {
  return String(
    mirrorEvent?.user_visible_summary
    || mirrorEvent?.user_visible_cause
    || mirrorEvent?.current_state_summary
    || ""
  ).trim();
}

export function isKernelExplainNow(mirrorEvent: KernelMirrorEvent | null | undefined): boolean {
  const guidance = mirrorEvent?.agent_explanation_guidance;
  if (typeof guidance === "string") return guidance.includes("explain_now");
  if (guidance && typeof guidance === "object") {
    const record = guidance as Record<string, unknown>;
    return record.response_mode === "explain_now" || record.mode === "explain_now";
  }
  return false;
}

export function isKernelRecoveryMirror(mirrorEvent: KernelMirrorEvent | null | undefined): boolean {
  return kernelMirrorAllowedAgentTools(mirrorEvent).some((name) => EVENT_SCOPED_RECOVERY_TOOL_NAMES.has(name))
    || Array.isArray(mirrorEvent?.recovery_options) && mirrorEvent.recovery_options.length > 0;
}

export function isKernelFinalErrorMirror(mirrorEvent: KernelMirrorEvent | null | undefined): boolean {
  return String(mirrorEvent?.severity || "") === "final_error";
}
