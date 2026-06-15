import type { HealthResponse } from "../types/index.ts";
import { buildKernelProgressPresentation } from "./kernel_event_policy.ts";
import type { ChatAgentType, DomRefs, KernelUiState } from "./types.ts";

export function createPipelineDomAdapter(document: Document, dom: DomRefs) {
  let pipelineAbortPending = false;
  let renderedStageRowsSignature = "";
  return {
    renderPipelinePermission(health: HealthResponse | null, activeAgent: ChatAgentType, kernelUi: KernelUiState): void {
      if (!dom.pipelinePermissionEl) return;
      if (activeAgent !== "pipeline") {
        setDatasetState(dom.pipelinePermissionEl, "idle");
        setTextIfChanged(dom.pipelinePermissionEl, "");
        return;
      }
      const manager = health?.pipeline_manager;
      if (!manager?.available) {
        setDatasetState(dom.pipelinePermissionEl, "idle");
        setTextIfChanged(dom.pipelinePermissionEl, manager?.reason || "Choose Pipeline Root Folder");
        return;
      }
      if (kernelUi.activeRecoveryEvent) {
        setDatasetState(dom.pipelinePermissionEl, "warning");
        setTextIfChanged(dom.pipelinePermissionEl, kernelUi.activeRecoveryEvent.user_visible_summary || "Kernel recovery is active.");
        return;
      }
      setDatasetState(dom.pipelinePermissionEl, manager.permission_warning ? "warning" : "ok");
      setTextIfChanged(
        dom.pipelinePermissionEl,
        manager.permission_warning
          || `Kernel tools ready: ${manager.semantic_control_kernel_tool_count ?? manager.tool_count ?? 0}. Pending kernel events: ${manager.pending_kernel_event_count ?? 0}.`
      );
    },
    setPipelineAbortPending(pending: boolean): void {
      pipelineAbortPending = pending;
      if (!dom.pipelineAbortButtonEl) return;
      dom.pipelineAbortButtonEl.disabled = pending;
      setTextIfChanged(dom.pipelineAbortButtonEl, pending ? "Stopping..." : "Abort");
    },
    renderPipelineProgress(health: HealthResponse | null, activeAgent: ChatAgentType, kernelUi: KernelUiState): void {
      const panel = dom.pipelineProgressPanelEl;
      if (!panel) return;
      const manager = health?.pipeline_manager;
      const presentation = buildKernelProgressPresentation(kernelUi, {
        activeWorkflowRun: manager?.active_workflow_run || null,
        activePipelineRun: manager?.active_pipeline_run || null
      });
      if (activeAgent !== "pipeline" || !presentation.visible) {
        panel.hidden = true;
        if (dom.pipelineAbortButtonEl) dom.pipelineAbortButtonEl.hidden = true;
        renderedStageRowsSignature = "";
        return;
      }
      panel.hidden = false;
      setDatasetState(panel, presentation.state);
      if (dom.pipelineProgressTitleEl) setTextIfChanged(dom.pipelineProgressTitleEl, presentation.title);
      if (dom.pipelineProgressCountEl) setTextIfChanged(dom.pipelineProgressCountEl, presentation.countText);
      if (dom.pipelineProgressFillEl) setStyleWidthIfChanged(dom.pipelineProgressFillEl, `${presentation.meterPercent}%`);
      if (dom.pipelineProgressSummaryEl) setTextIfChanged(dom.pipelineProgressSummaryEl, presentation.summary);
      if (dom.pipelineAbortButtonEl) {
        dom.pipelineAbortButtonEl.hidden = !presentation.showAbort;
        dom.pipelineAbortButtonEl.disabled = pipelineAbortPending || !presentation.showAbort;
        if (dom.pipelineAbortButtonEl.dataset.runId !== presentation.abortRunId) dom.pipelineAbortButtonEl.dataset.runId = presentation.abortRunId;
        setTextIfChanged(dom.pipelineAbortButtonEl, pipelineAbortPending ? "Stopping..." : "Abort");
      }
      renderedStageRowsSignature = renderStageRows(document, dom, presentation.rows, renderedStageRowsSignature);
    }
  };
}

function renderStageRows(
  document: Document,
  dom: DomRefs,
  rows: Array<{ name: string; status: string; detail: string; state: string }>,
  currentSignature: string
): string {
  if (!dom.pipelineStageListEl) return currentSignature;
  const nextSignature = JSON.stringify(rows);
  if (currentSignature === nextSignature) return currentSignature;
  dom.pipelineStageListEl.replaceChildren();
  for (const row of rows) {
    const element = document.createElement("div");
    element.className = "pipeline-stage-row";
    element.dataset.state = row.state;

    const name = document.createElement("div");
    name.className = "pipeline-stage-name";
    name.textContent = row.name;
    element.appendChild(name);

    const status = document.createElement("div");
    status.className = "pipeline-stage-status";
    status.textContent = row.status;
    element.appendChild(status);

    const detail = document.createElement("div");
    detail.className = row.detail ? "pipeline-stage-detail" : "pipeline-stage-empty";
    detail.textContent = row.detail || "No detail";
    element.appendChild(detail);

    dom.pipelineStageListEl.appendChild(element);
  }
  return nextSignature;
}

function setTextIfChanged(element: HTMLElement, nextText: string): void {
  if (element.textContent !== nextText) element.textContent = nextText;
}

function setDatasetState(element: HTMLElement, nextState: string): void {
  if (element.dataset.state !== nextState) element.dataset.state = nextState;
}

function setStyleWidthIfChanged(element: HTMLElement, nextWidth: string): void {
  if (element.style.width !== nextWidth) element.style.width = nextWidth;
}
