import type { PendingChatRequest } from "../chat_controller.ts";
import type { Source } from "../types/index.ts";
import {
  collectSourceCatalog,
  createAssistantMessage,
  getReferencedSources
} from "./state_domain.ts";
import type { AppState, ChatAgentType, ChatController, ConversationMutation, MainApi } from "./types.ts";

const AUTOMATED_PIPELINE_STATUS = "Taxonomy Agent is checking the completed run...";

type AppendMessageForAgent = (agent: ChatAgentType, message: AppState["messages"][number]) => boolean;

interface PipelineConversationDeps {
  api: MainApi;
  state: AppState;
  chatController: ChatController;
  renderMessages: () => void;
  applyDisplayedSources: (sources: Source[]) => void;
  refreshKernelEvents?: () => Promise<void>;
  refreshHistoryList: () => Promise<void>;
  appendMessageForAgent: AppendMessageForAgent;
  setSendingState: (sending: boolean) => void;
  setStatus: (text: string, spinning?: boolean) => void;
  getActiveConversationMutation: () => ConversationMutation;
  chatErrorMessage: (error: unknown) => string;
  chatErrorStatus: (error: unknown) => string;
  noReferencedSourcesText: string;
  noNewSourcesText: string;
  referencedSourcesText: (count: number) => string;
}

export function createPipelineConversationActions(deps: PipelineConversationDeps) {
  const appendPipelineAutoResults = async (results: Array<{
    answer?: string;
    sources?: any[];
    mode?: "exact" | "lookup" | "analytic";
    exactness?: "exact" | "evidence_grounded" | "ambiguous" | "insufficient_evidence";
    metrics?: AppState["messages"][number]["metrics"];
    ambiguities?: AppState["messages"][number]["ambiguities"];
    method?: string;
  }> = []): Promise<void> => {
    let rendered = false;
    for (const result of Array.isArray(results) ? results : []) {
      const assistantMessage = createAssistantMessage({
        answer: String(result?.answer || ""),
        sources: Array.isArray(result?.sources) ? result.sources : [],
        mode: result?.mode,
        exactness: result?.exactness,
        metrics: result?.metrics,
        ambiguities: result?.ambiguities,
        method: result?.method
      });
      if (!assistantMessage.content) continue;
      rendered = deps.appendMessageForAgent("pipeline", assistantMessage) || rendered;
    }
    if (!rendered) return;
    deps.renderMessages();
    void deps.refreshHistoryList();
  };

  const submitAutomatedPipelineMessage = async (message: string): Promise<boolean> => {
    const trimmedMessage = message.trim();
    if (!trimmedMessage || deps.state.sending || deps.getActiveConversationMutation() !== null) return false;
    const pendingRequest: PendingChatRequest = deps.chatController.beginSend();
    const visible = deps.state.activeAgentType === "pipeline";
    deps.setSendingState(true);
    if (visible) deps.setStatus(AUTOMATED_PIPELINE_STATUS, true);
    if (deps.appendMessageForAgent("pipeline", { role: "user", content: trimmedMessage })) deps.renderMessages();
    try {
      const response = await deps.api.sendChat(trimmedMessage, "pipeline");
      if (!deps.chatController.canApplyResponse(pendingRequest)) return true;
      const assistantMessage = createAssistantMessage(response);
      const responseVisible = deps.appendMessageForAgent("pipeline", assistantMessage);
      if (responseVisible) await applyVisiblePipelineResponse(deps, assistantMessage, response.sources);
    } catch (error) {
      if (!deps.chatController.canApplyResponse(pendingRequest)) return true;
      const errorVisible = deps.appendMessageForAgent("pipeline", { role: "system", content: deps.chatErrorMessage(error) });
      if (errorVisible) {
        deps.renderMessages();
        deps.setStatus(deps.chatErrorStatus(error));
      }
    } finally {
      deps.chatController.finishSend(pendingRequest);
      deps.setSendingState(deps.chatController.isSending());
    }
    return true;
  };

  return { appendPipelineAutoResults, submitAutomatedPipelineMessage };
}

async function applyVisiblePipelineResponse(
  deps: PipelineConversationDeps,
  assistantMessage: AppState["messages"][number],
  responseSources: Source[]
): Promise<void> {
  deps.renderMessages();
  if (deps.refreshKernelEvents) await deps.refreshKernelEvents();
  void deps.refreshHistoryList();
  const referencedSources = getReferencedSources(assistantMessage, collectSourceCatalog(deps.state.messages));
  if (referencedSources.length) {
    deps.applyDisplayedSources(referencedSources);
    deps.setStatus(deps.referencedSourcesText(referencedSources.length));
    return;
  }
  deps.applyDisplayedSources([]);
  deps.setStatus(responseSources.length ? deps.noReferencedSourcesText : deps.noNewSourcesText);
}
