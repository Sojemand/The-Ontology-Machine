import type {
  ChatHistoryResponse,
  ChatResponse,
  ChatRestoreResponse,
  ConfigResponse,
  ConnectionTestResponse,
  HealthResponse,
  KernelClientFrontendEventBatch,
  KernelInteractionRouteResponse,
  KernelRuntimeResetResponse,
  KernelUserInteractionResponse,
  ModelsResponse,
  PipelineRunCancelResponse
} from "../types/index.ts";

import { routeForAgent, type ChatAgentType } from "./agent_routes.ts";
import { requestWithFetch, type FetchLike } from "./transport.ts";

export function createApiClient(fetchImpl: FetchLike = fetch) {
  return {
    getHealth(): Promise<HealthResponse> {
      return requestWithFetch<HealthResponse>(fetchImpl, "/api/v2/health", { cache: "no-store" });
    },

    sendChat(message: string, agent?: ChatAgentType): Promise<ChatResponse> {
      return requestWithFetch<ChatResponse>(fetchImpl, routeForAgent(agent, { query: "/api/v2/chat", pipeline: "/api/v2/pipeline-manager/chat", ontology: "/api/v2/ontology-agent/chat" }), {
        method: "POST",
        body: JSON.stringify({ message })
      });
    },

    getCurrentConfig(): Promise<ConfigResponse> {
      return requestWithFetch<ConfigResponse>(fetchImpl, "/config/api/current");
    },

    getModels(params: Record<string, string>): Promise<ModelsResponse> {
      return requestWithFetch<ModelsResponse>(fetchImpl, "/config/api/models", {
        method: "POST",
        body: JSON.stringify(params)
      });
    },

    deleteApiKey(payload: Record<string, unknown>): Promise<{
      status: string;
      deleted: boolean;
      group: string;
      provider: string;
      base_url: string;
      message: string;
      config: ConfigResponse;
    }> {
      return requestWithFetch(fetchImpl, "/config/api/delete-api-key", {
        method: "POST",
        body: JSON.stringify(payload)
      });
    },

    testLlm(payload: Record<string, unknown>): Promise<ConnectionTestResponse> {
      return requestWithFetch<ConnectionTestResponse>(fetchImpl, "/config/api/test-llm", {
        method: "POST",
        body: JSON.stringify(payload)
      });
    },

    testEmbedding(payload: Record<string, unknown>): Promise<ConnectionTestResponse> {
      return requestWithFetch<ConnectionTestResponse>(fetchImpl, "/config/api/test-embedding", {
        method: "POST",
        body: JSON.stringify(payload)
      });
    },

    unlockConfig(secret: string): Promise<{ status: string }> {
      return requestWithFetch<{ status: string }>(fetchImpl, "/config/api/unlock", {
        method: "POST",
        body: JSON.stringify({ secret })
      });
    },

    logoutOAuth(): Promise<{ status: string; config: ConfigResponse }> {
      return requestWithFetch<{ status: string; config: ConfigResponse }>(fetchImpl, "/config/api/oauth/logout", {
        method: "POST"
      });
    },

    saveConfig(payload: Record<string, unknown>): Promise<{ status: string; config: ConfigResponse }> {
      return requestWithFetch<{ status: string; config: ConfigResponse }>(fetchImpl, "/config/api/save", {
        method: "POST",
        body: JSON.stringify(payload)
      });
    },

    getChatHistory(agent?: ChatAgentType): Promise<ChatHistoryResponse> {
      return requestWithFetch<ChatHistoryResponse>(fetchImpl, routeForAgent(agent, { query: "/api/chat/history", pipeline: "/api/pipeline-manager/history", ontology: "/api/ontology-agent/history" }));
    },

    newChat(agent?: ChatAgentType): Promise<{ status: string }> {
      return requestWithFetch<{ status: string }>(fetchImpl, routeForAgent(agent, { query: "/api/chat/new", pipeline: "/api/pipeline-manager/new", ontology: "/api/ontology-agent/new" }), { method: "POST" });
    },

    restoreChat(id: string, agent?: ChatAgentType): Promise<ChatRestoreResponse> {
      const base = routeForAgent(agent, { query: "/api/chat/restore", pipeline: "/api/pipeline-manager/restore", ontology: "/api/ontology-agent/restore" });
      return requestWithFetch<ChatRestoreResponse>(fetchImpl, `${base}/${encodeURIComponent(id)}`, {
        method: "POST"
      });
    },

    cancelPipelineRun(runId = ""): Promise<PipelineRunCancelResponse> {
      return requestWithFetch<PipelineRunCancelResponse>(fetchImpl, "/api/v2/pipeline-manager/run/cancel", {
        method: "POST",
        body: JSON.stringify({ run_id: runId })
      });
    },

    resetKernelRuntimeState(): Promise<KernelRuntimeResetResponse> {
      return requestWithFetch<KernelRuntimeResetResponse>(fetchImpl, "/api/v2/pipeline-manager/kernel/reset", {
        method: "POST",
        body: JSON.stringify({
          confirmation: "RESET_KERNEL_RUNTIME_STATE",
          reason: "client frontend kernel reset"
        })
      });
    },

    getPipelineKernelEvents(after = ""): Promise<KernelClientFrontendEventBatch> {
      const suffix = after ? `?after=${encodeURIComponent(after)}` : "";
      return requestWithFetch<KernelClientFrontendEventBatch>(fetchImpl, `/api/v2/pipeline-manager/kernel/events${suffix}`);
    },

    submitKernelInteractionResponse(interactionRequestId: string, payload: KernelUserInteractionResponse): Promise<KernelInteractionRouteResponse> {
      return requestWithFetch<KernelInteractionRouteResponse>(
        fetchImpl,
        `/api/v2/pipeline-manager/kernel/interactions/${encodeURIComponent(interactionRequestId)}/response`,
        {
          method: "POST",
          body: JSON.stringify(payload)
        }
      );
    },

    cancelKernelInteraction(interactionRequestId: string, payload: KernelUserInteractionResponse): Promise<KernelInteractionRouteResponse> {
      return requestWithFetch<KernelInteractionRouteResponse>(
        fetchImpl,
        `/api/v2/pipeline-manager/kernel/interactions/${encodeURIComponent(interactionRequestId)}/cancel`,
        {
          method: "POST",
          body: JSON.stringify(payload)
        }
      );
    }
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
