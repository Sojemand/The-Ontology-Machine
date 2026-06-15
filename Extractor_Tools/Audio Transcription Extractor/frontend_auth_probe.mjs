import path from "node:path";
import { fileURLToPath } from "node:url";

import { buildAppPaths } from "../../Client Frontend/client_frontend/app_paths/policy.js";
import { loadConfigState, resolveRuntimeConfig } from "../../Client Frontend/client_frontend/config.js";
import { getLlmRuntime, getTargetApiKey } from "../../Client Frontend/client_frontend/credentials.js";
import { loadToken } from "../../Client Frontend/client_frontend/credentials/oauth_token_store.js";

function jsonOut(payload) {
  process.stdout.write(`${JSON.stringify(payload)}\n`);
}

async function main() {
  const redacted = process.argv.includes("--redacted");
  const toolDir = path.dirname(fileURLToPath(import.meta.url));
  const machineRoot = path.resolve(toolDir, "..", "..");
  const frontendRoot = path.join(machineRoot, "Client Frontend");
  const appPaths = buildAppPaths({ moduleRoot: frontendRoot });

  const state = await loadConfigState(appPaths.config_dir);
  const runtimeConfig = {
    ...resolveRuntimeConfig(appPaths.config_dir, state.config),
    state_dir: appPaths.state_dir
  };

  let apiKey = "";
  let apiKeyError = "";
  try {
    apiKey = await getTargetApiKey(appPaths.state_dir, "llm_shared", runtimeConfig);
  } catch (error) {
    apiKeyError = error instanceof Error ? error.message : String(error);
  }

  let runtime = null;
  let runtimeError = "";
  try {
    runtime = await getLlmRuntime(appPaths.state_dir, runtimeConfig);
  } catch (error) {
    runtimeError = error instanceof Error ? error.message : String(error);
  }

  let token = null;
  let tokenError = "";
  try {
    token = await loadToken(appPaths.state_dir);
  } catch (error) {
    tokenError = error instanceof Error ? error.message : String(error);
  }

  if (redacted) {
    jsonOut({
      ok: true,
      has_api_key: Boolean(apiKey || runtime?.api_key || runtime?.fallback_api_key),
      has_oauth_access_token: Boolean(runtime?.access_token || token?.access_token),
      runtime_auth_mode: runtime?.auth_mode || "",
      runtime_ready: Boolean(runtime?.ready),
      oauth_expires_at: runtime?.oauth_session?.expires_at || token?.expires_at || "",
      api_key_error: apiKeyError,
      runtime_error: runtimeError,
      token_error: tokenError
    });
    return;
  }

  jsonOut({
    ok: true,
    api_key: runtime?.api_key || apiKey || runtime?.fallback_api_key || "",
    oauth_access_token: runtime?.access_token || token?.access_token || "",
    oauth_account_id: runtime?.account_id || token?.account_id || "",
    oauth_expires_at: runtime?.oauth_session?.expires_at || token?.expires_at || "",
    runtime_auth_mode: runtime?.auth_mode || "",
    runtime_ready: Boolean(runtime?.ready),
    api_key_error: apiKeyError,
    runtime_error: runtimeError,
    token_error: tokenError
  });
}

main().catch((error) => {
  jsonOut({
    ok: false,
    error: error instanceof Error ? error.message : String(error)
  });
  process.exitCode = 1;
});
