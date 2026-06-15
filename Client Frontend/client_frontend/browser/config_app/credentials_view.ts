import type { ConfigResponse } from "../types/index.ts";
import type { CredentialDomRefs } from "./types.ts";

function text(value: unknown, fallback = "-"): string {
  const nextValue = String(value || "").trim();
  return nextValue || fallback;
}

export function queryCredentialDom(document: Document): CredentialDomRefs {
  return {
    statusEl: document.querySelector<HTMLParagraphElement>("#oauth-status"),
    modeEl: document.querySelector<HTMLElement>("#oauth-mode"),
    accountEl: document.querySelector<HTMLElement>("#oauth-account"),
    expiresEl: document.querySelector<HTMLElement>("#oauth-expires"),
    refreshEl: document.querySelector<HTMLElement>("#oauth-refresh"),
    loginButton: document.querySelector<HTMLButtonElement>("#oauth-login"),
    logoutButton: document.querySelector<HTMLButtonElement>("#oauth-logout")
  };
}

export function hasHealthyOAuth(config: ConfigResponse | null): boolean {
  return config?.credential_state?.auth_mode === "oauth" && config.credential_state?.oauth_session?.status === "connected";
}

export function applyCredentialView(dom: CredentialDomRefs, config: ConfigResponse): void {
  const state = config.credential_state;
  const session = state?.oauth_session;
  if (dom.statusEl) dom.statusEl.textContent = session?.status_message || "No active OAuth login.";
  if (dom.modeEl) dom.modeEl.textContent = state?.auth_mode === "oauth" ? "OAuth active" : state?.oauth_supported === false ? "Provider API" : "API key fallback";
  if (dom.accountEl) dom.accountEl.textContent = text(session?.account_label);
  if (dom.expiresEl) dom.expiresEl.textContent = text(session?.expires_at);
  if (dom.refreshEl) dom.refreshEl.textContent = session?.has_refresh_token ? "Present" : "Not present";
  if (dom.loginButton) dom.loginButton.disabled = hasHealthyOAuth(config) || state?.oauth_supported === false;
  if (dom.logoutButton) dom.logoutButton.disabled = !session || session.status === "logged_out";
}
