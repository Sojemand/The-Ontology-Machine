import { json } from "./adapter.js";
import { buildHealthPayload } from "./policy.js";

const PIPELINE_HEALTH_STATUS_TIMEOUT_MS = 50;

function delay(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

async function pipelineManagerHealthStatus(pipelineAgent) {
  if (!pipelineAgent) return null;
  const timeoutStatus = {
    available: false,
    reason: "Taxonomy Agent status is still loading.",
    permission_status: null,
    permission_warning: "",
    startup_pending: true
  };
  const statusPromise = typeof pipelineAgent.healthStatus === "function"
    ? pipelineAgent.healthStatus()
    : pipelineAgent.status({ fast: true });
  return await Promise.race([
    statusPromise,
    delay(PIPELINE_HEALTH_STATUS_TIMEOUT_MS).then(() => timeoutStatus)
  ]);
}

export async function handleHealthRouteV2({ response, context }) {
  const credentialState = await context.getCredentialState();
  json(
    response,
    200,
    {
      ...buildHealthPayload(context),
      llm_ready: credentialState.targets.llm_shared.ready,
      embedding_ready: credentialState.targets.embeddings.ready,
      llm_auth_mode: credentialState.auth_mode,
      oauth_session: credentialState.oauth_session,
      pipeline_manager: await pipelineManagerHealthStatus(context.pipelineAgent),
      api_version: "v2"
    }
  );
}
