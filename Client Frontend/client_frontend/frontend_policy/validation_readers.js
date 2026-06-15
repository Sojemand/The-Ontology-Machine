import { REGEX_DESCRIPTOR_KEYS, SOURCE_ORDER_VALUES } from "./types.js";
import { failFrontendPolicy } from "./error.js";

export function assertObject(value, path) {
  if (!value || Object.prototype.toString.call(value) !== "[object Object]") {
    failFrontendPolicy(path, "must be a JSON object.");
  }
  return value;
}

export function assertExactKeys(value, keys, path) {
  const object = assertObject(value, path);
  const actualKeys = Object.keys(object).sort();
  const expectedKeys = [...keys].sort();
  if (actualKeys.length !== expectedKeys.length || actualKeys.some((key, index) => key !== expectedKeys[index])) {
    failFrontendPolicy(path, `has invalid or missing keys: [${actualKeys.join(", ")}].`);
  }
  return object;
}

export function readInteger(value, path, min = 1, max = Number.MAX_SAFE_INTEGER) {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < min || parsed > max) {
    failFrontendPolicy(path, `must be an integer between ${min} and ${max}.`);
  }
  return parsed;
}

export function readNumber(value, path, min, max) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed < min || parsed > max) {
    failFrontendPolicy(path, `must be a number between ${min} and ${max}.`);
  }
  return parsed;
}

export function readString(value, path) {
  if (typeof value !== "string") {
    failFrontendPolicy(path, "must be a string.");
  }
  return value;
}

export function readStringArray(value, path) {
  if (!Array.isArray(value)) {
    failFrontendPolicy(path, "must be an array of strings.");
  }
  return value.map((entry, index) => readString(entry, `${path}[${index}]`));
}

function readRegexDescriptor(value, path) {
  const descriptor = assertExactKeys(value, REGEX_DESCRIPTOR_KEYS, path);
  const pattern = readString(descriptor.pattern, `${path}.pattern`);
  const flags = readString(descriptor.flags, `${path}.flags`);
  if (!/^(?:[dgimsuvy]{0,8})$/.test(flags) || new Set(flags).size !== flags.length) {
    failFrontendPolicy(`${path}.flags`, "contains invalid regex flags.");
  }
  try {
    new RegExp(pattern, flags);
  } catch (error) {
    failFrontendPolicy(path, `contains an invalid regex pattern: ${error instanceof Error ? error.message : error}`);
  }
  return { pattern, flags };
}

export function readRegexArray(value, path) {
  if (!Array.isArray(value)) {
    failFrontendPolicy(path, "must be an array of regex descriptors.");
  }
  return value.map((entry, index) => readRegexDescriptor(entry, `${path}[${index}]`));
}

export function readSourceOrder(value, path) {
  const order = readStringArray(value, path);
  if (order.length !== SOURCE_ORDER_VALUES.length || new Set(order).size !== order.length) {
    failFrontendPolicy(path, "must contain each source exactly once.");
  }
  if (order.some((entry) => !SOURCE_ORDER_VALUES.includes(entry))) {
    failFrontendPolicy(path, "contains invalid source values.");
  }
  return order;
}
