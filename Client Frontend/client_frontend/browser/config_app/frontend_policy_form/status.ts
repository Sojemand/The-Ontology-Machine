import type { StatusMode } from "../types.ts";
import type { FrontendPolicyDiagnostics } from "../../types/frontend_policy.ts";
import type { FrontendPolicyDomRefs } from "./types.ts";

function setStatusText(element: HTMLElement | null, text: string, mode: StatusMode): void {
  if (!element) {
    return;
  }
  element.textContent = text;
  element.style.color = mode === "ok" ? "var(--success)" : mode === "error" ? "var(--danger)" : "var(--text-muted)";
}

function isPathMatch(candidate: string | null, path: string): boolean {
  return Boolean(candidate && (path === candidate || path.startsWith(`${candidate}.`) || path.startsWith(`${candidate}[`)));
}

function findPolicyTarget(rootEl: HTMLElement | null, policyPath?: string): HTMLElement | null {
  if (!rootEl || !policyPath) {
    return null;
  }
  const exactMatch = Array.from(rootEl.querySelectorAll<HTMLElement>("[data-policy-path]"))
    .find((element) => element.dataset.policyPath === policyPath);
  if (exactMatch) {
    return exactMatch;
  }
  const prefixMatch = Array.from(rootEl.querySelectorAll<HTMLElement>("[data-policy-path-prefix],[data-policy-path]"))
    .sort((left, right) => (right.dataset.policyPathPrefix || right.dataset.policyPath || "").length - (left.dataset.policyPathPrefix || left.dataset.policyPath || "").length)
    .find((element) => isPathMatch(element.dataset.policyPathPrefix || element.dataset.policyPath || null, policyPath));
  if (!prefixMatch) {
    return null;
  }
  if (prefixMatch.matches("input, textarea, select, button")) {
    return prefixMatch;
  }
  return prefixMatch.querySelector<HTMLElement>("input, textarea, select")
    || prefixMatch.querySelector<HTMLElement>("button")
    || prefixMatch;
}

function activateConfigTabForTarget(target: HTMLElement): void {
  const panel = target.closest<HTMLElement>("[data-config-panel]");
  const panelName = panel?.dataset.configPanel;
  if (!panelName) return;
  const document = target.ownerDocument;
  document.querySelectorAll<HTMLButtonElement>("[data-config-tab]").forEach((button) => {
    const active = button.dataset.configTab === panelName;
    button.setAttribute("aria-selected", String(active));
  });
  document.querySelectorAll<HTMLElement>("[data-config-panel]").forEach((candidate) => {
    candidate.hidden = candidate.dataset.configPanel !== panelName;
  });
}

function activatePromptTabForTarget(target: HTMLElement): void {
  const panel = target.closest<HTMLElement>("[data-policy-prompt-panel]");
  const panelName = panel?.dataset.policyPromptPanel;
  const root = panel?.parentElement;
  if (!panelName || !root) return;
  root.querySelectorAll<HTMLButtonElement>("[data-policy-prompt-tab]").forEach((button) => {
    button.setAttribute("aria-selected", String(button.dataset.policyPromptTab === panelName));
  });
  root.querySelectorAll<HTMLElement>("[data-policy-prompt-panel]").forEach((candidate) => {
    candidate.hidden = candidate.dataset.policyPromptPanel !== panelName;
  });
}

export function clearFrontendPolicyHighlights(dom: FrontendPolicyDomRefs): void {
  dom.rootEl?.querySelectorAll(".policy-field-error,.policy-group-error").forEach((element) => {
    element.classList.remove("policy-field-error", "policy-group-error");
  });
}

export function buildDiagnosticsMessage(diagnostics?: FrontendPolicyDiagnostics): string {
  if (!diagnostics) {
    return "";
  }
  return `${diagnostics.message} The form shows default values; saving replaces frontend_policy.json.`;
}

export function setFrontendPolicyStatus(dom: FrontendPolicyDomRefs, text: string, mode: StatusMode = "idle", policyPath?: string): void {
  clearFrontendPolicyHighlights(dom);
  setStatusText(dom.statusEl, text, mode);
  if (mode !== "error") {
    return;
  }
  const target = findPolicyTarget(dom.rootEl, policyPath);
  if (!target) {
    return;
  }
  activateConfigTabForTarget(target);
  activatePromptTabForTarget(target);
  target.classList.add("policy-field-error");
  (target.closest<HTMLElement>(".policy-group") || target).classList.add("policy-group-error");
  target.scrollIntoView?.({ block: "center", behavior: "smooth" });
  if ("focus" in target) {
    target.focus();
  }
}
