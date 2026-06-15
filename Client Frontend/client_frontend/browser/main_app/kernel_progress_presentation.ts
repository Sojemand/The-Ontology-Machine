import type {
  KernelProgressEvent,
  KernelUiState
} from "./types.ts";
import type { KernelWorkflowRunSummary, PipelineRunState } from "../types/index.ts";
import { kernelMirrorSummary } from "./kernel_mirror_policy.ts";
import { pipelineStageRowsFromProgressEvent } from "./kernel_pipeline_stage_rows.ts";
import {
  isTerminalKernelProgressStatus,
  progressStatusText,
  progressTitle,
  progressVisualState
} from "./kernel_progress_status.ts";
export { isTerminalKernelProgressStatus } from "./kernel_progress_status.ts";

export interface KernelProgressPresentation {
  visible: boolean;
  title: string;
  summary: string;
  countText: string;
  meterPercent: number;
  state: string;
  rows: Array<{
    name: string;
    status: string;
    detail: string;
    state: string;
  }>;
  showAbort: boolean;
  abortRunId: string;
}

export function buildKernelProgressPresentation(
  kernelState: KernelUiState,
  fallbacks: {
    activeWorkflowRun?: KernelWorkflowRunSummary | null;
    activePipelineRun?: PipelineRunState | KernelWorkflowRunSummary | null;
    nowMs?: number;
  } = {}
): KernelProgressPresentation {
  const nowMs = Number(fallbacks.nowMs ?? Date.now());
  if (
    kernelState.latestProgressEvent
    && (
      !isTerminalKernelProgressStatus(kernelState.latestProgressEvent.status)
      || !kernelState.terminalProgressVisibleUntilMs
      || kernelState.terminalProgressVisibleUntilMs > nowMs
    )
  ) {
    return latestProgressPresentation(kernelState.latestProgressEvent, kernelState);
  }
  if (fallbacks.activeWorkflowRun && fallbacks.activeWorkflowRun.status && fallbacks.activeWorkflowRun.status !== "idle" && fallbacks.activeWorkflowRun.status !== "unavailable") {
    return runProgressPresentation(fallbacks.activeWorkflowRun, "Kernel workflow");
  }
  const fallbackRun = fallbacks.activePipelineRun;
  if (fallbackRun && fallbackRun.status && fallbackRun.status !== "idle" && fallbackRun.status !== "unavailable") {
    return runProgressPresentation(fallbackRun, "Pipeline status");
  }
  const activity = kernelState.localWorkflowActivity;
  if (activity && (!activity.expiresAtMs || activity.expiresAtMs > nowMs)) {
    return {
      visible: true,
      title: activity.title,
      summary: activity.summary,
      countText: "",
      meterPercent: 0,
      state: activity.state,
      rows: [{
        name: activity.workflowTool || "Kernel",
        status: activity.state === "waiting" ? "Waiting" : "Running",
        detail: activity.summary,
        state: activity.state
      }],
      showAbort: false,
      abortRunId: String(activity.workflowRunId || "")
    };
  }
  if (kernelState.activeRecoveryEvent) {
    return {
      visible: true,
      title: "Recovery required",
      summary: kernelMirrorSummary(kernelState.activeRecoveryEvent),
      countText: "",
      meterPercent: 0,
      state: "warning",
      rows: [],
      showAbort: false,
      abortRunId: String(kernelState.activeRecoveryEvent.workflow_run_id || "")
    };
  }
  return {
    visible: false,
    title: "",
    summary: "",
    countText: "",
    meterPercent: 0,
    state: "idle",
    rows: [],
    showAbort: false,
    abortRunId: ""
  };
}

function latestProgressPresentation(
  latest: KernelProgressEvent,
  kernelState: KernelUiState
): KernelProgressPresentation {
  const stageRows = pipelineStageRowsFromProgressEvent(latest);
  const rows = stageRows.length ? stageRows : kernelState.progressEvents
    .filter((event) => event.workflow_run_id === latest.workflow_run_id)
    .map((event) => ({
      name: String(event.step_label || event.step_id || "Kernel step"),
      status: progressStatusText(event.status),
      detail: String(event.user_visible_summary || event.current_state_summary || ""),
      state: progressVisualState(event.status)
    }));
  const completedCount = rows.filter((row) => row.state === "done").length;
  const totalSteps = Number(latest.total_steps || rows.length || 0);
  const currentOrdinal = Number(latest.ordinal || completedCount || 0);
  const countText = totalSteps > 0 ? `${Math.min(currentOrdinal, totalSteps)}/${totalSteps}` : rows.length ? `${rows.length}` : "";
  const meterPercent = totalSteps > 0 ? Math.max(0, Math.min(100, Math.round((Math.min(currentOrdinal, totalSteps) / totalSteps) * 100))) : completedCount ? 100 : 0;
  return {
    visible: true,
    title: progressTitle(latest.status),
    summary: String(latest.user_visible_summary || latest.current_state_summary || ""),
    countText,
    meterPercent,
    state: progressVisualState(latest.status),
    rows,
    showAbort: !isTerminalKernelProgressStatus(latest.status),
    abortRunId: String(latest.workflow_run_id || "")
  };
}

function runProgressPresentation(
  run: PipelineRunState | KernelWorkflowRunSummary,
  title: string
): KernelProgressPresentation {
  const raw = run as PipelineRunState & KernelWorkflowRunSummary;
  const status = String(raw.status || "");
  const stepLabel = String(raw.step_label || raw.step_id || "");
  const summary = String(raw.user_visible_summary || raw.message || status);
  return {
    visible: true,
    title,
    summary,
    countText: "",
    meterPercent: 0,
    state: progressVisualState(status),
    rows: stepLabel ? [{
      name: stepLabel,
      status: progressStatusText(status),
      detail: summary,
      state: progressVisualState(status)
    }] : [],
    showAbort: status === "running" || status === "running_unknown" || status === "step_started" || status === "retrying",
    abortRunId: String(raw.run_id || raw.workflow_run_id || "")
  };
}
