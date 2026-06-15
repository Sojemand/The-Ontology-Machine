export interface PendingChatRequest {
  requestId: number;
  conversationVersion: number;
}

export function createChatController() {
  let conversationVersion = 0;
  let nextRequestId = 1;
  let pendingRequest: PendingChatRequest | null = null;

  return {
    beginSend() {
      const request = {
        requestId: nextRequestId++,
        conversationVersion
      };
      pendingRequest = request;
      return request;
    },
    resetConversation() {
      conversationVersion += 1;
      pendingRequest = null;
      return conversationVersion;
    },
    canApplyResponse(request: PendingChatRequest | null | undefined) {
      return Boolean(
        request &&
          pendingRequest &&
          request.requestId === pendingRequest.requestId &&
          request.conversationVersion === conversationVersion
      );
    },
    finishSend(request: PendingChatRequest | null | undefined) {
      if (pendingRequest && request && pendingRequest.requestId === request.requestId) {
        pendingRequest = null;
      }
    },
    isSending() {
      return pendingRequest != null;
    }
  };
}
