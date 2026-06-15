import type { AppState, ConversationViewState } from "./types.ts";

export function cloneConversationView(view: ConversationViewState): ConversationViewState {
  return {
    messages: view.messages.map((message) => ({
      ...message,
      sources: message.sources ? [...message.sources] : undefined,
      token_usage: message.token_usage ? { ...message.token_usage } : undefined
    })),
    sources: [...view.sources],
    viewer: { ...view.viewer }
  };
}

export function cloneAppState(state: AppState): AppState {
  return {
    ...state,
    messages: state.messages.map((message) => ({
      ...message,
      sources: message.sources ? [...message.sources] : undefined,
      token_usage: message.token_usage ? { ...message.token_usage } : undefined
    })),
    sources: [...state.sources],
    viewer: { ...state.viewer },
    kernelUi: {
      ...state.kernelUi,
      activeDialog: state.kernelUi.activeDialog
        ? {
            ...state.kernelUi.activeDialog,
            interaction_request: state.kernelUi.activeDialog.interaction_request
              ? { ...state.kernelUi.activeDialog.interaction_request }
              : null
          }
        : null,
      activeRecoveryEvent: state.kernelUi.activeRecoveryEvent ? { ...state.kernelUi.activeRecoveryEvent } : null,
      latestMirrorEvent: state.kernelUi.latestMirrorEvent ? { ...state.kernelUi.latestMirrorEvent } : null,
      latestProgressEvent: state.kernelUi.latestProgressEvent ? { ...state.kernelUi.latestProgressEvent } : null,
      progressEvents: state.kernelUi.progressEvents.map((event) => ({ ...event })),
      pendingInteraction: state.kernelUi.pendingInteraction ? { ...state.kernelUi.pendingInteraction } : null,
      localWorkflowActivity: state.kernelUi.localWorkflowActivity ? { ...state.kernelUi.localWorkflowActivity } : null
    },
    agentViews: {
      query: cloneConversationView(state.agentViews.query),
      pipeline: cloneConversationView(state.agentViews.pipeline),
      ontology: cloneConversationView(state.agentViews.ontology)
    },
    layout: { ...state.layout }
  };
}
