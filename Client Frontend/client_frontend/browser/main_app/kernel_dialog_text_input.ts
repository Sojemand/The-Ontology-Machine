import type { DraftStateUpdater, TextInputOptions } from "./kernel_dialog_types.ts";

export function buildTextInput(
  document: Document,
  requestId: string,
  id: string,
  labelText: string,
  value = "",
  updateDraftState: DraftStateUpdater,
  options: TextInputOptions = {},
  disabled = false
): HTMLElement {
  const multiline = options.multiline === true;
  const wrapper = document.createElement("label");
  wrapper.className = "kernel-dialog-field";
  const label = document.createElement("span");
  label.textContent = labelText;
  wrapper.appendChild(label);
  const input = multiline ? document.createElement("textarea") : document.createElement("input");
  input.id = id;
  input.className = "kernel-dialog-input";
  input.disabled = disabled;
  if (!multiline) input.setAttribute("type", "text");
  input.value = value;
  input.addEventListener("input", () => {
    updateDraftState(requestId, id === "path-value" ? { pathValue: input.value } : { textValue: input.value });
  });
  wrapper.appendChild(input);
  if (options.helperText) {
    const hint = document.createElement("small");
    hint.className = "kernel-dialog-hint";
    hint.textContent = options.helperText;
    wrapper.appendChild(hint);
  }
  return wrapper;
}
