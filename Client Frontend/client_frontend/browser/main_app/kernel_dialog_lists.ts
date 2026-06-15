import type { KernelUserInteractionRequest } from "../types/index.ts";
import { normalizedOptions } from "./kernel_dialog_options.ts";
import type { DraftStateUpdater, KernelDialogDraftState } from "./kernel_dialog_types.ts";
import { buildTextInput } from "./kernel_dialog_text_input.ts";

export function buildChoiceList(document: Document, request: KernelUserInteractionRequest): HTMLElement {
  const list = document.createElement("div");
  list.className = "kernel-dialog-choice-list";
  for (const option of normalizedOptions(request)) {
    const row = document.createElement("div");
    row.className = "kernel-dialog-choice";
    const title = document.createElement("strong");
    title.textContent = option.label;
    row.appendChild(title);
    if (option.description) {
      const detail = document.createElement("p");
      detail.textContent = option.description;
      row.appendChild(detail);
    }
    list.appendChild(row);
  }
  return list;
}

export function buildManualSourcePathList(
  document: Document,
  request: KernelUserInteractionRequest,
  draftState: KernelDialogDraftState,
  updateDraftState: DraftStateUpdater,
  count: number,
  disabled = false
): HTMLElement {
  const list = document.createElement("div");
  list.className = "kernel-dialog-choice-list";
  const values = Array.isArray(draftState.selectedDatabasePaths)
    ? draftState.selectedDatabasePaths
    : Array.isArray(request.prefilled_values?.selected_database_paths)
      ? request.prefilled_values.selected_database_paths.map((value) => String(value))
      : [];
  const inputs: HTMLInputElement[] = [];
  const syncDraftState = () => {
    updateDraftState(request.interaction_request_id, {
      selectedDatabasePaths: inputs.map((input) => String(input.value))
    });
  };
  for (let index = 0; index < count; index += 1) {
    const field = buildTextInput(
      document,
      request.interaction_request_id,
      `source-path-value-${index + 1}`,
      `Artifact Tree path ${index + 1}`,
      values[index] || "",
      updateDraftState,
      {},
      disabled
    ) as HTMLLabelElement;
    const input = field.querySelector<HTMLInputElement>("input");
    if (input) {
      input.dataset.kernelSourcePath = "true";
      input.addEventListener("input", syncDraftState);
      inputs.push(input);
    }
    list.appendChild(field);
  }
  return list;
}

export function buildCheckboxList(
  document: Document,
  request: KernelUserInteractionRequest,
  draftState: KernelDialogDraftState,
  updateDraftState: DraftStateUpdater,
  disabled = false
): HTMLElement {
  const list = document.createElement("div");
  list.className = "kernel-dialog-choice-list";
  const selected = new Set(Array.isArray(draftState.selectedDatabasePaths) ? draftState.selectedDatabasePaths : []);
  const inputs: HTMLInputElement[] = [];
  const syncDraftState = () => {
    updateDraftState(request.interaction_request_id, {
      selectedDatabasePaths: inputs.filter((input) => input.checked).map((input) => String(input.value))
    });
  };
  for (const option of normalizedOptions(request)) {
    const label = document.createElement("label");
    label.className = "kernel-dialog-checkbox";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = option.choiceId;
    input.dataset.kernelDbChoice = "true";
    input.checked = selected.has(option.choiceId);
    input.disabled = disabled;
    input.addEventListener("change", syncDraftState);
    inputs.push(input);
    label.appendChild(input);
    const text = document.createElement("span");
    text.textContent = option.label;
    label.appendChild(text);
    list.appendChild(label);
  }
  return list;
}
