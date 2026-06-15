import { estimateMessagesTokens } from "../tokens.js";
import {
  assistantText,
  clipMiddle,
  compactToolResult,
  estimateToolsTokens,
  MAX_TOOL_ROUNDS,
  parseToolArguments,
  PIPELINE_RESPONSE_RESERVE_TOKENS,
  toChatTool,
  trimPipelineHistoryForContext,
  trimWorkingMessagesForProvider
} from "./context_policy.js";
import { errorMessage } from "./errors.js";
import { isWorkflowStarterTool } from "./kernel_tool_surface.js";
import { buildPipelineSystemPrompt } from "./prompt.js";

const PIPELINE_USER_MESSAGE_CHAR_LIMIT = 20_000;
const WORKFLOW_MENU_COMMAND_PATTERN = /^Run Taxonomy Agent workflow `([^`]+)`\. This was selected from the workflow menu; use the matching visible Kernel workflow tool\.$/;

async function executePipelineToolByName(toolName, args, callKernelToolFromModel) {
  try {
    return await callKernelToolFromModel(toolName, args);
  } catch (error) {
    return {
      schema_version: "semantic_control_kernel.mcp_response.v1",
      status: "failed",
      tool_name: toolName,
      effect: "none",
      user_visible_summary: "The Client Frontend could not complete the Kernel tool call.",
      mirror_event: null,
      error: {
        code: "client_frontend_tool_call_failed",
        category: "technical_failure",
        safe_message: errorMessage(error)
      }
    };
  }
}

async function executePipelineToolCall(toolCall, callKernelToolFromModel) {
  const args = parseToolArguments(toolCall);
  if (!args) {
    return {
      schema_version: "semantic_control_kernel.mcp_response.v1",
      status: "rejected",
      tool_name: String(toolCall?.function?.name || ""),
      effect: "none",
      reason: "tool_arguments_invalid_json",
      user_visible_summary: "The tool call arguments were not valid JSON.",
      mirror_event: null,
      error: {
        code: "tool_arguments_invalid_json",
        category: "client_frontend_validation",
        safe_message: "The tool call arguments were not valid JSON."
      }
    };
  }
  const toolName = String(toolCall?.function?.name || "");
  return await executePipelineToolByName(toolName, args, callKernelToolFromModel);
}

function menuSelectedWorkflowToolName(userMessage) {
  const match = WORKFLOW_MENU_COMMAND_PATTERN.exec(String(userMessage || "").trim());
  return match ? String(match[1] || "").trim() : "";
}

function isVisibleWorkflowStarter(toolDefinitions, toolName) {
  const name = String(toolName || "");
  return isWorkflowStarterTool(name) && Array.isArray(toolDefinitions) && toolDefinitions.some((tool) => String(tool?.name || "") === name);
}

function toolResultAnswer(toolName, result) {
  const summary = String(result?.user_visible_summary || "").trim();
  if (summary) return summary;
  const safeMessage = String(result?.error?.safe_message || "").trim();
  if (safeMessage) return safeMessage;
  const reason = String(result?.reason || "").trim();
  if (reason) return reason;
  const status = String(result?.status || "").trim();
  if (status) return `Kernel tool ${toolName} returned status: ${status}.`;
  return `Kernel tool ${toolName} was sent to the Semantic Control Kernel.`;
}

async function runMenuSelectedWorkflow({ toolName, toolDefinitions, callKernelToolFromModel }) {
  if (!isVisibleWorkflowStarter(toolDefinitions, toolName)) {
    return {
      content: `The workflow selected from the menu is not currently visible to the Taxonomy Agent: ${toolName}. Refresh the Kernel status and try again.`
    };
  }
  const result = await executePipelineToolByName(toolName, {}, callKernelToolFromModel);
  return { content: toolResultAnswer(toolName, result) };
}

export async function runPipelineAgentChat({
  message = "",
  history = [],
  root,
  toolDefinitions,
  availabilityStatus,
  getRuntimeConfig,
  getFrontendPolicy,
  createChatCompletionFn,
  callKernelToolFromModel,
  interactionMode = "workflow_selection"
}) {
  const userMessage = clipMiddle(String(message || "").trim(), PIPELINE_USER_MESSAGE_CHAR_LIMIT);
  const runtimeConfig = getRuntimeConfig?.() || {};
  const frontendPolicy = getFrontendPolicy?.() || null;
  const explanationOnly = interactionMode === "kernel_event_explanation";
  const effectiveToolDefinitions = explanationOnly ? [] : (Array.isArray(toolDefinitions) ? toolDefinitions : []);
  const tools = effectiveToolDefinitions.map(toChatTool);
  const menuWorkflowToolName = explanationOnly ? "" : menuSelectedWorkflowToolName(userMessage);
  const systemMessage = {
    role: "system",
    content: buildPipelineSystemPrompt({
      pipelineRoot: root,
      availabilityStatus,
      toolDefinitions: effectiveToolDefinitions,
      interactionMode
    })
  };
  const seedMessages = userMessage ? [systemMessage, { role: "user", content: userMessage }] : [systemMessage];
  const reservedTokens = estimateMessagesTokens(seedMessages)
    + estimateToolsTokens(tools)
    + PIPELINE_RESPONSE_RESERVE_TOKENS;
  const messages = [
    systemMessage,
    ...trimPipelineHistoryForContext(history, runtimeConfig.context_limit, frontendPolicy, reservedTokens)
  ];
  if (userMessage) {
    messages.push({ role: "user", content: userMessage });
  }
  if (menuWorkflowToolName) {
    return buildFinalChatResult(
      await runMenuSelectedWorkflow({
        toolName: menuWorkflowToolName,
        toolDefinitions: effectiveToolDefinitions,
        callKernelToolFromModel
      }),
      history,
      userMessage,
      runtimeConfig,
      frontendPolicy,
      reservedTokens
    );
  }
  let workflowStarterResult = null;
  let workflowStarterToolName = "";
  for (let round = 0; round < MAX_TOOL_ROUNDS; round += 1) {
    const providerMessages = trimWorkingMessagesForProvider(messages, tools, runtimeConfig.context_limit);
    const assistantMessage = (await createChatCompletionFn(runtimeConfig, providerMessages, tools))?.choices?.[0]?.message;
    if (!assistantMessage) throw new Error("Empty model response.");
    if (!assistantMessage.tool_calls?.length) {
      return buildFinalChatResult(assistantMessage, history, userMessage, runtimeConfig, frontendPolicy, reservedTokens);
    }
    if (explanationOnly) {
      return buildFinalChatResult(
        {
          content: "The Kernel requested explanation-only mode. No workflow tool was executed in this mode."
        },
        history,
        userMessage,
        runtimeConfig,
        frontendPolicy,
        reservedTokens
      );
    }
    messages.push({ role: "assistant", content: assistantMessage.content || "", tool_calls: assistantMessage.tool_calls });
    for (const toolCall of assistantMessage.tool_calls) {
      const toolName = String(toolCall?.function?.name || "");
      if (workflowStarterResult && isWorkflowStarterTool(toolName)) {
        return buildFinalChatResult(
          { content: toolResultAnswer(workflowStarterToolName, workflowStarterResult) },
          history,
          userMessage,
          runtimeConfig,
          frontendPolicy,
          reservedTokens
        );
      }
      const result = await executePipelineToolCall(toolCall, callKernelToolFromModel);
      messages.push({
        role: "tool",
        tool_call_id: toolCall.id,
        content: compactToolResult(toolName, result)
      });
      if (isWorkflowStarterTool(toolName)) {
        workflowStarterResult = result;
        workflowStarterToolName = toolName;
      }
    }
  }
  if (workflowStarterResult) {
    return buildFinalChatResult(
      { content: toolResultAnswer(workflowStarterToolName, workflowStarterResult) },
      history,
      userMessage,
      runtimeConfig,
      frontendPolicy,
      reservedTokens
    );
  }
  throw new Error("Too many Kernel tool rounds without a final answer.");
}

function buildFinalChatResult(assistantMessage, history, userMessage, runtimeConfig, frontendPolicy, reservedTokens) {
  const answer = assistantText(assistantMessage) || "I could not formulate a Taxonomy Agent answer.";
  const nextHistory = userMessage
    ? [...(Array.isArray(history) ? history : []), { role: "user", content: userMessage }, { role: "assistant", content: answer }]
    : [...(Array.isArray(history) ? history : []), { role: "assistant", content: answer }];
  return {
    answer,
    sources: [],
    history: trimPipelineHistoryForContext(nextHistory, runtimeConfig.context_limit, frontendPolicy, reservedTokens),
    mode: "analytic",
    exactness: "evidence_grounded",
    metrics: { scope_documents: 0, matched_documents: 0, matched_occurrences: 0, aggregated_values: null },
    ambiguities: [],
    method: "pipeline_manager_agent"
  };
}
