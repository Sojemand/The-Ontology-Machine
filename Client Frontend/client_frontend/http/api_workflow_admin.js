import { updateSecrets } from "../config.js";
import { persistRuntimeApiKeys } from "../credentials.js";
import { json, readJsonBody } from "./adapter.js";

export async function handleAdminUpdateKeyRoute({ request, response, context }) {
  const authHeader = String(request.headers.authorization || "");
  const token = authHeader.startsWith("Bearer ") ? authHeader.slice(7) : "";
  if (!context.getRuntimeConfig().admin_secret || token !== context.getRuntimeConfig().admin_secret) {
    json(response, 403, { error: "Invalid admin token." });
    return;
  }
  const body = await readJsonBody(request);
  await persistRuntimeApiKeys(context.appPaths.state_dir, { ...context.getRuntimeConfig(), ...body });
  context.setConfig(await updateSecrets(context.appPaths.config_dir, { ...context.getConfig(), llm_api_key: "", embedding_api_key: "" }, { ...body, llm_api_key: "", embedding_api_key: "" }));
  json(response, 200, { status: "ok", updated: ["llm_api_key", "embedding_api_key", "admin_secret"].filter((field) => body[field]) });
}
