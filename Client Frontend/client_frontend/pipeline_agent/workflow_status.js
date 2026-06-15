import { PIPELINE_ROOT_REQUIRED_MESSAGE } from "./prompt.js";

export function summarizeResetManifest(manifest) {
  const archivedPaths = Array.isArray(manifest?.archived_paths) ? manifest.archived_paths : [];
  const termination = manifest?.background_process_termination && typeof manifest.background_process_termination === "object"
    ? manifest.background_process_termination
    : null;
  const stoppedCount = Array.isArray(termination?.terminated) ? termination.terminated.length : 0;
  return {
    status: "ok",
    reset_id: String(manifest?.reset_id || ""),
    created_at: String(manifest?.created_at || ""),
    archived_path_count: archivedPaths.length,
    preserved_paths: Array.isArray(manifest?.preserved_paths) ? manifest.preserved_paths : [],
    reason: String(manifest?.reason || ""),
    background_process_termination: termination,
    message: archivedPaths.length
      ? `Kernel Runtime State wurde zurueckgesetzt; ${archivedPaths.length} aktive State-Dateien wurden archiviert${stoppedCount ? ` und ${stoppedCount} Hintergrundprozess(e) gestoppt` : ""}.`
      : `Kernel Runtime State wurde zurueckgesetzt; aktive State-Dateien waren bereits leer${stoppedCount ? `, ${stoppedCount} Hintergrundprozess(e) wurden gestoppt` : ""}.`
  };
}

export function unavailableManagerStatus({ reason, root, serverInfo, rawToolCount, extra = {} }) {
  return {
    available: false,
    reason,
    pipeline_root: root,
    mcp_server_dir: serverInfo?.root || "",
    tool_count: 0,
    kernel_status: null,
    semantic_control_kernel_tool_count: 0,
    active_workflow_run: null,
    active_pipeline_run: null,
    active_dialog: null,
    active_recovery_event: null,
    pending_kernel_event_count: 0,
    permission_status: null,
    permission_warning: "",
    raw_mcp_tool_count: rawToolCount,
    ...extra
  };
}

export function managerStatusFromAdapter({ root, serverInfo, kernelAdapter, rawToolCount, adapterStatus }) {
  return {
    available: true,
    reason: "",
    pipeline_root: root,
    mcp_server_dir: serverInfo?.root || "",
    tool_count: kernelAdapter.permanentToolCount(),
    kernel_status: adapterStatus.kernel_status || null,
    semantic_control_kernel_tool_count: kernelAdapter.permanentToolCount(),
    active_workflow_run: adapterStatus.active_workflow_run || null,
    active_pipeline_run: adapterStatus.active_pipeline_run || null,
    active_dialog: adapterStatus.active_dialog || null,
    active_recovery_event: adapterStatus.active_recovery_event || null,
    pending_kernel_event_count: adapterStatus.pending_kernel_event_count || 0,
    permission_status: null,
    permission_warning: adapterStatus.operational_warning || "",
    raw_mcp_tool_count: rawToolCount
  };
}

export function fastManagerStatus({ root, kernelAdapter, startupError, readyPromise, serverInfo, rawToolCount }) {
  if (!root) return unavailableManagerStatus({ reason: PIPELINE_ROOT_REQUIRED_MESSAGE, root: "", serverInfo, rawToolCount });
  if (!kernelAdapter) {
    return unavailableManagerStatus({
      reason: startupError || (readyPromise ? "Taxonomy Agent is still starting." : PIPELINE_ROOT_REQUIRED_MESSAGE),
      root,
      serverInfo,
      rawToolCount,
      extra: { startup_pending: Boolean(readyPromise) }
    });
  }
  return managerStatusFromAdapter({
    root,
    serverInfo,
    kernelAdapter,
    rawToolCount,
    adapterStatus: kernelAdapter.cachedStatus()
  });
}
