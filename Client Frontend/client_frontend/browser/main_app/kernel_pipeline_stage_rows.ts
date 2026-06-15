import type { KernelProgressEvent } from "./types.ts";
import type { KernelProgressPresentation } from "./kernel_progress_presentation.ts";

export function pipelineStageRowsFromProgressEvent(event: KernelProgressEvent): KernelProgressPresentation["rows"] {
  const refs = Array.isArray(event.artifact_refs) ? event.artifact_refs : [];
  for (const ref of refs) {
    if (!ref || typeof ref !== "object") continue;
    const payload = ref as { kind?: unknown; stages?: unknown };
    if (String(payload.kind || "") !== "orchestrator_stage_statuses" || !Array.isArray(payload.stages)) continue;
    return payload.stages
      .map((stage) => pipelineStageRow(stage))
      .filter((row) => row.name);
  }
  return [];
}

function pipelineStageRow(stage: unknown): KernelProgressPresentation["rows"][number] {
  const payload = stage && typeof stage === "object" ? stage as Record<string, unknown> : {};
  const name = String(payload.name || "Pipeline module").trim();
  const rawStatus = String(payload.status || "").trim();
  const rawCurrent = Number(payload.progress_current || 0);
  const rawTotal = Number(payload.progress_total || 0);
  const current = Number.isFinite(rawCurrent) ? rawCurrent : 0;
  const total = Number.isFinite(rawTotal) ? rawTotal : 0;
  const progressLabel = String(payload.progress_label || "").trim();
  const progress = Number.isFinite(total) && total > 0
    ? `${Math.max(0, current)}/${total}${progressLabel ? ` ${progressLabel}` : ""}`
    : "";
  const detail = [String(payload.detail || "").trim(), progress].filter(Boolean).join(" | ");
  return {
    name,
    status: rawStatus || "Ready",
    detail,
    state: pipelineStageVisualState(rawStatus, current, total)
  };
}

function pipelineStageVisualState(status: string, current: number, total: number): string {
  const key = String(status || "").trim().toLowerCase();
  if (key.includes("fehler") || key.includes("error") || key.includes("fail") || key.includes("abgebrochen")) {
    return "error";
  }
  if (key.includes("warn") || key.includes("review")) {
    return "warning";
  }
  if (key.includes("verarbeite") || key.includes("running") || key.includes("started") || key.includes("retry")) {
    return "running";
  }
  if (key === "fertig" || key === "done" || key === "completed" || key === "complete") {
    return "done";
  }
  if (Number.isFinite(total) && total > 0 && Number.isFinite(current) && current > 0 && current < total) {
    return "running";
  }
  return "idle";
}
