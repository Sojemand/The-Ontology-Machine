import test from "node:test";

import { interactionRequest } from "./pipeline-agent-test-fixtures.js";
import { assertSingleDialogResponseValue } from "./main-app-kernel-dialog-support.js";

test("kernel decision and notice dialogs submit exactly one response value field", async () => {
  const cases = [
    {
          dialogType: "database_list_picker_manual_paths",
          request: interactionRequest({
            interaction_function: "choose_databases_to_merge",
            interaction_kind: "selection",
            dialog_type: "database_list_picker",
            response_shape: "selected_database_paths",
            prefilled_values: { manual_path_count: 2, path_value_kind: "artifact_tree_root" },
            options: []
          }),
          interact(document) {
            document.querySelector("#source-path-value-1").value = "C:\\Workspace\\TreeA";
            document.querySelector("#source-path-value-2").value = "C:\\Workspace\\TreeB";
            document.querySelector("#kernel-dialog-actions button")?.click();
          },
          expectedField: "selected_database_paths"
        },
    {
          dialogType: "input_presence_confirmation",
          request: interactionRequest({ dialog_type: "input_presence_confirmation" }),
          interact(document) {
            document.querySelector("#kernel-dialog-actions button")?.click();
          },
          expectedField: "confirmation_decision"
        },
    {
          dialogType: "update_mode_choice",
          request: interactionRequest({
            dialog_type: "update_mode_choice",
            options: [{ choice_id: "additive", label: "Additive update" }]
          }),
          interact(document) {
            document.querySelector("#kernel-dialog-actions button")?.click();
          },
          expectedField: "choice_id"
        },
    {
          dialogType: "generic_confirmation",
          request: interactionRequest({ dialog_type: "generic_confirmation" }),
          interact(document) {
            document.querySelector("#kernel-dialog-actions button")?.click();
          },
          expectedField: "confirmation_decision"
        },
    {
          dialogType: "recovery_dialog",
          request: interactionRequest({
            dialog_type: "recovery_dialog",
            options: [{ recovery_id: "rec_retry", label: "Retry workflow" }]
          }),
          interact(document) {
            document.querySelector("#kernel-dialog-actions button")?.click();
          },
          expectedField: "recovery_id"
        },
    {
          dialogType: "blocker_notice",
          request: interactionRequest({ dialog_type: "blocker_notice" }),
          interact(document) {
            document.querySelector("#kernel-dialog-actions button")?.click();
          },
          expectedField: "cancellation_reason"
        },
    {
          dialogType: "progress_notice",
          request: interactionRequest({ dialog_type: "progress_notice" }),
          interact(document) {
            document.querySelector("#kernel-dialog-actions button")?.click();
          },
          expectedField: "cancellation_reason"
        },
    {
          dialogType: "support_bundle_notice",
          request: interactionRequest({ dialog_type: "support_bundle_notice" }),
          interact(document) {
            document.querySelector("#kernel-dialog-actions button")?.click();
          },
          expectedField: "cancellation_reason"
        }
  ];

  for (const testCase of cases) {
    await assertSingleDialogResponseValue(testCase);
  }
});
