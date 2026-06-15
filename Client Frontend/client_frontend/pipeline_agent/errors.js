const POLICY_CATALOG_DRIFT_PATTERN = /(?:enthaelt|enth.lt) unbekannte Tools|Agent-Policy .*unbekannte Tools|klassifiziert nicht alle MCP-Tools/i;

export function unavailableError(message) {
  const error = new Error(message);
  error.code = "pipeline_manager_unavailable";
  return error;
}

export function errorMessage(error) {
  return error instanceof Error ? error.message : String(error);
}

export function isPolicyCatalogDrift(error) {
  return POLICY_CATALOG_DRIFT_PATTERN.test(errorMessage(error));
}

export function policyCatalogDriftError(error) {
  return unavailableError(
    [
      "MCP agent policy and MCP tool catalog do not match.",
      errorMessage(error),
      "Please restart the client; if the error remains, the Pipeline Root is running an outdated MCP server version."
    ].join(" ")
  );
}
