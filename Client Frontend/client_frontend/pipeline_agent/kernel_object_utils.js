export function cleanObject(value) {
  return Object.fromEntries(
    Object.entries(value || {}).filter(([, item]) => item !== "" && item !== undefined && item !== null)
  );
}

export function isEmptyObject(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? Object.keys(value).length === 0 : false;
}
