import type { RegexDescriptor } from "../../types/frontend_policy.ts";
import type { RegexListDomRefs } from "./types.ts";

function escapeAttribute(value: string): string {
  return value.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
}

function readDraftRows(list: RegexListDomRefs): RegexDescriptor[] {
  const rows = Array.from(list.rowsEl?.querySelectorAll<HTMLElement>("[data-regex-row]") || []);
  return rows.map((row) => ({
    pattern: row.querySelector<HTMLInputElement>('[data-regex-role="pattern"]')?.value || "",
    flags: (row.querySelector<HTMLInputElement>('[data-regex-role="flags"]')?.value || "").trim()
  }));
}

function buildRowMarkup(listPath: string, index: number, descriptor: RegexDescriptor): string {
  return [
    `<div class="policy-regex-row" data-regex-row="${index}" data-policy-path-prefix="${listPath}[${index}]">`,
    `<input type="text" value="${escapeAttribute(descriptor.pattern)}" placeholder="Pattern" data-regex-role="pattern" data-policy-path="${listPath}[${index}].pattern" />`,
    `<input type="text" value="${escapeAttribute(descriptor.flags)}" placeholder="Flags" maxlength="8" class="policy-regex-flags" data-regex-role="flags" data-policy-path="${listPath}[${index}].flags" />`,
    `<button type="button" class="ghost-button" data-remove-regex="${index}">Remove</button>`,
    "</div>"
  ].join("");
}

export function renderRegexRows(list: RegexListDomRefs, listPath: string, descriptors: RegexDescriptor[]): void {
  if (!list.rowsEl) {
    return;
  }
  list.rowsEl.innerHTML = descriptors.length
    ? descriptors.map((descriptor, index) => buildRowMarkup(listPath, index, descriptor)).join("")
    : '<p class="muted policy-empty">No regex rules.</p>';
}

export function collectRegexDraftRows(list: RegexListDomRefs): RegexDescriptor[] {
  return readDraftRows(list);
}

export function bindRegexList(list: RegexListDomRefs, listPath: string): void {
  list.addButton?.addEventListener("click", () => {
    renderRegexRows(list, listPath, [...readDraftRows(list), { pattern: "", flags: "" }]);
  });
  list.rowsEl?.addEventListener("click", (event) => {
    const button = (event.target as HTMLElement | null)?.closest<HTMLButtonElement>("[data-remove-regex]");
    if (!button) {
      return;
    }
    const index = Number(button.dataset.removeRegex);
    const rows = readDraftRows(list);
    rows.splice(Number.isInteger(index) ? index : -1, 1);
    renderRegexRows(list, listPath, rows);
  });
}
