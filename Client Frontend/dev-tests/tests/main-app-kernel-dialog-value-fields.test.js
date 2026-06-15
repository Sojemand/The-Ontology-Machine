import test from "node:test";

import { interactionRequest } from "./pipeline-agent-test-fixtures.js";
import { assertSingleDialogResponseValue } from "./main-app-kernel-dialog-support.js";

test("kernel value dialogs submit exactly one response value field", async () => {
  const cases = [
    {
          dialogType: "folder_picker",
          request: interactionRequest({ dialog_type: "folder_picker" }),
          interact(document) {
            document.querySelector("#path-value").value = "C:\\Workspace\\Chosen";
            document.querySelector("#kernel-dialog-actions button")?.click();
          },
          expectedField: "path_value"
        },
    {
          dialogType: "folder_create_picker",
          request: interactionRequest({ dialog_type: "folder_create_picker" }),
          interact(document) {
            document.querySelector("#path-value").value = "C:\\Workspace\\Created";
            document.querySelector("#kernel-dialog-actions button")?.click();
          },
          expectedField: "path_value"
        },
    {
          dialogType: "name_artifact_root_folder",
          request: interactionRequest({
            interaction_function: "name_artifact_root_folder",
            interaction_kind: "input",
            dialog_type: "folder_create_picker",
            response_shape: "path_value_or_text_value",
            prefilled_values: { text_value: "Artifact Tree" }
          }),
          interact(document) {
            document.querySelector("#text-value").value = "File Optimizer";
            document.querySelector("#kernel-dialog-actions button")?.click();
          },
          expectedField: "text_value"
        },
    {
          dialogType: "text_input",
          request: interactionRequest({ dialog_type: "text_input" }),
          interact(document) {
            document.querySelector("#text-value").value = "Fantasy notes";
            document.querySelector("#kernel-dialog-actions button")?.click();
          },
          expectedField: "text_value"
        },
    {
          dialogType: "choose_merge_database_count",
          request: interactionRequest({
            interaction_function: "choose_merge_database_count",
            interaction_kind: "input",
            dialog_type: "text_input",
            response_shape: "text_value"
          }),
          interact(document) {
            document.querySelector("#text-value").value = "3";
            document.querySelector("#kernel-dialog-actions button")?.click();
          },
          expectedField: "text_value"
        },
    {
          dialogType: "database_path_picker",
          request: interactionRequest({ dialog_type: "database_path_picker" }),
          interact(document) {
            document.querySelector("#path-value").value = "C:\\Workspace\\Corpus\\corpus.db";
            document.querySelector("#kernel-dialog-actions button")?.click();
          },
          expectedField: "path_value"
        },
    {
          dialogType: "active_database_choice",
          request: interactionRequest({
            dialog_type: "active_database_choice",
            options: [{ choice_id: "db_active", label: "Use active database" }]
          }),
          interact(document) {
            document.querySelector("#kernel-dialog-actions button")?.click();
          },
          expectedField: "choice_id"
        },
    {
          dialogType: "database_list_picker",
          request: interactionRequest({
            dialog_type: "database_list_picker",
            options: [
              { choice_id: "C:\\DbOne" , label: "DbOne" },
              { choice_id: "C:\\DbTwo" , label: "DbTwo" }
            ]
          }),
          interact(document) {
            document.querySelectorAll('input[data-kernel-db-choice="true"]').forEach((input) => {
              input.checked = true;
            });
            document.querySelector("#kernel-dialog-actions button")?.click();
          },
          expectedField: "selected_database_paths"
        }
  ];

  for (const testCase of cases) {
    await assertSingleDialogResponseValue(testCase);
  }
});
