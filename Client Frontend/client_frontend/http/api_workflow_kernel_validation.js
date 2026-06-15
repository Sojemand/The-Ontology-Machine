const KERNEL_INTERACTIONS_PREFIX = "/api/v2/pipeline-manager/kernel/interactions/";

export function parseKernelInteractionRoute(pathname) {
  if (!pathname.startsWith(KERNEL_INTERACTIONS_PREFIX)) return null;
  const suffix = pathname.slice(KERNEL_INTERACTIONS_PREFIX.length);
  const parts = suffix.split("/").filter(Boolean);
  if (parts.length !== 2) return null;
  const [interactionRequestId, action] = parts;
  if (!interactionRequestId || (action !== "response" && action !== "cancel")) return null;
  return { interactionRequestId, action };
}

export function validateKernelInteractionBody(route, body) {
  const payload = normalizeKernelInteractionPayload(body && typeof body === "object" ? body : {});
  if (payload.schema_version !== "kernel.user_interaction_response.v1") {
    throw new Error("schema_version must be kernel.user_interaction_response.v1.");
  }
  validateKernelInteractionIdentityFields(payload);
  validateKernelInteractionResponseStatus(route, payload);
  return payload;
}

function validateKernelInteractionResponseStatus(route, payload) {
  const responseValueFields = [
    "path_value",
    "text_value",
    "choice_id",
    "selected_database_paths",
    "confirmation_decision",
    "recovery_id",
    "cancellation_reason"
  ].filter((field) => payload[field] !== undefined);
  if (route.action === "response") {
    if (payload.response_status !== "submitted") {
      throw new Error("response route requires response_status submitted.");
    }
    if (responseValueFields.length !== 1) {
      throw new Error("Exactly one response value field must be set.");
    }
  } else if (!["cancelled", "closed", "expired"].includes(String(payload.response_status || ""))) {
    throw new Error("cancel route requires response_status cancelled, closed or expired.");
  }
}

function validateKernelInteractionIdentityFields(payload) {
  if (!payload.target_identity || typeof payload.target_identity !== "object") {
    throw new Error("target_identity must be an object.");
  }
  if (!payload.state_snapshot_identity || typeof payload.state_snapshot_identity !== "object") {
    throw new Error("state_snapshot_identity must be an object.");
  }
  for (const field of ["host_surface_identity", "interaction_response_id", "submitted_at"]) {
    if (typeof payload[field] !== "string" || !payload[field].trim()) {
      throw new Error(`${field} must be a non-empty string.`);
    }
  }
}

function normalizeKernelInteractionPayload(payload) {
  const normalized = { ...payload };
  if (normalized.confirmation_decision === "declined") {
    normalized.confirmation_decision = "rejected";
  }
  return normalized;
}
