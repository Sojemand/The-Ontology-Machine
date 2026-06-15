import { createPipelineKernelAdapter } from "./kernel_client.js";
import { HOST_ONLY_TOOL_NAMES } from "./kernel_tool_surface.js";

const HOST_ONLY_TOOL_NAME_SET = new Set(Object.values(HOST_ONLY_TOOL_NAMES));

export async function probePipelineClient(candidate) {
  const adapter = createPipelineKernelAdapter({
    callKernelTool: (name, args) => candidate.callTool(name, hostOnlyArguments(candidate, name, args)),
    listKernelTools: () => candidate.listTools(),
    listEventScopedTools: (request) => candidate.callTool(HOST_ONLY_TOOL_NAMES.listEventScopedTools, hostOnlyArguments(candidate, HOST_ONLY_TOOL_NAMES.listEventScopedTools, request))
  });
  const permanentTools = await adapter.bootstrap();
  return {
    client: candidate,
    adapter,
    rawToolCount: adapter.discoveredToolCount(),
    permanentTools
  };
}

function hostOnlyArguments(candidate, name, args = {}) {
  if (!HOST_ONLY_TOOL_NAME_SET.has(String(name || ""))) return args;
  const token = String(candidate?.hostBridgeToken || "").trim();
  if (!token) return args;
  const payload = args && typeof args === "object" && !Array.isArray(args) ? args : {};
  return { ...payload, host_bridge_token: token };
}
