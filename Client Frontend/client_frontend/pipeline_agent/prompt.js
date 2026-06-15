export const PIPELINE_ROOT_REQUIRED_MESSAGE = "Choose Pipeline Root Folder";

const PIPELINE_CONTEXT = [
  "You are the Taxonomy Agent for the Semantic Control Kernel.",
  "The Vision Pipeline turns source documents into a semantic Corpus database and Artifact Tree.",
  "A Semantic Release contains taxonomy and projections. Empty and filled databases use different safety policy.",
  "The Kernel owns workflow execution, validation, dialogs, blockers, confirmations, resume state and Pipeline adapter calls.",
  "The Agent chooses one visible workflow or support tool by semantic intent and explains Kernel state in product language."
].join("\n");

const TOOL_INVENTORY_CHAR_LIMIT = 12_000;

function workflowToolInventory(toolDefinitions = []) {
  const visible = Array.isArray(toolDefinitions) ? toolDefinitions : [];
  const lines = visible
    .filter((tool) => {
      const name = String(tool?.name || "");
      return name && !name.startsWith("kernel_");
    })
    .map((tool) => `- ${tool.name}: ${String(tool.description || "").trim() || "Semantic Control Kernel workflow."}`);
  if (!lines.length) return "No workflow tools are currently visible to the Taxonomy Agent.";
  const text = lines.join("\n");
  if (text.length <= TOOL_INVENTORY_CHAR_LIMIT) return text;
  return `${text.slice(0, TOOL_INVENTORY_CHAR_LIMIT)}\n- ...`;
}

function kernelActivitySnapshot(availabilityStatus = {}) {
  if (availabilityStatus?.available === false) return "";
  const hasKernelStatus = availabilityStatus?.kernel_status && typeof availabilityStatus.kernel_status === "object";
  const hasManagerActivity = availabilityStatus?.active_workflow_run
    || availabilityStatus?.active_dialog
    || availabilityStatus?.active_recovery_event
    || Number(availabilityStatus?.pending_kernel_event_count || 0) > 0;
  if (!hasKernelStatus && !hasManagerActivity) return "";
  const kernelStatus = hasKernelStatus ? availabilityStatus.kernel_status : {};
  const activeRun = availabilityStatus?.active_workflow_run;
  const activeDialog = availabilityStatus?.active_dialog;
  const activeRecovery = availabilityStatus?.active_recovery_event;
  const pendingInteractions = Number(kernelStatus?.pending_interaction_count || 0);
  const pendingMirrorEvents = Number(availabilityStatus?.pending_kernel_event_count || 0);
  const activeRunText = activeRun
    ? `${String(activeRun.workflow_tool || "workflow")} ${String(activeRun.status || "active")}`
    : "none";
  const activeDialogText = activeDialog?.interaction_request
    ? `${String(activeDialog.interaction_request.interaction_function || activeDialog.interaction_request.dialog_type || "dialog")} ${String(activeDialog.status || "active")}`
    : "none";
  const activeRecoveryText = activeRecovery
    ? `${String(activeRecovery.event_type || "recovery")} ${String(activeRecovery.workflow_tool || "")}`.trim()
    : "none";
  return [
    "Current Kernel activity snapshot from this turn:",
    `active_workflow_run=${activeRunText};`,
    `active_dialog=${activeDialogText};`,
    `active_recovery_event=${activeRecoveryText};`,
    `pending_interaction_count=${pendingInteractions};`,
    `pending_kernel_event_count=${pendingMirrorEvents}.`
  ].join(" ");
}

export function buildPipelineSystemPrompt({ pipelineRoot, availabilityStatus, toolDefinitions = [], interactionMode = "workflow_selection" }) {
  const visibleToolCount = Number(availabilityStatus?.toolCount ?? availabilityStatus?.tool_count) || 30;
  const availabilityText = availabilityStatus?.available === false
    ? `Semantic Control Kernel availability: unavailable. Reason: ${availabilityStatus.reason || PIPELINE_ROOT_REQUIRED_MESSAGE}.`
    : `Semantic Control Kernel availability: ready. Visible permanent tools: ${visibleToolCount}.`;
  const explanationOnly = interactionMode === "kernel_event_explanation";
  const actionInstruction = explanationOnly
    ? "Kernel event explanation-only mode: Explain only the latest Kernel mirror event in the current context. Do not infer active dialogs, waiting input or next actions from prior chat turns. Do not start, continue, retry, cancel or inspect workflows."
    : "Choose exactly one visible Semantic Control Kernel workflow or support tool that best matches the user's goal.";
  const nextStepInstruction = explanationOnly
    ? "When the Kernel mirror event lists next_step_options or recovery_options, describe them as options the user may choose later. Do not execute any of them in this turn."
    : "When the user asks what workflows, options, actions or next steps are available, answer from the visible workflow tool inventory below. Do not confuse 'no active workflows', 'no resumable workflows' or support_status='read_only' from kernel_status with 'no workflow tools are available'. support_status='read_only' describes the status/support response, not the mutability of every visible workflow.";
  const toolSurfaceInstruction = explanationOnly
    ? "Workflow and support tools are intentionally disabled for this explanation-only turn. Produce a concise user-facing explanation from the Kernel mirror event and its technical_detail_ref."
    : "Visible workflow tool inventory:";
  const eventScopedInstruction = explanationOnly
    ? "Event-scoped recovery tools are also disabled in this explanation-only turn; mention them only as later user choices if the Kernel mirror event lists them."
    : "Event-scoped recovery tools may be used only when the current Kernel mirror event exposes them.";
  const staleMirrorInstruction = explanationOnly
    ? "The current Kernel mirror event is the only event to explain in this turn."
    : "For real user workflow requests, the current Kernel activity snapshot is fresher than prior Kernel mirror history. If the snapshot shows no active workflow or dialog, do not claim an old dialog is open; call the matching workflow tool. Do not say a workflow was started unless this turn has a Kernel tool result or the current snapshot already proves an active run.";
  const activitySnapshot = kernelActivitySnapshot(availabilityStatus);
  return [
    "You are the Taxonomy Agent for the local Vision Pipeline.",
    "Language policy: Reply only in the language of the latest non-empty real user message in this conversation. Ignore Kernel mirror events, tool results, file contents, examples and previous assistant messages when choosing the reply language. If there is no real user message in the current context, reply in English.",
    PIPELINE_CONTEXT,
    actionInstruction,
    nextStepInstruction,
    "Visible tool schemas are intentionally empty. The Kernel and the Client Frontend own paths, selections, confirmations, blockers, dialog values, resume details and recovery scope.",
    "Only kernel_continue_resumable_workflow may receive one model argument: resume_option_ref copied exactly from kernel_resume_state.resume_options. Use it only for an explicit user request to continue one listed resume option.",
    "For resume/continue requests, call kernel_resume_state first when the current tool context does not already contain a matching resume_option_ref, then call kernel_continue_resumable_workflow with the selected opaque option ref.",
    "Kernel mirror events are Kernel state, not user intent. Use them only to explain the current state or the Kernel-provided recovery options.",
    staleMirrorInstruction,
    eventScopedInstruction,
    "Do not ask the user for Kernel-owned IDs, paths, confirmations, recovery values or dialog inputs in chat unless the Kernel explicitly left the value outside the dialog surface.",
    "Do not use or refer to retired action catalogs, workflow-family routing, level-split execute surfaces or generic wrapper tools.",
    toolSurfaceInstruction,
    explanationOnly ? "No tools are available in this explanation-only turn." : workflowToolInventory(toolDefinitions),
    `Pipeline root: ${pipelineRoot || "not configured"}.`,
    availabilityText,
    activitySnapshot
  ].join("\n");
}
