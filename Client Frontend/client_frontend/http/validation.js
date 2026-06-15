import path from "node:path";

export class HttpError extends Error {
  constructor(statusCode, message) {
    super(message);
    this.name = "HttpError";
    this.statusCode = statusCode;
  }
}

function safeDecodeURIComponent(value) {
  try {
    return decodeURIComponent(value);
  } catch {
    return null;
  }
}

function parsePositiveInteger(value) {
  const normalized = String(value || "").trim();
  if (!normalized || !/^[1-9]\d*$/.test(normalized)) {
    return null;
  }
  const parsed = Number(normalized);
  return Number.isSafeInteger(parsed) ? parsed : null;
}

export function requireChatMessage(body) {
  const message = String(body?.message || "").trim();
  if (!message) {
    throw new HttpError(400, "message is missing.");
  }
  return message;
}

export function requireDecodedPathSuffix(pathname, prefix, label) {
  const decoded = safeDecodeURIComponent(pathname.slice(prefix.length));
  if (!decoded) {
    throw new HttpError(400, `${label} is encoded incorrectly.`);
  }
  return decoded;
}

export function parseImageRequest(pathname) {
  const parts = pathname.split("/");
  if (parts.length !== 5) {
    throw new HttpError(400, "Image route expects exactly document ID and page.");
  }
  const [, , , encodedDocId, pageText] = parts;
  if (!encodedDocId) {
    throw new HttpError(400, "Document ID is missing.");
  }
  const docId = safeDecodeURIComponent(encodedDocId);
  if (!docId) {
    throw new HttpError(400, "Document ID is encoded incorrectly.");
  }
  const page = parsePositiveInteger(pageText);
  if (!page) {
    throw new HttpError(400, "Page must be a positive integer.");
  }
  return { docId, page };
}

export function resolveAssetPath(appDir, pathname) {
  const resolved = path.resolve(appDir, pathname.slice(1));
  if (!resolved.startsWith(appDir + path.sep) && resolved !== appDir) {
    throw new HttpError(403, "Access denied.");
  }
  return resolved;
}
