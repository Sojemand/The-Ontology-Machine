const TERMINAL_PROGRESS_STATUSES = new Set(["completed", "cancelled", "failed"]);

export function isTerminalKernelProgressStatus(status: unknown): boolean {
  return TERMINAL_PROGRESS_STATUSES.has(String(status || ""));
}

export function progressTitle(status: string): string {
  switch (status) {
    case "step_started":
      return "Kernel step running";
    case "step_completed":
      return "Kernel step completed";
    case "waiting_for_user":
      return "Waiting for your input";
    case "blocked":
      return "Kernel blocked";
    case "retrying":
      return "Kernel retrying";
    case "cancelled":
      return "Kernel cancelled";
    case "completed":
      return "Kernel workflow completed";
    case "failed":
      return "Kernel workflow failed";
    default:
      return "Kernel progress";
  }
}

export function progressVisualState(status: string): string {
  switch (status) {
    case "step_started":
    case "running":
    case "running_unknown":
      return "running";
    case "step_completed":
      return "done";
    case "waiting_for_user":
      return "waiting";
    case "blocked":
      return "warning";
    case "retrying":
      return "running";
    case "cancelled":
      return "warning";
    case "completed":
      return "done";
    case "failed":
    case "error":
      return "error";
    default:
      return "idle";
  }
}

export function progressStatusText(status: string): string {
  switch (status) {
    case "step_started":
    case "running":
    case "running_unknown":
      return "Running";
    case "step_completed":
      return "Done";
    case "waiting_for_user":
      return "Waiting";
    case "blocked":
      return "Blocked";
    case "retrying":
      return "Retrying";
    case "cancelled":
      return "Cancelled";
    case "completed":
      return "Completed";
    case "failed":
      return "Failed";
    default:
      return status;
  }
}
