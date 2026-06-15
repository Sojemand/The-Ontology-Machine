import { randomUUID } from "node:crypto";

import {
  getPipelineSessionIdFromCookies,
  json,
  parseCookies,
  readJsonBody,
  resolveUserId,
  setPipelineSessionCookie
} from "./adapter.js";
import { persistPipelineDisplayMessages } from "./chat_routes.js";
import { parseKernelInteractionRoute, validateKernelInteractionBody } from "./api_workflow_kernel_validation.js";

export const KERNEL_INTERACTIONS_PREFIX = "/api/v2/pipeline-manager/kernel/interactions/";
export const KERNEL_EVENTS_ROUTE = "/api/v2/pipeline-manager/kernel/events";
export const KERNEL_RESET_ROUTE = "/api/v2/pipeline-manager/kernel/reset";

const KERNEL_RESET_CONFIRMATION = "RESET_KERNEL_RUNTIME_STATE";

export async function handlePipelineRunCancelRoute({ request, response, context }) {
  if (!context.pipelineAgent?.cancelActiveRun) {
    json(response, 409, { error: "Choose Pipeline Root Folder", field: "pipeline_root" });
    return;
  }
  try {
    const body = await readJsonBody(request);
    const runId = typeof body?.run_id === "string" ? body.run_id : "";
    json(response, 200, await context.pipelineAgent.cancelActiveRun(runId));
  } catch (error) {
    if (error?.code === "pipeline_manager_unavailable") {
      json(response, 409, { error: error.message, field: "pipeline_root" });
      return;
    }
    throw error;
  }
}

export async function handleKernelResetRoute({ request, response, context }) {
  if (!context.pipelineAgent?.resetKernelRuntimeState) {
    json(response, 409, { error: "Choose Pipeline Root Folder", field: "pipeline_root" });
    return;
  }
  const body = await readJsonBody(request);
  if (body?.confirmation !== KERNEL_RESET_CONFIRMATION) {
    json(response, 400, { error: "Kernel Reset requires explicit confirmation." });
    return;
  }
  const reason = typeof body.reason === "string" && body.reason.trim()
    ? body.reason.trim()
    : "client frontend kernel reset";
  try {
    json(response, 200, await context.pipelineAgent.resetKernelRuntimeState({ reason }));
  } catch (error) {
    if (error?.code === "pipeline_manager_unavailable") {
      json(response, 409, { error: error.message, field: "pipeline_root" });
      return;
    }
    throw error;
  }
}

export async function handleKernelEventsRoute({ request, response, url, context }) {
  if (!context.pipelineAgent?.listKernelEvents) {
    json(response, 409, { error: "Choose Pipeline Root Folder", field: "pipeline_root" });
    return;
  }
  await withPipelineSession({ request, response, context }, async ({ sessionId, ownerId }) => {
    const after = String(url.searchParams.get("after") || "");
    const history = context.pipelineSessionManager.getHistory(sessionId);
    const result = await context.pipelineAgent.listKernelEvents(after, { conversationRef: sessionId, history });
    syncKernelAgentResult(context, sessionId, ownerId, result);
    json(response, 200, {
      ...(result.batch || {}),
      session_id: sessionId,
      auto_results: Array.isArray(result.autoResults) ? result.autoResults : []
    });
  });
}

export async function handleKernelInteractionRoute({ request, response, url, context }) {
  if (!context.pipelineAgent?.submitInteractionResponse || !context.pipelineAgent?.cancelInteraction) {
    json(response, 409, { error: "Choose Pipeline Root Folder", field: "pipeline_root" });
    return;
  }
  const route = parseKernelInteractionRoute(url.pathname);
  if (!route) {
    json(response, 404, { error: "Kernel interaction route not found." });
    return;
  }
  await withPipelineSession({ request, response, context }, async ({ sessionId, ownerId }) => {
    let payload;
    try {
      const body = await readJsonBody(request);
      payload = validateKernelInteractionBody(route, body);
    } catch (error) {
      json(response, 400, { error: error instanceof Error ? error.message : "Invalid Kernel interaction payload." });
      return;
    }
    if (payload.interaction_request_id !== route.interactionRequestId) {
      json(response, 400, { error: "interaction_request_id must match the request path." });
      return;
    }
    const history = context.pipelineSessionManager.getHistory(sessionId);
    const result = route.action === "response"
      ? await context.pipelineAgent.submitInteractionResponse(route.interactionRequestId, payload, { conversationRef: sessionId, history })
      : await context.pipelineAgent.cancelInteraction(route.interactionRequestId, payload, { conversationRef: sessionId, history });
    syncKernelAgentResult(context, sessionId, ownerId, result);
    json(response, 200, {
      bridge_response: result.bridge_response,
      event_batch: result.event_batch,
      auto_results: Array.isArray(result.autoResults) ? result.autoResults : []
    });
  });
}

async function withPipelineSession({ request, response, context }, callback) {
  const cookies = parseCookies(request.headers.cookie);
  const existingSessionId = getPipelineSessionIdFromCookies(context.vaultDir, cookies);
  const sessionId = existingSessionId || randomUUID();
  await context.pipelineSessionManager.runSerialized(sessionId, async () => {
    if (!existingSessionId) setPipelineSessionCookie(context.vaultDir, response, sessionId, request);
    const ownerId = resolveUserId(context.vaultDir, response, cookies, sessionId, request);
    context.pipelineSessionManager.setOwnerId(sessionId, ownerId);
    context.pipelineSessionManager.touch(sessionId);
    await callback({ sessionId, ownerId });
  });
}

function syncKernelAgentResult(context, sessionId, ownerId, result) {
  if (Array.isArray(result.history)) {
    context.pipelineSessionManager.setHistory(sessionId, result.history);
    context.pipelineSessionManager.touch(sessionId);
  }
  const autoResults = Array.isArray(result.autoResults) ? result.autoResults : [];
  if (autoResults.length) {
    persistAutoCallResults(context, sessionId, ownerId, autoResults);
  }
}

function persistAutoCallResults(context, sessionId, ownerId, autoResults) {
  const displayMessages = [...context.pipelineSessionManager.getDisplayMessages(sessionId)];
  let nextHistory = context.pipelineSessionManager.getHistory(sessionId);
  for (const result of autoResults) {
    displayMessages.push({
      role: "assistant",
      content: String(result.answer || ""),
      sources: [],
      mode: result.mode,
      exactness: result.exactness,
      method: result.method,
      metrics: result.metrics,
      ambiguities: result.ambiguities
    });
    nextHistory = Array.isArray(result.history) ? result.history : nextHistory;
  }
  context.pipelineSessionManager.setDisplayMessages(sessionId, displayMessages);
  context.pipelineSessionManager.setHistory(sessionId, nextHistory);
  context.pipelineSessionManager.setOwnerId(sessionId, ownerId);
  persistPipelineDisplayMessages(context, sessionId);
}
