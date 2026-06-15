import type { KernelUserInteractionRequest } from "../types/index.ts";

export interface NormalizedKernelOption {
  choiceId: string;
  label: string;
  description: string;
}

export function normalizedOptions(request: KernelUserInteractionRequest): NormalizedKernelOption[] {
  return (Array.isArray(request.options) ? request.options : []).map((option, index) => {
    const raw = option as Record<string, unknown>;
    const choiceId = String(raw["choice_id"] || raw["recovery_id"] || raw["id"] || raw["agent_tool"] || raw["label"] || `option_${index}`);
    return {
      choiceId,
      label: String(raw["label"] || raw["title"] || raw["description"] || choiceId),
      description: String(raw["description"] || raw["user_visible_summary"] || raw["summary"] || "")
    };
  });
}

export function usesChoiceList(dialogType: KernelUserInteractionRequest["dialog_type"]): boolean {
  return [
    "active_database_choice",
    "update_mode_choice"
  ].includes(dialogType);
}

export function bodyRenderKey(request: KernelUserInteractionRequest): string {
  if (request.dialog_type === "database_list_picker") {
    return `${request.interaction_request_id}:${request.dialog_type}:${manualSourcePathCount(request)}:${optionsSignature(request)}`;
  }
  return `${request.interaction_request_id}:${request.dialog_type}`;
}

export function actionRenderKey(request: KernelUserInteractionRequest): string {
  if (request.dialog_type === "database_list_picker" || usesChoiceList(request.dialog_type) || request.dialog_type === "recovery_dialog") {
    return `${request.interaction_request_id}:${request.dialog_type}:${manualSourcePathCount(request)}:${optionsSignature(request)}`;
  }
  return `${request.interaction_request_id}:${request.dialog_type}`;
}

export function manualSourcePathCount(request: KernelUserInteractionRequest): number {
  const value = request.prefilled_values?.manual_path_count;
  const count = typeof value === "number" ? value : Number.parseInt(String(value || ""), 10);
  return Number.isFinite(count) && count > 0 ? Math.min(50, count) : 0;
}

export function stringValue(value: unknown): string {
  return typeof value === "string" ? value : "";
}

export function suggestedFolderName(request: KernelUserInteractionRequest): string {
  const explicit = stringValue(request.prefilled_values?.text_value);
  if (explicit) return explicit;
  const pathValue = stringValue(request.prefilled_values?.path_value || request.prefilled_values?.path);
  if (!pathValue) return "";
  const normalized = pathValue.replace(/[\\/]+$/, "");
  const parts = normalized.split(/[\\/]+/).filter(Boolean);
  return parts[parts.length - 1] || "";
}

function optionsSignature(request: KernelUserInteractionRequest): string {
  return JSON.stringify(normalizedOptions(request));
}
