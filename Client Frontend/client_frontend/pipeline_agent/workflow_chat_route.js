import { filterKernelHistoryForActiveState } from "./context_policy.js";
import { runPipelineAgentChat } from "./chat_workflow.js";

export function createPipelineChatRoute({
  root,
  getKernelAdapter,
  ensureReady,
  buildCallContext,
  syncConversationScope,
  callKernelAdapter,
  callKernelToolFromModel,
  toManagerStatus,
  getRuntimeConfig,
  getFrontendPolicy,
  createChatCompletionFn,
  autoEvents
}) {
  return async function chat({ message, history = [], ownerId = "" }) {
    await ensureReady();
    const callContext = buildCallContext({
      conversationRef: ownerId || "pipeline-session",
      turnRef: "chat-turn"
    });
    syncConversationScope(callContext);
    const adapterStatus = await callKernelAdapter("status", callContext);
    await callKernelAdapter("prepareEventScopedTools", callContext);
    const historyForModel = filterKernelHistoryForActiveState(history, adapterStatus.kernel_status || {});
    const kernelAdapter = getKernelAdapter();
    const result = await runPipelineAgentChat({
      message,
      history: historyForModel,
      root,
      toolDefinitions: kernelAdapter.toolDefinitions(),
      availabilityStatus: toManagerStatus(adapterStatus),
      getRuntimeConfig,
      getFrontendPolicy,
      createChatCompletionFn,
      callKernelToolFromModel: (toolName, args) => callKernelToolFromModel(toolName, args, callContext)
    });
    result.history = await autoEvents.appendMirrorEvents(result.history);
    return result;
  };
}
