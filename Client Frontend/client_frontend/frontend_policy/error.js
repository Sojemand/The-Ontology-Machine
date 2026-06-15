export class FrontendPolicyValidationError extends Error {
  constructor(message, status = "invalid_policy", policyPath = null) {
    super(message);
    this.name = "FrontendPolicyValidationError";
    this.status = status;
    this.policy_path = policyPath || undefined;
  }
}

export function failFrontendPolicy(path, detail, status = "invalid_policy") {
  throw new FrontendPolicyValidationError(`${path} ${detail}`, status, path);
}
