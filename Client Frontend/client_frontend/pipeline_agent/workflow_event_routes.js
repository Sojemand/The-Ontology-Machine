export function createKernelEventRoutes({
  ensureReady,
  buildCallContext,
  syncConversationScope,
  callKernelAdapter,
  autoEvents
}) {
  async function collectAutoResults(history, conversationRef) {
    return await autoEvents.collectPendingAutoCallResults(history, {
      conversationRef,
      turnRef: "kernel-auto-call"
    });
  }

  return {
    async listKernelEvents(cursor = "", { conversationRef = "", turnRef = "kernel-events", history = null } = {}) {
      await ensureReady();
      const callContext = buildCallContext({ conversationRef, turnRef });
      syncConversationScope(callContext);
      const batch = await callKernelAdapter("listKernelEvents", cursor, callContext);
      const nextHistory = await autoEvents.appendMirrorEvents(history);
      const autoCall = await collectAutoResults(nextHistory, conversationRef);
      return { batch, history: autoCall.history, autoResults: autoCall.autoResults };
    },

    async submitInteractionResponse(interactionRequestId, responsePayload, { conversationRef = "", history = null } = {}) {
      await ensureReady();
      const callContext = buildCallContext({ conversationRef, turnRef: "interaction-response" });
      syncConversationScope(callContext);
      const result = await callKernelAdapter("submitInteractionResponse", interactionRequestId, responsePayload, callContext);
      const nextHistory = await autoEvents.appendMirrorEvents(history);
      const autoCall = await collectAutoResults(nextHistory, conversationRef);
      return { ...result, history: autoCall.history, autoResults: autoCall.autoResults };
    },

    async cancelInteraction(interactionRequestId, responsePayload, { conversationRef = "", history = null } = {}) {
      await ensureReady();
      const callContext = buildCallContext({ conversationRef, turnRef: "interaction-cancel" });
      syncConversationScope(callContext);
      const result = await callKernelAdapter("cancelInteraction", interactionRequestId, responsePayload, callContext);
      const nextHistory = await autoEvents.appendMirrorEvents(history);
      const autoCall = await collectAutoResults(nextHistory, conversationRef);
      return { ...result, history: autoCall.history, autoResults: autoCall.autoResults };
    }
  };
}
