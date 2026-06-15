import { errorMessage, unavailableError } from "./errors.js";
import { resetKernelRuntimeState as runKernelRuntimeStateReset } from "./kernel_reset.js";
import { PIPELINE_ROOT_REQUIRED_MESSAGE } from "./prompt.js";
import { summarizeResetManifest, unavailableManagerStatus } from "./workflow_status.js";

export function createPipelineAdminRoutes({
  root,
  ensureReady,
  callKernelAdapter,
  buildCallContext,
  closeCurrentClient,
  resetBootState,
  setStartupError,
  getStartupError,
  getManagerStatusContext,
  fastStatus,
  toManagerStatus
}) {
  return {
    async resetKernelRuntimeState({ reason = "" } = {}) {
      if (!root) throw unavailableError(PIPELINE_ROOT_REQUIRED_MESSAGE);
      closeCurrentClient();
      resetBootState();
      const manifest = await runKernelRuntimeStateReset({
        pipelineRoot: root,
        reason: reason || "client frontend kernel reset"
      });
      void ensureReady().catch((error) => {
        setStartupError(errorMessage(error));
      });
      return summarizeResetManifest(manifest);
    },

    async status(options = {}) {
      if (options?.fast) return fastStatus();
      if (!root) return { available: false, reason: PIPELINE_ROOT_REQUIRED_MESSAGE, permission_status: null, permission_warning: "" };
      try {
        await ensureReady();
        const adapterStatus = await callKernelAdapter("status", buildCallContext({ turnRef: "pipeline-status" }));
        return toManagerStatus(adapterStatus);
      } catch (error) {
        return unavailableManagerStatus({
          ...getManagerStatusContext(),
          reason: getStartupError() || errorMessage(error)
        });
      }
    }
  };
}
