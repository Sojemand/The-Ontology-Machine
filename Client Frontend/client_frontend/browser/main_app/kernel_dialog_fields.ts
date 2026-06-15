import type { KernelUserInteractionRequest } from "../types/index.ts";
import { manualSourcePathCount, stringValue, suggestedFolderName, usesChoiceList } from "./kernel_dialog_options.ts";
import { buildCheckboxList, buildChoiceList, buildManualSourcePathList } from "./kernel_dialog_lists.ts";
import type { DraftStateUpdater, KernelDialogDraftState, TextInputOptions } from "./kernel_dialog_types.ts";
import { buildTextInput } from "./kernel_dialog_text_input.ts";

export { buildTextInput } from "./kernel_dialog_text_input.ts";

export function buildDialogBody(
  document: Document,
  request: KernelUserInteractionRequest,
  draftState: KernelDialogDraftState,
  updateDraftState: DraftStateUpdater,
  disabled = false
): HTMLElement[] {
  if (request.dialog_type === "folder_create_picker" && request.interaction_function === "name_artifact_root_folder") {
    return [buildTextInput(
      document,
      request.interaction_request_id,
      "text-value",
      "Folder name",
      draftState.textValue ?? suggestedFolderName(request),
      updateDraftState,
      {},
      disabled
    )];
  }
  if (request.dialog_type === "folder_picker" || request.dialog_type === "folder_create_picker" || request.dialog_type === "database_path_picker") {
    return [buildTextInput(
      document,
      request.interaction_request_id,
      "path-value",
      "Path",
      draftState.pathValue ?? stringValue(request.prefilled_values?.path_value || request.prefilled_values?.path),
      updateDraftState,
      {},
      disabled
    )];
  }
  if (request.dialog_type === "text_input") {
    return [buildTextInput(
      document,
      request.interaction_request_id,
      "text-value",
      textInputLabel(request),
      draftState.textValue ?? stringValue(request.prefilled_values?.text_value),
      updateDraftState,
      textInputOptions(request),
      disabled
    )];
  }
  if (request.dialog_type === "database_list_picker") {
    const manualCount = manualSourcePathCount(request);
    return [manualCount > 0
      ? buildManualSourcePathList(document, request, draftState, updateDraftState, manualCount, disabled)
      : buildCheckboxList(document, request, draftState, updateDraftState, disabled)];
  }
  if (usesChoiceList(request.dialog_type) || request.dialog_type === "recovery_dialog") {
    return [buildChoiceList(document, request)];
  }
  return [];
}

function textInputLabel(request: KernelUserInteractionRequest): string {
  if (request.interaction_function === "choose_merge_database_count") return "Database count";
  if (request.interaction_function === "name_database") return "Database name";
  return "Text";
}

function textInputOptions(request: KernelUserInteractionRequest): TextInputOptions {
  if (request.interaction_function === "name_database") {
    return { helperText: "Optional .db. If omitted, the Kernel appends .db automatically." };
  }
  return request.interaction_function === "choose_merge_database_count" ? {} : { multiline: true };
}
