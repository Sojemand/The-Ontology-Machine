export function validateRootDir(rootDir) {
  const normalizedRootDir = String(rootDir || "").trim();
  if (!normalizedRootDir) {
    throw new TypeError("rootDir ist erforderlich.");
  }
  return normalizedRootDir;
}

export function isPlainObject(value) {
  return Boolean(value) && Object.prototype.toString.call(value) === "[object Object]";
}
