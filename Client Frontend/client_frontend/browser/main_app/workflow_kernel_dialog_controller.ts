import { MAIN_APP_DEFAULTS } from "./policy.ts";
import { buildKernelCancelPayload, buildKernelInteractionResponsePayload, applyKernelEventBatchToState, applyKernelInteractionResponseToState } from "./kernel_event_policy.ts";
import { reconcileLocalWorkflowActivityWithRealKernelState } from "./workflow_kernel_state.ts";
import type { AppState, MainApi } from "./types.ts";
import type { KernelAutoChatResult } from "../types/pipeline.ts";
import type { MainDomAdapter } from "./dom_adapter.ts";

interface KernelDialogControllerDeps {
  api: MainApi;
  state: AppState;
  domAdapter: MainDomAdapter;
  beginKernelInteractionPending: (
    request: NonNullable<NonNullable<AppState["kernelUi"]["activeDialog"]>["interaction_request"]>,
    actionLabel: string
  ) => boolean;
  clearLocalInteractionPendingState: () => void;
  renderUi: () => void;
  refreshRuntimeStatus: () => Promise<void>;
  appendPipelineAutoResults: (results: KernelAutoChatResult[]) => Promise<void>;
}

export function createKernelDialogController({
  api,
  state,
  domAdapter,
  beginKernelInteractionPending,
  clearLocalInteractionPendingState,
  renderUi,
  refreshRuntimeStatus,
  appendPipelineAutoResults
}: KernelDialogControllerDeps) {
  async function applyRouteResult(
    result: Awaited<ReturnType<MainApi["submitKernelInteractionResponse"]>>
  ): Promise<void> {
    state.kernelUi = applyKernelInteractionResponseToState(state.kernelUi, result.bridge_response);
    state.kernelUi = applyKernelEventBatchToState(state.kernelUi, result.event_batch);
    reconcileLocalWorkflowActivityWithRealKernelState(state);
    if (Array.isArray(result.auto_results) && result.auto_results.length) await appendPipelineAutoResults(result.auto_results);
    renderUi();
    domAdapter.setChatStatus(result.bridge_response.user_visible_summary || MAIN_APP_DEFAULTS.readyStatus);
    await refreshRuntimeStatus();
  }

  async function submitDialogPayload(valuePayload: Record<string, unknown>, actionLabel = "Submit"): Promise<void> {
    const request = state.kernelUi.activeDialog?.interaction_request;
    if (!request || !beginKernelInteractionPending(request, actionLabel)) return;
    try {
      const payload = buildKernelInteractionResponsePayload(request, valuePayload);
      await applyRouteResult(await api.submitKernelInteractionResponse(request.interaction_request_id, payload));
    } catch (error) {
      clearLocalInteractionPendingState();
      renderUi();
      domAdapter.setChatStatus(error instanceof Error ? error.message : "Kernel dialog submission failed.");
    }
  }

  async function cancelDialog(responseStatus: "cancelled" | "closed" | "expired", cancellationReason: string, actionLabel = "Cancel"): Promise<void> {
    const request = state.kernelUi.activeDialog?.interaction_request;
    if (!request || !beginKernelInteractionPending(request, actionLabel)) return;
    try {
      const payload = buildKernelCancelPayload(request, responseStatus, cancellationReason);
      await applyRouteResult(await api.cancelKernelInteraction(request.interaction_request_id, payload));
    } catch (error) {
      clearLocalInteractionPendingState();
      renderUi();
      domAdapter.setChatStatus(error instanceof Error ? error.message : "Kernel dialog cancellation failed.");
    }
  }

  function renderDialog(): void {
    domAdapter.renderKernelDialog(state.kernelUi.activeDialog, state.kernelUi.dialogStatusText, state.kernelUi.pendingInteraction, {
      onSubmit: (payload, actionLabel) => {
        void submitDialogPayload(payload, actionLabel);
      },
      onCancel: (payload, actionLabel) => {
        void cancelDialog(payload.response_status, payload.cancellation_reason, actionLabel);
      }
    });
  }

  return {
    renderDialog
  };
}
