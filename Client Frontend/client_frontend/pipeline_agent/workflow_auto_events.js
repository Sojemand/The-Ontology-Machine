import { mergeKernelMirrorEventsIntoHistory } from "./context_policy.js";
import { runPipelineAgentChat } from "./chat_workflow.js";

export function createWorkflowAutoEventHandlers({
  root,
  getKernelAdapter,
  callKernelAdapter,
  availabilityStatus,
  getRuntimeConfig,
  getFrontendPolicy,
  createChatCompletionFn
}) {
  async function appendMirrorEvents(history) {
    const kernelAdapter = getKernelAdapter();
    const mirrorEvents = kernelAdapter?.drainKernelMirrorEvents?.() || [];
    return mergeKernelMirrorEventsIntoHistory(history, mirrorEvents);
  }

  async function autoExplainMirrorEvent(history, mirrorEvent, callContext = {}) {
    const guidance = mirrorEvent?.agent_explanation_guidance;
    const responseMode = typeof guidance === "string"
      ? guidance
      : guidance && typeof guidance === "object"
        ? String(guidance.response_mode || guidance.mode || "")
        : "";
    if (!mirrorEvent?.is_kernel_auto_call) return null;
    if (responseMode === "emit_direct_message") {
      return directMirrorMessageResult(history, mirrorEvent);
    }
    await callKernelAdapter("prepareEventScopedTools", callContext);
    const explainNow = responseMode === "explain_now" || responseMode.includes("explain_now");
    if (!explainNow) return null;
    const kernelAdapter = getKernelAdapter();
    const modelHistory = mergeKernelMirrorEventsIntoHistory([], [mirrorEvent]);
    const autoResult = await runPipelineAgentChat({
      message: "",
      history: modelHistory,
      root,
      toolDefinitions: kernelAdapter.toolDefinitions(),
      availabilityStatus: await availabilityStatus(),
      getRuntimeConfig,
      getFrontendPolicy,
      createChatCompletionFn,
      callKernelToolFromModel: () => ({
        schema_version: "semantic_control_kernel.mcp_response.v1",
        status: "rejected",
        effect: "none",
        reason: "kernel_event_explanation_tool_call_disabled",
        user_visible_summary: "Kernel event explanation turns cannot execute workflow tools."
      }),
      interactionMode: "kernel_event_explanation"
    });
    autoResult.history = [
      ...mergeKernelMirrorEventsIntoHistory(history, [mirrorEvent]),
      { role: "assistant", content: String(autoResult.answer || "") }
    ];
    return autoResult;
  }

  async function collectPendingAutoCallResults(history, callContext = {}) {
    const kernelAdapter = getKernelAdapter();
    let nextHistory = Array.isArray(history) ? history : [];
    const autoResults = [];
    for (const mirrorEvent of kernelAdapter?.drainPendingAutoCallMirrorEvents?.() || []) {
      const autoResult = await autoExplainMirrorEvent(nextHistory, mirrorEvent, callContext);
      if (!autoResult) continue;
      autoResults.push(autoResult);
      if (Array.isArray(autoResult.history)) {
        nextHistory = autoResult.history;
      }
    }
    return { autoResults, history: nextHistory };
  }

  return {
    appendMirrorEvents,
    collectPendingAutoCallResults
  };
}

function directMirrorMessageResult(history, mirrorEvent) {
  const answer = String(mirrorEvent?.user_visible_summary || "").trim();
  if (!answer) return null;
  const guidance = mirrorEvent?.agent_explanation_guidance && typeof mirrorEvent.agent_explanation_guidance === "object"
    ? mirrorEvent.agent_explanation_guidance
    : {};
  const suppressKernelHistory = guidance?.suppress_kernel_history === true;
  const baseHistory = Array.isArray(history) ? history.map((entry) => ({ ...entry })) : [];
  const nextHistory = suppressKernelHistory
    ? baseHistory.filter((entry) => !(entry?.role === "kernel" && entry?.kernel_mirror_event?.mirror_event_id === mirrorEvent?.mirror_event_id))
    : mergeKernelMirrorEventsIntoHistory(baseHistory, [mirrorEvent]);
  return {
    answer,
    sources: [],
    history: [...nextHistory, { role: "assistant", content: answer }],
    mode: "analytic",
    exactness: "evidence_grounded",
    metrics: { scope_documents: 0, matched_documents: 0, matched_occurrences: 0, aggregated_values: null },
    ambiguities: [],
    method: "kernel_auto_report"
  };
}
