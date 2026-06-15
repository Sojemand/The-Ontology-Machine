import path from "node:path";

import { APP_HOME_ENV, APP_NAME, APP_VENDOR } from "./types.js";

export function validateModuleRoot(moduleRoot) {
  const normalized = String(moduleRoot || "").trim();
  if (!normalized) {
    throw new TypeError("moduleRoot is required.");
  }
  return path.resolve(normalized);
}

export function resolveExplicitAppHome(appHome) {
  const normalized = String(appHome || "").trim();
  return normalized ? path.resolve(normalized) : "";
}

export function resolveConfiguredAppHome(appHome, envAppHome, localAppData) {
  const explicitAppHome = resolveExplicitAppHome(appHome);
  if (explicitAppHome) {
    return explicitAppHome;
  }
  const configuredEnvAppHome = resolveExplicitAppHome(envAppHome);
  if (configuredEnvAppHome) {
    return configuredEnvAppHome;
  }
  const normalizedLocalAppData = String(localAppData || "").trim();
  if (!normalizedLocalAppData) {
    throw new Error(
      `${APP_HOME_ENV} is not set and LOCALAPPDATA is empty. The frontend app home could not be resolved.`
    );
  }
  return path.resolve(normalizedLocalAppData, APP_VENDOR, APP_NAME);
}
