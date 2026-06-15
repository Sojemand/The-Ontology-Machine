import { estimateTokens } from "../tokens.js";
import { PIPELINE_TOOL_RESULT_CHAR_LIMIT, USER_VISIBLE_RESULT_FIELDS } from "./context_policy_constants.js";
import { clipMiddle } from "./context_policy_core.js";
import { compactKernelMirrorEvent } from "./context_policy_kernel_events.js";
import { compactLargeJson } from "./context_policy_json.js";

export { compactLargeJson } from "./context_policy_json.js";

export function estimateToolsTokens(tools) {
  return estimateTokens(JSON.stringify(Array.isArray(tools) ? tools : []));
}

export function compactToolResult(toolName, result) {
  const source = result && typeof result === "object" ? result : { result };
  const compact = compactLargeToolResult(toolName, source);
  const text = JSON.stringify(compact);
  if (text.length <= PIPELINE_TOOL_RESULT_CHAR_LIMIT) return text;
  return JSON.stringify({
    status: source.status || "ok",
    tool_name: toolName,
    truncated_for_model_context: true,
    original_chars: text.length,
    preview: clipMiddle(text, PIPELINE_TOOL_RESULT_CHAR_LIMIT - 500)
  });
}

function compactLargeToolResult(toolName, value) {
  const payload = {};
  for (const [key, item] of Object.entries(value || {})) {
    if (key === "mirror_event") {
      payload.mirror_event = compactKernelMirrorEvent(item);
      continue;
    }
    if (USER_VISIBLE_RESULT_FIELDS.has(key)) {
      payload[key] = compactLargeJson(item, 1);
    }
  }
  if (!("tool_name" in payload)) payload.tool_name = toolName;
  if (!("status" in payload)) payload.status = String(value?.status || "ok");
  if (!("effect" in payload)) payload.effect = String(value?.effect || "none");
  if (!("user_visible_summary" in payload)) {
    payload.user_visible_summary = clipMiddle(String(value?.user_visible_summary || value?.message || ""), 2_000);
  }
  return payload;
}
