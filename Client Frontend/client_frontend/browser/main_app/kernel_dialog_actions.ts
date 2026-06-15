import type { KernelUserInteractionRequest } from "../types/index.ts";
import { normalizedOptions, usesChoiceList } from "./kernel_dialog_options.ts";
import type { KernelDialogCallbacks, PendingKernelInteraction } from "./kernel_dialog_types.ts";

export function buildDialogActions(
  document: Document,
  request: KernelUserInteractionRequest,
  callbacks: KernelDialogCallbacks,
  pendingInteraction: PendingKernelInteraction
): HTMLElement[] {
  const actions: HTMLElement[] = [];
  const isPending = Boolean(pendingInteraction?.requestId && pendingInteraction.requestId === request.interaction_request_id);
  if (request.dialog_type === "folder_create_picker" && request.interaction_function === "name_artifact_root_folder") {
    actions.push(textValueSubmitButton(document, "Submit name", callbacks, pendingInteraction, isPending));
  } else if (request.dialog_type === "folder_picker" || request.dialog_type === "folder_create_picker" || request.dialog_type === "database_path_picker") {
    actions.push(pathValueSubmitButton(document, callbacks, pendingInteraction, isPending));
  } else if (request.dialog_type === "text_input") {
    actions.push(textInputSubmitButton(document, request, callbacks, pendingInteraction, isPending));
  } else if (request.dialog_type === "database_list_picker") {
    actions.push(databaseSelectionSubmitButton(document, callbacks, pendingInteraction, isPending));
  } else if (request.dialog_type === "input_presence_confirmation" || request.dialog_type === "generic_confirmation") {
    actions.push(button(document, "Confirm", () => callbacks.onSubmit({ confirmation_decision: "confirmed" }, "Confirm"), pendingInteraction, isPending));
    actions.push(button(document, "Decline", () => callbacks.onSubmit({ confirmation_decision: "rejected" }, "Decline"), pendingInteraction, isPending));
  } else if (usesChoiceList(request.dialog_type)) {
    for (const option of normalizedOptions(request)) {
      actions.push(button(document, option.label, () => callbacks.onSubmit({ choice_id: option.choiceId }, option.label), pendingInteraction, isPending));
    }
  } else if (request.dialog_type === "recovery_dialog") {
    for (const option of normalizedOptions(request)) {
      actions.push(button(document, option.label, () => callbacks.onSubmit({ recovery_id: option.choiceId }, option.label), pendingInteraction, isPending));
    }
  }
  appendFallbackAction(document, actions, callbacks, pendingInteraction, isPending);
  return actions;
}

function textValueSubmitButton(
  document: Document,
  label: string,
  callbacks: KernelDialogCallbacks,
  pendingInteraction: PendingKernelInteraction,
  disabled: boolean
): HTMLButtonElement {
  return button(document, label, () => {
    const input = document.querySelector<HTMLInputElement>("#text-value");
    callbacks.onSubmit({ text_value: String(input?.value || "") }, label);
  }, pendingInteraction, disabled);
}

function pathValueSubmitButton(
  document: Document,
  callbacks: KernelDialogCallbacks,
  pendingInteraction: PendingKernelInteraction,
  disabled: boolean
): HTMLButtonElement {
  const label = "Submit path";
  return button(document, label, () => {
    const input = document.querySelector<HTMLInputElement>("#path-value");
    callbacks.onSubmit({ path_value: String(input?.value || "") }, label);
  }, pendingInteraction, disabled);
}

function textInputSubmitButton(
  document: Document,
  request: KernelUserInteractionRequest,
  callbacks: KernelDialogCallbacks,
  pendingInteraction: PendingKernelInteraction,
  disabled: boolean
): HTMLButtonElement {
  const label = request.interaction_function === "name_database"
    ? "Submit database name"
    : request.interaction_function === "choose_merge_database_count"
      ? "Submit count"
      : "Submit text";
  return button(document, label, () => {
    const input = document.querySelector<HTMLInputElement | HTMLTextAreaElement>("#text-value");
    const value = request.interaction_function === "name_database" || request.interaction_function === "choose_merge_database_count"
      ? String(input?.value || "").trim()
      : String(input?.value || "");
    callbacks.onSubmit({ text_value: value }, label);
  }, pendingInteraction, disabled);
}

function databaseSelectionSubmitButton(
  document: Document,
  callbacks: KernelDialogCallbacks,
  pendingInteraction: PendingKernelInteraction,
  disabled: boolean
): HTMLButtonElement {
  const label = "Submit selection";
  return button(document, label, () => {
    const manualInputs = Array.from(document.querySelectorAll<HTMLInputElement>('input[data-kernel-source-path="true"]'));
    const selected = manualInputs.length
      ? manualInputs.map((input) => String(input.value).trim()).filter(Boolean)
      : Array.from(document.querySelectorAll<HTMLInputElement>('input[data-kernel-db-choice="true"]:checked'))
        .map((input) => String(input.value))
        .filter(Boolean);
    callbacks.onSubmit({ selected_database_paths: selected }, label);
  }, pendingInteraction, disabled);
}

function appendFallbackAction(
  document: Document,
  actions: HTMLElement[],
  callbacks: KernelDialogCallbacks,
  pendingInteraction: PendingKernelInteraction,
  disabled: boolean
): void {
  if (!actions.length) {
    actions.push(button(document, "Close", () => callbacks.onCancel({ response_status: "closed", cancellation_reason: "dialog_closed" }, "Close"), pendingInteraction, disabled));
  } else {
    actions.push(button(document, "Cancel", () => callbacks.onCancel({ response_status: "cancelled", cancellation_reason: "user_cancelled" }, "Cancel"), pendingInteraction, disabled));
  }
}

function button(
  document: Document,
  text: string,
  onClick: () => void,
  pendingInteraction: PendingKernelInteraction = null,
  disabled = false
): HTMLButtonElement {
  const element = document.createElement("button");
  element.type = "button";
  element.className = "ghost-button kernel-dialog-button";
  element.textContent = pendingInteraction?.actionLabel === text ? "Processing..." : text;
  element.disabled = disabled;
  element.addEventListener("click", onClick);
  return element;
}
