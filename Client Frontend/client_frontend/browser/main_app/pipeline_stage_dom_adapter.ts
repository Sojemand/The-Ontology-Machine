import type { PipelineRunState, PipelineStageSnapshot } from "../types/index.ts";
import type { DomRefs } from "./types.ts";

function finiteNumber(value: unknown): number | null {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function pipelineStageState(stage: PipelineStageSnapshot): string {
  const text = `${stage.status || ""} ${stage.detail || ""}`.toLowerCase();
  if (text.includes("fehler") || text.includes("error")) return "error";
  if (text.includes("warn") || text.includes("review")) return "warning";
  if (text.includes("fertig") || text.includes("done") || text.includes("completed")) return "done";
  if (text.includes("verarbeite") || text.includes("running")) return "running";
  return "idle";
}

function pipelineStageProgress(stage: PipelineStageSnapshot): string {
  const current = finiteNumber(stage.progress_current);
  const total = finiteNumber(stage.progress_total);
  if (current === null || total === null || total <= 0) return "";
  const label = String(stage.progress_label || "").trim();
  return `${current}/${total}${label ? ` ${label}` : ""}`;
}

function preflightStageEntries(run: PipelineRunState): [string, PipelineStageSnapshot][] {
  return (run.preflight_failure?.modules || []).map((item) => [
    String(item.display_name || item.key || "Module"),
    {
      status: item.healthy ? "Ready" : "Error",
      detail: item.message || item.blocking_dependencies?.map((dependency) => dependency.detail || dependency.name).filter(Boolean).join(" | ") || ""
    }
  ]);
}

export function renderPipelineStages(document: Document, dom: DomRefs, run: PipelineRunState): void {
  if (!dom.pipelineStageListEl) return;
  dom.pipelineStageListEl.textContent = "";
  let stageEntries = Object.entries(run.snapshot?.stage_statuses || {}).filter((entry): entry is [string, PipelineStageSnapshot] =>
    Boolean(entry[0] && entry[1])
  );
  if (!stageEntries.length && run.run_phase === "preflight_failed") stageEntries = preflightStageEntries(run);
  if (!stageEntries.length) {
    const empty = document.createElement("div");
    empty.className = "pipeline-stage-empty muted";
    empty.textContent = "No stage snapshot received yet.";
    dom.pipelineStageListEl.appendChild(empty);
    return;
  }
  for (const [name, stage] of stageEntries) renderPipelineStageRow(document, dom, name, stage);
}

function renderPipelineStageRow(document: Document, dom: DomRefs, name: string, stage: PipelineStageSnapshot): void {
  const row = document.createElement("div");
  row.className = "pipeline-stage-row";
  row.dataset.state = pipelineStageState(stage);
  const nameEl = document.createElement("span");
  nameEl.className = "pipeline-stage-name";
  nameEl.textContent = name;
  const statusEl = document.createElement("span");
  statusEl.className = "pipeline-stage-status";
  statusEl.textContent = String(stage.status || "Ready");
  const detailEl = document.createElement("span");
  detailEl.className = "pipeline-stage-detail";
  detailEl.textContent = [stage.detail, pipelineStageProgress(stage)].filter(Boolean).join(" | ");
  row.append(nameEl, statusEl, detailEl);
  dom.pipelineStageListEl?.appendChild(row);
}
