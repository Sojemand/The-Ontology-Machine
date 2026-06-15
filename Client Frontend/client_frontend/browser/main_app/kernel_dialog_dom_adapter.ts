import type { KernelDialogState } from "../types/index.ts";
import type { DomRefs, KernelPendingInteractionState } from "./types.ts";
import { buildDialogActions } from "./kernel_dialog_actions.ts";
import { buildDialogBody } from "./kernel_dialog_fields.ts";
import { actionRenderKey, bodyRenderKey } from "./kernel_dialog_options.ts";
import type { KernelDialogCallbacks, KernelDialogDraftState } from "./kernel_dialog_types.ts";

type KernelDialogDomRefs = DomRefs & Required<Pick<DomRefs, "kernelDialogPanelEl" | "kernelDialogTitleEl" | "kernelDialogSummaryEl" | "kernelDialogBodyEl" | "kernelDialogActionsEl" | "kernelDialogStatusEl">>;

export function createKernelDialogDomAdapter(document: Document, dom: DomRefs) {
  let renderedRequestId = "";
  let renderedBodyKey = "";
  let renderedActionKey = "";
  const draftStateByRequestId = new Map<string, KernelDialogDraftState>();

  const clearRenderedDialog = () => {
    renderedRequestId = "";
    renderedBodyKey = "";
    renderedActionKey = "";
  };

  const updateDraftState = (requestId: string, patch: Partial<KernelDialogDraftState>) => {
    if (!requestId) return;
    draftStateByRequestId.set(requestId, {
      ...(draftStateByRequestId.get(requestId) || {}),
      ...patch
    });
  };

  const captureDraftState = (requestId: string) => {
    if (!requestId) return;
    const pathInput = document.querySelector<HTMLInputElement>("#path-value");
    const textInput = document.querySelector<HTMLInputElement | HTMLTextAreaElement>("#text-value");
    const sourcePathInputs = Array.from(document.querySelectorAll<HTMLInputElement>('input[data-kernel-source-path="true"]'));
    const checkboxes = Array.from(document.querySelectorAll<HTMLInputElement>('input[data-kernel-db-choice="true"]'));
    if (pathInput) updateDraftState(requestId, { pathValue: pathInput.value });
    if (textInput) updateDraftState(requestId, { textValue: textInput.value });
    if (sourcePathInputs.length) {
      updateDraftState(requestId, {
        selectedDatabasePaths: sourcePathInputs.map((input) => String(input.value))
      });
    }
    if (checkboxes.length) {
      updateDraftState(requestId, {
        selectedDatabasePaths: checkboxes.filter((input) => input.checked).map((input) => String(input.value))
      });
    }
  };

  return {
    render(dialogState: KernelDialogState | null, statusText = "", pendingInteraction: KernelPendingInteractionState | null, callbacks: KernelDialogCallbacks): void {
      if (!hasKernelDialogDom(dom)) return;
      if (!dialogState?.interaction_request) {
        if (renderedRequestId) draftStateByRequestId.delete(renderedRequestId);
        clearDialogDom(dom);
        clearRenderedDialog();
        return;
      }

      const request = dialogState.interaction_request;
      const requestId = String(request.interaction_request_id || "");
      const isPending = Boolean(pendingInteraction?.requestId && pendingInteraction.requestId === requestId);
      const nextBodyKey = `${bodyRenderKey(request)}:${isPending ? "pending" : "ready"}`;
      const nextActionKey = `${actionRenderKey(request)}:${isPending ? pendingInteraction?.actionLabel || "pending" : "ready"}`;
      const sameRequest = requestId && requestId === renderedRequestId;

      if (sameRequest) {
        captureDraftState(requestId);
      } else if (renderedRequestId) {
        draftStateByRequestId.delete(renderedRequestId);
      }

      dom.kernelDialogPanelEl.hidden = false;
      dom.kernelDialogPanelEl.setAttribute("aria-busy", String(isPending));
      setDatasetState(dom.kernelDialogPanelEl, dialogState.status);
      setTextIfChanged(dom.kernelDialogTitleEl, request.user_visible_title || "Kernel dialog");
      setTextIfChanged(dom.kernelDialogSummaryEl, request.user_visible_summary || "");
      setTextIfChanged(dom.kernelDialogStatusEl, statusForRender(dialogState.status, statusText, pendingInteraction, isPending));

      if (!sameRequest || renderedBodyKey !== nextBodyKey) {
        dom.kernelDialogBodyEl.replaceChildren(...buildDialogBody(document, request, draftStateByRequestId.get(requestId) || {}, updateDraftState, isPending));
      }
      if (!sameRequest || renderedActionKey !== nextActionKey) {
        dom.kernelDialogActionsEl.replaceChildren(...buildDialogActions(document, request, callbacks, pendingInteraction));
      }
      renderedRequestId = requestId;
      renderedBodyKey = nextBodyKey;
      renderedActionKey = nextActionKey;
    }
  };
}

function hasKernelDialogDom(dom: DomRefs): dom is KernelDialogDomRefs {
  return Boolean(dom.kernelDialogPanelEl && dom.kernelDialogTitleEl && dom.kernelDialogSummaryEl && dom.kernelDialogBodyEl && dom.kernelDialogActionsEl && dom.kernelDialogStatusEl);
}

function clearDialogDom(dom: KernelDialogDomRefs): void {
  dom.kernelDialogPanelEl.hidden = true;
  dom.kernelDialogTitleEl.textContent = "";
  dom.kernelDialogSummaryEl.textContent = "";
  dom.kernelDialogBodyEl.replaceChildren();
  dom.kernelDialogActionsEl.replaceChildren();
  dom.kernelDialogStatusEl.textContent = "";
  dom.kernelDialogPanelEl.removeAttribute("aria-busy");
}

function statusForRender(
  dialogStatus: KernelDialogState["status"],
  statusText: string,
  pendingInteraction: KernelPendingInteractionState | null,
  isPending: boolean
): string {
  if (isPending) return pendingInteraction?.statusText || "Input sent. Kernel is processing the next step...";
  return statusText || (dialogStatus === "stale" ? "This dialog is stale. Fetch the latest Kernel state." : "");
}

function setTextIfChanged(element: HTMLElement, nextText: string): void {
  if (element.textContent !== nextText) element.textContent = nextText;
}

function setDatasetState(element: HTMLElement, nextState: string): void {
  if (element.dataset.state !== nextState) element.dataset.state = nextState;
}
