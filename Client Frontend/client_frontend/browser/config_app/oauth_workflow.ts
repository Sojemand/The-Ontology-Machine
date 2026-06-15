import type { ConfigResponse } from "../types/index.ts";
import type { ConfigDomAdapter } from "./types.ts";
import type { ConfigWorkflowState } from "./workflow_state.ts";

interface OAuthWorkflowDeps {
  api: {
    logoutOAuth: () => Promise<{ status: string; config: ConfigResponse }>;
  };
  adapter: ConfigDomAdapter;
  state: ConfigWorkflowState;
  applyConfig: (config: ConfigResponse) => void;
}

export function createOAuthWorkflow({ api, adapter, applyConfig }: OAuthWorkflowDeps) {
  const loginWithOAuth = (): void => {
    adapter.setCredentialStatus("Redirecting to OAuth login...");
    adapter.document.defaultView?.location.assign("/config/oauth/login");
  };

  const logoutFromOAuth = async (): Promise<void> => {
    adapter.setCredentialStatus("Ending OAuth...");
    try {
      const response = await api.logoutOAuth();
      applyConfig(response.config);
      adapter.setCredentialStatus("OAuth disconnected.", "ok");
    } catch (error) {
      adapter.setCredentialStatus(error instanceof Error ? error.message : "OAuth logout failed.", "error");
    }
  };

  return { loginWithOAuth, logoutFromOAuth };
}
