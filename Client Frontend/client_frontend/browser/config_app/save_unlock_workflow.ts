import type { ConfigResponse } from "../types/index.ts";
import { extractFrontendPolicyError } from "./frontend_policy_field.ts";
import type { ConfigDomAdapter, ConfigFormPayload, StatusMode } from "./types.ts";
import { hasUnlockSecret } from "./validation.ts";
import type { ConfigWorkflowState } from "./workflow_state.ts";

interface SaveUnlockWorkflowDeps {
  api: {
    saveConfig: (payload: ConfigFormPayload) => Promise<{ status: string; config: ConfigResponse }>;
    unlockConfig: (secret: string) => Promise<{ status: string }>;
  };
  adapter: ConfigDomAdapter;
  state: ConfigWorkflowState;
  applyConfig: (config: ConfigResponse) => void;
}

export function createSaveUnlockWorkflow({ api, adapter, state, applyConfig }: SaveUnlockWorkflowDeps) {
  const setSaveStatus = (text: string, mode: StatusMode = "idle") => adapter.setSaveStatus(text, mode);

  const submitSave = async (): Promise<void> => {
    const saveToken = state.nextSaveToken();
    adapter.setSaveButtonDisabled(true);
    setSaveStatus("Saving configuration...");
    try {
      const response = await api.saveConfig(adapter.collectPayload());
      if (!state.isCurrentSaveToken(saveToken)) {
        return;
      }
      applyConfig(response.config);
      adapter.clearSensitiveInputs();
      adapter.setFrontendPolicyStatus("", "idle");
      setSaveStatus("config.json and frontend_policy.json saved.", "ok");
    } catch (error) {
      const frontendPolicyError = extractFrontendPolicyError(error);
      if (!state.isCurrentSaveToken(saveToken)) {
        return;
      }
      if (frontendPolicyError) {
        adapter.setFrontendPolicyStatus(frontendPolicyError.message, "error", frontendPolicyError.policyPath);
      }
      setSaveStatus(error instanceof Error ? error.message : "Save failed.", "error");
    } finally {
      if (state.isCurrentSaveToken(saveToken)) {
        adapter.setSaveButtonDisabled(false);
      }
    }
  };

  const submitUnlock = async (secretOverride?: string): Promise<void> => {
    const secret = String(secretOverride ?? adapter.getUnlockSecret()).trim();
    if (!hasUnlockSecret(secret)) {
      adapter.setUnlockStatus("Please enter the password.", "error");
      return;
    }
    const unlockToken = state.nextUnlockToken();
    adapter.setUnlockButtonDisabled(true);
    try {
      await api.unlockConfig(secret);
      if (!state.isCurrentUnlockToken(unlockToken)) {
        return;
      }
      state.setUnlocked(true);
      adapter.applyLockState(Boolean(state.getCurrentConfig()?.protected && !state.getUnlocked()));
      adapter.clearUnlockSecret();
      adapter.setUnlockStatus("");
    } catch (error) {
      if (!state.isCurrentUnlockToken(unlockToken)) {
        return;
      }
      adapter.setUnlockStatus(error instanceof Error ? error.message : "Unlock failed.", "error");
    } finally {
      if (state.isCurrentUnlockToken(unlockToken)) {
        adapter.setUnlockButtonDisabled(false);
      }
    }
  };

  return { setSaveStatus, submitSave, submitUnlock };
}
