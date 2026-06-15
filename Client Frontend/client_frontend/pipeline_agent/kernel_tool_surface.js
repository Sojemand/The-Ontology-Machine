import { isEmptyObject } from "./kernel_object_utils.js";

const EMPTY_TOOL_SCHEMA = {
  type: "object",
  properties: {},
  additionalProperties: false
};

const RESUME_CONTINUE_TOOL_NAME = "kernel_continue_resumable_workflow";
const RESUME_CONTINUE_TOOL_SCHEMA = {
  type: "object",
  properties: {
    resume_option_ref: {
      type: "string",
      description: "Opaque Kernel resume option ref returned by kernel_resume_state."
    }
  },
  required: ["resume_option_ref"],
  additionalProperties: false
};

export const PERMANENT_AGENT_TOOL_NAMES = [
  "empty_database_no_semantic_release",
  "empty_database_default_taxonomy_no_projections",
  "empty_database_default_taxonomy_default_projections",
  "empty_database_default_taxonomy_custom_projections",
  "empty_database_custom_taxonomy_no_projections",
  "empty_database_custom_taxonomy_custom_projections",
  "manual_pipeline_run",
  "database_merge_additive_only",
  "database_rebuild_from_artifacts",
  "create_custom_taxonomy_path",
  "create_custom_projection_path",
  "reset_database",
  "kernel_status",
  "kernel_resume_state",
  "kernel_continue_resumable_workflow",
  "kernel_cancel_active_run"
];

export const EVENT_SCOPED_RECOVERY_TOOL_NAMES = [
  "kernel_apply_recovery_option",
  "kernel_open_recovery_dialog",
  "kernel_retry_recoverable_workflow",
  "kernel_resolve_stale_lock",
  "kernel_rebind_database_artifact_tree",
  "kernel_discard_or_archive_staged_work",
  "kernel_reconcile_partial_pipeline_run",
  "kernel_open_support_bundle"
];

function legacyName(...parts) {
  return parts.join("_");
}

export const FORBIDDEN_LEGACY_AGENT_SURFACE_NAMES = [
  legacyName("pipeline", "action"),
  legacyName("pipeline", "continue"),
  legacyName("llm", "action", "catalog"),
  legacyName("open", "workflow"),
  legacyName("inspect", "workflow"),
  legacyName("execute", "readonly", "workflow", "action"),
  legacyName("execute", "author", "workflow", "action"),
  legacyName("execute", "operator", "workflow", "action"),
  legacyName("execute", "admin", "workflow", "action"),
  legacyName("interrupt", "workflow"),
  legacyName("close", "workflow"),
  legacyName("workflow", "family", "id"),
  legacyName("workflow", "revision"),
  legacyName("action", "token"),
  legacyName("target", "action", "id"),
  legacyName("x", "action", "catalog"),
  legacyName("required", "agent", "level")
];

export const HOST_ONLY_TOOL_NAMES = {
  listEvents: "kernel_list_client_frontend_events",
  submitInteraction: "kernel_submit_user_interaction_response",
  cancelInteraction: "kernel_cancel_user_interaction",
  listEventScopedTools: "kernel_list_event_scoped_tool_definitions"
};

const READ_ONLY_MANAGER_TOOLS = new Set(["kernel_status", "kernel_resume_state", "kernel_cancel_active_run"]);

export function validateSemanticControlKernelToolSurface(toolDefinitions = []) {
  const raw = Array.isArray(toolDefinitions) ? toolDefinitions : [];
  const availableByName = new Map(raw.map((tool) => [String(tool?.name || ""), tool]));
  const missing = PERMANENT_AGENT_TOOL_NAMES.filter((name) => !availableByName.has(name));
  if (missing.length) {
    throw new Error(`Semantic Control Kernel tool surface is missing permanent Agent tools: ${missing.join(", ")}`);
  }
  const forbiddenVisible = FORBIDDEN_LEGACY_AGENT_SURFACE_NAMES.filter((name) => availableByName.has(name));
  if (forbiddenVisible.length) {
    throw new Error(`Semantic Control Kernel exposed retired Agent tools: ${forbiddenVisible.join(", ")}`);
  }
  return PERMANENT_AGENT_TOOL_NAMES.map((name) => toModelVisibleToolDefinition(name, availableByName.get(name)));
}

export function toModelVisibleToolDefinition(name, sourceDefinition) {
  return {
    name,
    description: String(sourceDefinition?.description || fallbackDescription(name)),
    inputSchema: inputSchemaForVisibleTool(name, sourceDefinition)
  };
}

export function isWorkflowStarterTool(name) {
  const toolName = String(name || "");
  return PERMANENT_AGENT_TOOL_NAMES.includes(toolName) && !READ_ONLY_MANAGER_TOOLS.has(toolName);
}

function inputSchemaForVisibleTool(name, sourceDefinition) {
  if (name === RESUME_CONTINUE_TOOL_NAME) {
    const schema = sourceDefinition?.inputSchema;
    if (schema && typeof schema === "object" && schema.properties?.resume_option_ref) {
      return {
        type: "object",
        properties: { ...schema.properties },
        required: Array.isArray(schema.required) ? [...schema.required] : ["resume_option_ref"],
        additionalProperties: false
      };
    }
    return { ...RESUME_CONTINUE_TOOL_SCHEMA, properties: { ...RESUME_CONTINUE_TOOL_SCHEMA.properties } };
  }
  return { ...EMPTY_TOOL_SCHEMA };
}

function fallbackDescription(name) {
  const friendly = name.replace(/_/g, " ");
  if (name.startsWith("kernel_")) {
    return `Semantic Control Kernel ${friendly}.`;
  }
  return `Semantic Control Kernel workflow ${friendly}.`;
}

export function normalizeKernelResponse(response, toolName) {
  if (response && typeof response === "object") return response;
  return {
    schema_version: "semantic_control_kernel.mcp_response.v1",
    status: "failed",
    tool_name: toolName,
    effect: "none",
    user_visible_summary: "The Semantic Control Kernel returned an invalid response.",
    mirror_event: null,
    error: {
      code: "invalid_kernel_response",
      category: "contract_validation",
      safe_message: "The Semantic Control Kernel returned an invalid response."
    }
  };
}

export function rejectedToolResult(toolName, reason, userVisibleSummary) {
  return {
    schema_version: "semantic_control_kernel.mcp_response.v1",
    status: "rejected",
    tool_name: toolName,
    effect: "none",
    reason,
    user_visible_summary: userVisibleSummary,
    mirror_event: null,
    error: {
      code: reason,
      category: "client_frontend_validation",
      safe_message: userVisibleSummary
    }
  };
}

export function visibleToolArguments(name, modelArguments = {}) {
  const args = modelArguments && typeof modelArguments === "object" && !Array.isArray(modelArguments) ? modelArguments : null;
  if (!args) {
    return {
      ok: false,
      message: "Kernel workflow and support tools accept only object arguments."
    };
  }
  if (name !== RESUME_CONTINUE_TOOL_NAME) {
    return isEmptyObject(args)
      ? { ok: true, arguments: {} }
      : {
          ok: false,
          message: "Kernel workflow and support tools do not accept model-authored arguments."
        };
  }
  const keys = Object.keys(args);
  if (keys.length === 0) return { ok: true, arguments: {} };
  if (keys.length === 1 && keys[0] === "resume_option_ref" && typeof args.resume_option_ref === "string" && args.resume_option_ref.trim()) {
    return { ok: true, arguments: { resume_option_ref: args.resume_option_ref.trim() } };
  }
  return {
    ok: false,
    message: "kernel_continue_resumable_workflow accepts only the opaque resume_option_ref returned by kernel_resume_state."
  };
}
