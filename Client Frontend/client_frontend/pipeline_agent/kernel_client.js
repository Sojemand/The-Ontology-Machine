import { PipelineKernelAdapterState } from "./kernel_client_state.js";
import {
  PERMANENT_AGENT_TOOL_NAMES,
  validateSemanticControlKernelToolSurface
} from "./kernel_tool_surface.js";

export {
  EVENT_SCOPED_RECOVERY_TOOL_NAMES,
  FORBIDDEN_LEGACY_AGENT_SURFACE_NAMES,
  PERMANENT_AGENT_TOOL_NAMES,
  validateSemanticControlKernelToolSurface
} from "./kernel_tool_surface.js";

export function createPipelineKernelAdapter({ callKernelTool, listKernelTools, listEventScopedTools }) {
  return new PipelineKernelAdapter({ callKernelTool, listKernelTools, listEventScopedTools });
}

class PipelineKernelAdapter extends PipelineKernelAdapterState {
  constructor({ callKernelTool, listKernelTools, listEventScopedTools }) {
    super();
    this.callKernelTool = callKernelTool;
    this.listKernelTools = listKernelTools;
    this.listEventScopedTools = listEventScopedTools;
    this.permanentTools = [];
    this.eventScopedTools = [];
    this.permanentToolMap = new Map();
    this.mirrorEvents = new Map();
    this.pendingMirrorEvents = [];
    this.pendingAutoCallMirrorEvents = [];
    this.activeDialog = null;
    this.activeRecoveryMirrorEventId = "";
    this.activeRecoveryEventByRecoveryId = new Map();
    this.eventCursor = "";
    this.rawToolCount = 0;
    this.clientInstanceId = `pipeline-manager-${Math.random().toString(16).slice(2, 10)}`;
    this.latestKernelStatus = null;
    this.latestResumeState = null;
    this.latestProgressByWorkflowRun = new Map();
    this.terminalWorkflowRunIds = new Set();
    this.transientActiveWorkflowRun = null;
    this.eventScopedToolsWarning = "";
  }

  async bootstrap() {
    const rawDefinitions = await this.listKernelTools();
    this.rawToolCount = rawDefinitions.length;
    this.permanentTools = validateSemanticControlKernelToolSurface(rawDefinitions);
    this.permanentToolMap = new Map(this.permanentTools.map((tool) => [tool.name, tool]));
    return this.permanentTools;
  }

  discoveredToolCount() {
    return this.rawToolCount;
  }

  toolDefinitions() {
    return [...this.permanentTools, ...this.eventScopedTools];
  }

  permanentToolCount() {
    return this.permanentTools.length;
  }


}
