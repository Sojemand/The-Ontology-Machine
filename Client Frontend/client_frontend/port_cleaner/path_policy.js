function normalizeExecutablePath(value) {
  return String(value || "")
    .trim()
    .replace(/^"|"$/g, "")
    .replace(/\//g, "\\")
    .replace(/\\+/g, "\\")
    .toLowerCase();
}

export function isAllowedExecutablePath(candidatePath, allowedExecutablePath) {
  return Boolean(candidatePath) && normalizeExecutablePath(candidatePath) === normalizeExecutablePath(allowedExecutablePath);
}
