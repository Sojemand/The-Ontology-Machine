import { resolveChatHistoryPolicy } from "../frontend_policy.js";

export function truncateTitle(text, frontendPolicy = null) {
  const policy = resolveChatHistoryPolicy(frontendPolicy);
  const clean = String(text || "").trim().replace(/[\r\n]+/g, " ");
  if (clean.length <= policy.title_max_length) {
    return clean;
  }
  return clean.slice(0, policy.title_max_length - 3) + "...";
}

export function clampHistoryLimit(limit, frontendPolicy = null) {
  const policy = resolveChatHistoryPolicy(frontendPolicy);
  const normalized = Number(limit);
  if (!Number.isFinite(normalized)) {
    return policy.max_history;
  }
  return Math.min(Math.trunc(normalized), policy.max_history);
}
