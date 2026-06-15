import { buildCallContext } from "./workflow_call_context.js";

export function createWorkflowPublicApi({
  ensureReady,
  chat,
  eventRoutes,
  adminRoutes,
  callKernelAdapter,
  fastStatus,
  closeCurrentClient
}) {
  return {
    initialize: () => ensureReady().catch(() => false),
    chat,
    listKernelEvents: eventRoutes.listKernelEvents,
    submitInteractionResponse: eventRoutes.submitInteractionResponse,
    cancelInteraction: eventRoutes.cancelInteraction,
    async cancelActiveRun() {
      await ensureReady();
      return await callKernelAdapter("cancelActiveRun", buildCallContext({ turnRef: "cancel-active-run" }));
    },
    resetKernelRuntimeState: adminRoutes.resetKernelRuntimeState,
    status: adminRoutes.status,
    healthStatus() {
      return fastStatus();
    },
    close() {
      closeCurrentClient();
    }
  };
}
