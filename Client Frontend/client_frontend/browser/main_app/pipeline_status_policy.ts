import type { AppState } from "./types.ts";

type PipelineRunState = NonNullable<NonNullable<AppState["health"]>["pipeline_manager"]>["active_pipeline_run"];

function isTerminalPipelineRun(run: PipelineRunState): boolean {
  const status = String(run?.status || "").toLowerCase();
  return status === "completed" || status === "error" || status === "failed" || status === "cancelled" || status === "interrupted" || status === "no_documents_processed" || Boolean(run?.snapshot?.aborted);
}

function isRunningPipelineRun(run: PipelineRunState): boolean {
  const status = String(run?.status || "").toLowerCase();
  return status === "running" || status === "running_unknown";
}

function finiteElapsedSeconds(value: unknown): number | null {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function pipelineRunSessionKey(run: PipelineRunState): string {
  if (!run) return "";
  return [
    String(run.run_id || ""),
    String(run.status || ""),
    String(run.run_phase || ""),
    String(run.preflight_failure?.artifact_path || ""),
    String(run.no_document_processing?.input_files ?? ""),
    String(run.message || run.preflight_failure?.message || run.preflight_failure?.reason || "")
  ].join("|");
}

function pipelineRunElapsedKey(run: PipelineRunState): string {
  if (!run) return "";
  const runId = String(run.run_id || "").trim();
  if (runId) return `run:${runId}`;
  return [
    "active",
    String(run.active_context?.artifact_folder || ""),
    String(run.active_context?.corpus_output_folder || ""),
    String(run.active_context?.corpus_db_path || ""),
    String(run.input_before_run?.total_files ?? ""),
    String(run.mode || "")
  ].join("|");
}

export function createStartupPipelineStatusFilter() {
  let ignoredStartupPipelineRunKey: string | null | undefined;
  return (health: AppState["health"]): AppState["health"] => {
    const manager = health?.pipeline_manager;
    const run = manager?.active_pipeline_run;
    if (ignoredStartupPipelineRunKey === undefined) {
      ignoredStartupPipelineRunKey = isTerminalPipelineRun(run) ? pipelineRunSessionKey(run) : null;
    }
    if (!run || !ignoredStartupPipelineRunKey || !isTerminalPipelineRun(run)) return health;
    if (pipelineRunSessionKey(run) !== ignoredStartupPipelineRunKey) return health;
    return {
      ...health,
      pipeline_manager: {
        ...manager,
        active_pipeline_run: { status: "idle" }
      }
    };
  };
}

export function createPipelineElapsedFreezer() {
  const runningElapsedByRun = new Map<string, number>();
  const frozenElapsedByRun = new Map<string, number>();

  return (health: AppState["health"]): AppState["health"] => {
    const manager = health?.pipeline_manager;
    const run = manager?.active_pipeline_run;
    const key = pipelineRunElapsedKey(run);
    if (!manager || !run || !key) return health;

    const elapsed = finiteElapsedSeconds(run.elapsed_seconds);
    if (isRunningPipelineRun(run)) {
      frozenElapsedByRun.delete(key);
      if (elapsed !== null) runningElapsedByRun.set(key, elapsed);
      return health;
    }
    if (!isTerminalPipelineRun(run)) return health;

    let frozenElapsed = frozenElapsedByRun.get(key);
    if (frozenElapsed === undefined) {
      frozenElapsed = elapsed ?? runningElapsedByRun.get(key);
      if (frozenElapsed === undefined) return health;
      frozenElapsedByRun.set(key, frozenElapsed);
    }
    if (elapsed === frozenElapsed) return health;

    return {
      ...health,
      pipeline_manager: {
        ...manager,
        active_pipeline_run: {
          ...run,
          elapsed_seconds: frozenElapsed
        }
      }
    };
  };
}

export function pipelineRunningStatusText(run: PipelineRunState): string {
  const elapsed = Number.isFinite(run?.elapsed_seconds) ? ` (${Math.round(Number(run?.elapsed_seconds))}s)` : "";
  return `Pipeline running${elapsed}`;
}
