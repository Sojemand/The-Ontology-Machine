import {
  EVENT_SCOPED_RECOVERY_TOOL_NAMES,
  FORBIDDEN_LEGACY_AGENT_SURFACE_NAMES,
  PERMANENT_AGENT_TOOL_NAMES
} from "../../client_frontend/pipeline_agent/kernel_client.js";

export { EVENT_SCOPED_RECOVERY_TOOL_NAMES, FORBIDDEN_LEGACY_AGENT_SURFACE_NAMES, PERMANENT_AGENT_TOOL_NAMES };

export const EMPTY_OBJECT_SCHEMA = {
  type: "object",
  properties: {},
  additionalProperties: false
};

export const RESUME_CONTINUE_TOOL_SCHEMA = {
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

function schemaForPermanentTool(name) {
  if (name === "kernel_continue_resumable_workflow") {
    return {
      ...RESUME_CONTINUE_TOOL_SCHEMA,
      properties: { ...RESUME_CONTINUE_TOOL_SCHEMA.properties },
      required: [...RESUME_CONTINUE_TOOL_SCHEMA.required]
    };
  }
  return { ...EMPTY_OBJECT_SCHEMA };
}

export const PERMANENT_MCP_TOOLS = PERMANENT_AGENT_TOOL_NAMES.map((name) => ({
  name,
  description: `Semantic tool ${name}.`,
  inputSchema: schemaForPermanentTool(name)
}));

export const NON_KERNEL_MCP_TOOLS = [
  {
    name: "healthcheck_mcp",
    description: "Non-kernel primitive.",
    inputSchema: { ...EMPTY_OBJECT_SCHEMA }
  }
];

export const LEGACY_MCP_TOOLS = FORBIDDEN_LEGACY_AGENT_SURFACE_NAMES.map((name) => ({
  name,
  description: `Legacy tool ${name}.`,
  inputSchema: { ...EMPTY_OBJECT_SCHEMA }
}));
