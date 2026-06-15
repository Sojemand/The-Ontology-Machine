import { MAIN_APP_DEFAULTS, MAIN_APP_TEXT } from "./policy.ts";
import { isPipelineStartupStatus, syncKernelUiToManagerState } from "./workflow_kernel_state.ts";
import type { AppState, ChatAgentType, MainApi } from "./types.ts";
import type { LayoutDebugController } from "./debug.ts";
import type { MainDomAdapter } from "./dom_adapter.ts";
import type { LayoutWorkflow } from "./layout_workflow.ts";

interface KernelHealthControllerDeps {
  api: MainApi;
  state: AppState;
  domAdapter: MainDomAdapter;
  layoutWorkflow: LayoutWorkflow;
  debug: LayoutDebugController;
  updateTurnCounter: () => void;
  renderChrome: () => void;
}

export function createKernelHealthController({
  api,
  state,
  domAdapter,
  layoutWorkflow,
  debug,
  updateTurnCounter,
  renderChrome
}: KernelHealthControllerDeps) {
  let healthRefreshInFlight = false;
  let pipelineStartupStatusVisible = false;

  function syncPipelineStartupStatus(): void {
    if (!pipelineStartupStatusVisible || state.activeAgentType !== "pipeline" || state.sending) return;
    const manager = state.health?.pipeline_manager;
    if (manager?.available) {
      domAdapter.setChatStatus(MAIN_APP_DEFAULTS.readyStatus);
      pipelineStartupStatusVisible = false;
      return;
    }
    if (manager && !isPipelineStartupStatus(manager)) {
      domAdapter.setChatStatus(manager.reason || MAIN_APP_TEXT.pipelineRootRequired);
      pipelineStartupStatusVisible = false;
      return;
    }
    if (manager?.reason) domAdapter.setChatStatus(manager.reason, true);
  }

  function applyHealth(health: AppState["health"]): void {
    if (!health) return;
    state.health = health;
    state.customerName = health.customer_name || state.customerName;
    state.queryAgentName = health.agent_name || state.queryAgentName;
    state.pipelineManager = health.pipeline_manager;
    domAdapter.setCustomerName(state.customerName);
    domAdapter.fitCustomerName(state.layout.density);
    state.agentName = state.activeAgentType === "pipeline"
      ? state.pipelineAgentName
      : state.activeAgentType === "ontology"
        ? state.ontologyAgentName
        : state.queryAgentName;
    domAdapter.setAgentName(state.agentName);
    layoutWorkflow.applyTheme(domAdapter.readStoredTheme() || health.theme || state.theme);
    syncKernelUiToManagerState(state);
    domAdapter.renderHealth(health);
    renderChrome();
    updateTurnCounter();
    debug.render(state);
    syncPipelineStartupStatus();
  }

  async function refreshHealth(): Promise<void> {
    if (healthRefreshInFlight) return;
    healthRefreshInFlight = true;
    try {
      applyHealth(await api.getHealth());
    } catch (error) {
      domAdapter.setHealthError(error instanceof Error ? error.message : MAIN_APP_DEFAULTS.healthError);
    } finally {
      healthRefreshInFlight = false;
    }
  }

  function setAgentSwitchStatus(agentType: ChatAgentType): void {
    if (agentType === "pipeline" && state.health?.pipeline_manager && !state.health.pipeline_manager.available) {
      pipelineStartupStatusVisible = isPipelineStartupStatus(state.health.pipeline_manager);
      domAdapter.setChatStatus(state.health.pipeline_manager.reason || MAIN_APP_TEXT.pipelineRootRequired, pipelineStartupStatusVisible);
      return;
    }
    pipelineStartupStatusVisible = false;
    domAdapter.setChatStatus(MAIN_APP_DEFAULTS.readyStatus);
  }

  return {
    refreshHealth,
    setAgentSwitchStatus
  };
}
