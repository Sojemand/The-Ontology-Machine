import type { KernelMirrorEvent } from "../types/index.ts";

export function kernelAutoCallKey(mirrorEvent: KernelMirrorEvent | null | undefined): string {
  return String(mirrorEvent?.mirror_event_id || "");
}

export function shouldRenderKernelAutoCall(mirrorEvent: KernelMirrorEvent | null | undefined): boolean {
  if (!mirrorEvent?.is_kernel_auto_call) return false;
  const guidance = mirrorEvent.agent_explanation_guidance;
  if (typeof guidance === "string") return guidance.includes("explain_now");
  if (guidance && typeof guidance === "object") {
    const record = guidance as Record<string, unknown>;
    return record.response_mode === "explain_now" || record.mode === "explain_now";
  }
  return false;
}
