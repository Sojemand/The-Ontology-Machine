import { MAIN_APP_TEXT } from "./policy.ts";
import { createInitialKernelUiState } from "./state_domain.ts";
import { applyKernelEventBatchToState } from "./kernel_event_policy.ts";
import { createKernelDialogController } from "./workflow_kernel_dialog_controller.ts";
import { createKernelHealthController } from "./workflow_kernel_health_controller.ts";
import {
  pruneExpiredLocalWorkflowActivity,
  reconcileLocalWorkflowActivityWithRealKernelState,
  startLocalWorkflowActivity,
} from "./workflow_kernel_state.ts";
import type { AppState, ChatAgentType, MainApi } from "./types.ts";
import type { KernelAutoChatResult } from "../types/pipeline.ts";
import type { LayoutDebugController } from "./debug.ts";
import type { MainDomAdapter } from "./dom_adapter.ts";
import type { LayoutWorkflow } from "./layout_workflow.ts";

interface KernelWorkflowControllerDeps {
  api: MainApi;
  state: AppState;
  domAdapter: MainDomAdapter;
  layoutWorkflow: LayoutWorkflow;
  debug: LayoutDebugController;
  windowObject: Window;
  updateTurnCounter: () => void;
  appendPipelineAutoResults: (results: KernelAutoChatResult[]) => Promise<void>;
}

export function createKernelWorkflowController({
  api,
  state,
  domAdapter,
  layoutWorkflow,
  debug,
  windowObject,
  updateTurnCounter,
  appendPipelineAutoResults
}: KernelWorkflowControllerDeps) {
  let kernelResetInFlight = false;
  let kernelRefreshInFlight = false;
  const dialog = createKernelDialogController({
    api,
    state,
    domAdapter,
    beginKernelInteractionPending,
    clearLocalInteractionPendingState,
    renderUi,
    refreshRuntimeStatus,
    appendPipelineAutoResults
  });
  const health = createKernelHealthController({
    api,
    state,
    domAdapter,
    layoutWorkflow,
    debug,
    updateTurnCounter,
    renderChrome
  });

  function clearLocalInteractionPendingState(): void {
    state.kernelUi.pendingInteraction = null;
    state.kernelUi.localWorkflowActivity = null;
  }

  function beginKernelInteractionPending(request: NonNullable<NonNullable<AppState["kernelUi"]["activeDialog"]>["interaction_request"]>, actionLabel: string): boolean {
    const requestId = String(request.interaction_request_id || "");
    if (!requestId || state.kernelUi.pendingInteraction?.requestId === requestId) return false;
    const statusText = "Input sent. Kernel is processing the next step...";
    state.kernelUi.pendingInteraction = { requestId, actionLabel, statusText, submittedAt: new Date().toISOString() };
    startLocalWorkflowActivity(state, {
      activityId: `interaction:${requestId}`,
      title: "Kernel is processing input",
      summary: statusText,
      workflowRunId: request.workflow_run_id,
      workflowTool: request.function_or_route
    });
    renderUi();
    return true;
  }

  function beginPipelineChatHandoff(message: string): void {
    if (state.activeAgentType !== "pipeline") return;
    startLocalWorkflowActivity(state, {
      activityId: `pipeline-chat:${Date.now()}`,
      title: "Taxonomy Agent is processing the request",
      summary: message.trim() ? "Request sent. Kernel workflow is being prepared..." : "Kernel workflow is being prepared..."
    });
    renderChrome();
    debug.render(state);
  }

  function renderChrome(): void {
    reconcileLocalWorkflowActivityWithRealKernelState(state);
    domAdapter.setKernelResetButtonState(
      state.activeAgentType === "pipeline",
      !state.health?.pipeline_manager?.available,
      kernelResetInFlight
    );
    domAdapter.renderPipelinePermission(state.health, state.activeAgentType, state.kernelUi);
    domAdapter.renderPipelineProgress(state.health, state.activeAgentType, state.kernelUi);
  }

  function renderUi(): void {
    renderChrome();
    dialog.renderDialog();
    debug.render(state);
  }

  async function refreshKernelEvents(): Promise<void> {
    if (kernelRefreshInFlight) return;
    if (!state.health?.pipeline_manager?.available) {
      renderUi();
      return;
    }
    kernelRefreshInFlight = true;
    try {
      const batch = await api.getPipelineKernelEvents(state.kernelUi.cursor);
      state.kernelUi = applyKernelEventBatchToState(state.kernelUi, batch);
      reconcileLocalWorkflowActivityWithRealKernelState(state);
      if (Array.isArray(batch.auto_results) && batch.auto_results.length) await appendPipelineAutoResults(batch.auto_results);
      renderUi();
    } catch (error) {
      if (state.activeAgentType === "pipeline") {
        domAdapter.setChatStatus(error instanceof Error ? error.message : "Kernel event polling failed.");
      }
    } finally {
      kernelRefreshInFlight = false;
    }
  }

  async function refreshRuntimeStatus(): Promise<void> {
    await health.refreshHealth();
    await refreshKernelEvents();
  }

  async function cancelPipelineRun(): Promise<void> {
    if (state.activeAgentType !== "pipeline") return;
    const run = state.health?.pipeline_manager?.active_pipeline_run;
    const runId = typeof run?.run_id === "string" ? run.run_id : "";
    domAdapter.setPipelineAbortPending(true);
    try {
      const result = await api.cancelPipelineRun(runId);
      domAdapter.setChatStatus(result.message || "Kernel cancellation requested.");
      await refreshRuntimeStatus();
    } catch (error) {
      domAdapter.setChatStatus(error instanceof Error ? error.message : "Kernel cancellation failed.");
    } finally {
      domAdapter.setPipelineAbortPending(false);
    }
  }

  async function resetKernelRuntimeState(): Promise<void> {
    if (state.activeAgentType !== "pipeline" || kernelResetInFlight) return;
    if (!state.health?.pipeline_manager?.available) {
      domAdapter.setChatStatus(state.health?.pipeline_manager?.reason || MAIN_APP_TEXT.pipelineRootRequired);
      return;
    }
    const confirmed = windowObject.confirm("Reset Kernel Runtime State?\n\nActive Kernel runs, open dialogs, and recovery availability will be archived and removed from the active state.");
    if (!confirmed) return;
    kernelResetInFlight = true;
    renderUi();
    domAdapter.setChatStatus("Kernel Reset running...", true);
    try {
      const result = await api.resetKernelRuntimeState();
      state.kernelUi = createInitialKernelUiState();
      renderUi();
      domAdapter.setChatStatus(result.message || "Kernel Runtime State was reset.");
      await refreshRuntimeStatus();
    } catch (error) {
      domAdapter.setChatStatus(error instanceof Error ? error.message : "Kernel Reset failed.");
    } finally {
      kernelResetInFlight = false;
      renderUi();
    }
  }

  return {
    beginPipelineChatHandoff,
    cancelPipelineRun,
    handlePipelineSubmitSettled(): void {
      pruneExpiredLocalWorkflowActivity(state);
      renderChrome();
    },
    refreshHealth: health.refreshHealth,
    refreshKernelEvents,
    refreshRuntimeStatus,
    renderUi,
    resetKernelRuntimeState,
    setAgentSwitchStatus: health.setAgentSwitchStatus
  };
}
