import { clipMiddle } from "./context_policy_core.js";

export function compactLargeJson(value, depth = 0) {
  if (typeof value === "string") {
    return value.length > 4_000 ? clipMiddle(value, 3_500) : value;
  }
  if (!value || typeof value !== "object") return value;
  if (Array.isArray(value)) return compactArray(value, depth);
  return compactObject(value, depth);
}

function compactArray(value, depth) {
  const limit = depth > 4 ? 12 : 24;
  const items = value.slice(0, limit).map((item) => compactLargeJson(item, depth + 1));
  if (value.length > limit) items.push({ omitted_items: value.length - limit });
  return items;
}

function compactObject(value, depth) {
  const result = {};
  for (const [key, item] of Object.entries(value)) {
    if (/raw|prompt|stack|traceback|output_text|normalized_json|structured_json|document_payloads/i.test(key)) {
      result[`${key}_summary`] = summarizeValueShape(item);
      continue;
    }
    result[key] = depth > 6 ? summarizeValueShape(item) : compactLargeJson(item, depth + 1);
  }
  return result;
}

function summarizeValueShape(value) {
  if (Array.isArray(value)) return { type: "array", length: value.length };
  if (value && typeof value === "object") {
    const keys = Object.keys(value);
    return { type: "object", key_count: keys.length, keys: keys.slice(0, 24) };
  }
  return { type: typeof value, present: value !== undefined && value !== null };
}
