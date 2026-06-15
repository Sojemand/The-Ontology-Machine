import { createLoopbackCallbackServer } from "./oauth_callback.js";
import { beginOAuthLogin, completeOAuthLogin } from "./oauth_flow.js";
import { utcNowIso, writeOAuthReport } from "./oauth_report.js";
import { deleteToken, saveToken } from "./oauth_token_store.js";
import { buildConnectedSession, buildErrorSession, buildLoggedOutSession, OAUTH_CALLBACK_PORT } from "./policy.js";
import { loadCredentialsState, saveCredentialsState } from "./repository.js";

let activeLoginCapture = null;

export async function startOAuthLogin(stateDir, returnUrl, pendingLogins) {
  await activeLoginCapture?.close().catch(() => {});
  const callbackServer = createLoopbackCallbackServer({
    port: OAUTH_CALLBACK_PORT,
    returnUrl,
    onCallback: async (params) => {
      try {
        await finishOAuthLogin(stateDir, callbackServer.callback_url, params, pendingLogins);
      } finally {
        if (activeLoginCapture === callbackServer) {
          activeLoginCapture = null;
        }
      }
    }
  });
  activeLoginCapture = callbackServer;
  try {
    await callbackServer.start();
    return beginOAuthLogin({ callbackUrl: callbackServer.callback_url, pendingLogins });
  } catch (error) {
    if (activeLoginCapture === callbackServer) {
      activeLoginCapture = null;
    }
    await callbackServer.close().catch(() => {});
    throw error;
  }
}

export async function finishOAuthLogin(stateDir, callbackUrl, params, pendingLogins) {
  const state = await loadCredentialsState(stateDir);
  try {
    const token = await completeOAuthLogin({ callbackUrl, params, pendingLogins });
    await saveToken(stateDir, token);
    state.oauth_session = buildConnectedSession(token);
    await saveCredentialsState(stateDir, state);
    await writeOAuthReport(stateDir, { event: "login", written_at: utcNowIso(), oauth: { status: state.oauth_session } });
    return state.oauth_session;
  } catch (error) {
    state.oauth_session = buildErrorSession(error instanceof Error ? error.message : String(error), state.oauth_session);
    await saveCredentialsState(stateDir, state);
    await writeOAuthReport(stateDir, { event: "login_error", written_at: utcNowIso(), oauth: { status: state.oauth_session } });
    throw error;
  }
}

export async function logoutFromOAuth(stateDir) {
  const state = await loadCredentialsState(stateDir);
  await deleteToken(stateDir);
  state.oauth_session = buildLoggedOutSession();
  await saveCredentialsState(stateDir, state);
  await writeOAuthReport(stateDir, { event: "logout", written_at: utcNowIso(), oauth: { status: state.oauth_session } });
  return state.oauth_session;
}
