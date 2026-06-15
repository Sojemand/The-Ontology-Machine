import { beginOAuthLogin, clearOAuthSession, completeOAuthLogin } from "../credentials.js";
import { providerSettingsForTarget } from "../credentials/policy.js";
import { json } from "./adapter.js";

function callbackUrlFor(request) {
  const host = String(request.headers.host || "127.0.0.1").trim();
  const protocol = host.startsWith("127.0.0.1") || host.startsWith("localhost") ? "http" : "https";
  return `${protocol}://${host}/config/oauth/callback`;
}

function configUrlFor(request) {
  const host = String(request.headers.host || "127.0.0.1").trim();
  const protocol = host.startsWith("127.0.0.1") || host.startsWith("localhost") ? "http" : "https";
  return `${protocol}://${host}/config`;
}

function redirect(response, location) {
  response.writeHead(302, { Location: location });
  response.end();
}

async function handleOAuthLoginRoute({ request, response, context }) {
  if (!providerSettingsForTarget(context.getRuntimeConfig(), "llm_shared").oauth_supported) {
    json(response, 409, { error: "The currently selected LLM provider does not support this OAuth path." });
    return;
  }
  redirect(response, await beginOAuthLogin(context.appPaths.state_dir, configUrlFor(request), context.oauthPendingLogins));
}

async function handleOAuthCallbackRoute({ request, response, url, context }) {
  try {
    await completeOAuthLogin(
      context.appPaths.state_dir,
      callbackUrlFor(request),
      new URLSearchParams(url.searchParams),
      context.oauthPendingLogins
    );
  } catch {}
  redirect(response, "/config");
}

async function handleOAuthLogoutRoute({ response, context }) {
  await clearOAuthSession(context.appPaths.state_dir);
  json(response, 200, { status: "ok", config: await context.getProtectedConfig() });
}

export function createCredentialRoutes({ exact }) {
  return [
    exact("oauth-login", "workflow", "GET", "/config/oauth/login", handleOAuthLoginRoute),
    exact("oauth-callback", "workflow", "GET", "/config/oauth/callback", handleOAuthCallbackRoute),
    exact("oauth-logout", "workflow", "POST", "/config/api/oauth/logout", handleOAuthLogoutRoute)
  ];
}
