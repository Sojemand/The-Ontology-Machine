import { createChatCompletion } from "../provider.js";
import { resolvePipelineRootFromConfig } from "../pipeline_root.js";
import { errorMessage, unavailableError } from "./errors.js";
import { EVENT_SCOPED_RECOVERY_TOOL_NAMES } from "./kernel_client.js";
import { discoverMcpServer, LocalMcpClient } from "./mcp_client.js";
import { PIPELINE_ROOT_REQUIRED_MESSAGE } from "./prompt.js";
import { probePipelineClient } from "./workflow_boot.js";
import { createPipelineAdminRoutes } from "./workflow_admin_routes.js";
import { createWorkflowAutoEventHandlers } from "./workflow_auto_events.js";
import { buildCallContext } from "./workflow_call_context.js";
import { createPipelineChatRoute } from "./workflow_chat_route.js";
import { createKernelEventRoutes } from "./workflow_event_routes.js";
import { createWorkflowPublicApi } from "./workflow_public_api.js";
import {
  fastManagerStatus,
  managerStatusFromAdapter,
} from "./workflow_status.js";

export function resolvePipelineRootForAgent(pipelineRoot = "", moduleRoot = "") {
  return resolvePipelineRootFromConfig(pipelineRoot, moduleRoot);
}

export function createPipelineManagerAgent({
  pipelineRoot = "",
  moduleRoot = "",
  getRuntimeConfig,
  getFrontendPolicy,
  createChatCompletionFn = createChatCompletion,
  mcpClientFactory = (server) => new LocalMcpClient(server)
} = {}) {
  const root = resolvePipelineRootForAgent(pipelineRoot, moduleRoot);
  let readyPromise = null;
  let client = null;
  let kernelAdapter = null;
  let serverInfo = null;
  let startupError = "";
  let rawToolCount = 0;
  let lastConversationRef = "";
  const managerStatusContext = () => ({ root, serverInfo, kernelAdapter, rawToolCount });
  const autoEvents = createWorkflowAutoEventHandlers({
    root,
    getKernelAdapter: () => kernelAdapter,
    callKernelAdapter,
    availabilityStatus,
    getRuntimeConfig,
    getFrontendPolicy,
    createChatCompletionFn
  });
  const eventRoutes = createKernelEventRoutes({
    ensureReady,
    buildCallContext,
    syncConversationScope,
    callKernelAdapter,
    autoEvents
  });
  const chat = createPipelineChatRoute({
    root,
    getKernelAdapter: () => kernelAdapter,
    ensureReady,
    buildCallContext,
    syncConversationScope,
    callKernelAdapter,
    callKernelToolFromModel,
    toManagerStatus,
    getRuntimeConfig,
    getFrontendPolicy,
    createChatCompletionFn,
    autoEvents
  });
  const adminRoutes = createPipelineAdminRoutes({
    root,
    ensureReady,
    callKernelAdapter,
    buildCallContext,
    closeCurrentClient,
    resetBootState: () => {
      readyPromise = null;
      startupError = "";
    },
    setStartupError: (message) => {
      startupError = message;
    },
    getStartupError: () => startupError,
    getManagerStatusContext: managerStatusContext,
    fastStatus,
    toManagerStatus
  });

  function createClient() {
    return mcpClientFactory({
      serverDir: serverInfo.root,
      runBat: serverInfo.runBat,
      pythonExe: serverInfo.pythonExe,
      launcherModule: serverInfo.launcherModule
    });
  }

  function closeCurrentClient() {
    client?.close();
    client = null;
    kernelAdapter = null;
    lastConversationRef = "";
  }

  function applyBootResult(result) {
    client = result.client;
    kernelAdapter = result.adapter;
    rawToolCount = result.rawToolCount;
  }

  async function bootClient() {
    closeCurrentClient();
    const candidate = createClient();
    try {
      applyBootResult(await probePipelineClient(candidate));
      return;
    } catch (error) {
      candidate?.close();
      throw error;
    }
  }

  async function initialize() {
    if (!root) throw unavailableError(PIPELINE_ROOT_REQUIRED_MESSAGE);
    const discovered = await discoverMcpServer(root);
    if (!discovered) throw unavailableError("MCP Server was not found under the configured Pipeline root.");
    serverInfo = discovered;
    await bootClient();
    return true;
  }

  async function ensureReady() {
    if (!readyPromise) {
      readyPromise = initialize().catch((error) => {
        startupError = errorMessage(error);
        readyPromise = null;
        throw error;
      });
    }
    return await readyPromise;
  }

  async function callKernelAdapter(method, ...args) {
    if (!kernelAdapter) throw unavailableError("Semantic Control Kernel is not ready.");
    return await kernelAdapter[method](...args);
  }

  function syncConversationScope(callContext = {}) {
    if (!kernelAdapter) return;
    const conversationRef = String(callContext.conversationRef || "").trim();
    if (!conversationRef) return;
    if (lastConversationRef && conversationRef !== lastConversationRef) {
      kernelAdapter.resetVolatileState();
    }
    lastConversationRef = conversationRef;
  }

  async function availabilityStatus() {
    if (!kernelAdapter) {
      return { available: false, reason: startupError || PIPELINE_ROOT_REQUIRED_MESSAGE, toolCount: 0 };
    }
    return { available: true, reason: "", toolCount: kernelAdapter.permanentToolCount() };
  }

  function toManagerStatus(adapterStatus) {
    return managerStatusFromAdapter({ ...managerStatusContext(), adapterStatus });
  }

  function fastStatus() {
    return fastManagerStatus({ ...managerStatusContext(), startupError, readyPromise });
  }

  async function callKernelToolFromModel(toolName, args, callContext = {}) {
    const activeRecoveryEvent = kernelAdapter.activeRecoveryMirrorEvent();
    if (EVENT_SCOPED_RECOVERY_TOOL_NAMES.includes(toolName)) {
      return await callKernelAdapter("callEventScopedTool", toolName, args, activeRecoveryEvent, callContext);
    }
    return await callKernelAdapter("callVisibleTool", toolName, args, callContext);
  }

  return createWorkflowPublicApi({
    ensureReady,
    chat,
    eventRoutes,
    adminRoutes,
    callKernelAdapter,
    fastStatus,
    closeCurrentClient
  });
}
