import { readFile } from "node:fs/promises";
import path from "node:path";

import { HttpError } from "./validation.js";

const MAX_BODY_BYTES = 256 * 1024;

export {
  getAdminTokenFromCookies,
  getExistingUserId,
  getOntologySessionIdFromCookies,
  getPipelineSessionIdFromCookies,
  getSessionIdFromCookies,
  parseCookies,
  resolveUserId,
  setAdminCookie,
  setOntologySessionCookie,
  setPipelineSessionCookie,
  setSessionCookie
} from "./cookies.js";

function getMimeType(filePath) {
  if (filePath.endsWith(".html")) return "text/html; charset=utf-8";
  if (filePath.endsWith(".css")) return "text/css; charset=utf-8";
  if (filePath.endsWith(".js")) return "text/javascript; charset=utf-8";
  if (filePath.endsWith(".ico")) return "image/x-icon";
  if (filePath.endsWith(".png")) return "image/png";
  if (filePath.endsWith(".jpg") || filePath.endsWith(".jpeg")) return "image/jpeg";
  return "application/octet-stream";
}

async function readProjectTextFile(rootDir, relativePaths) {
  for (const relativePath of relativePaths) {
    try {
      return String(await readFile(path.join(rootDir, relativePath), "utf8") || "").trim();
    } catch {}
  }
  return "";
}

export function json(response, statusCode, payload) {
  response.writeHead(statusCode, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store"
  });
  response.end(JSON.stringify(payload));
}

export function text(response, statusCode, payload, contentType = "text/plain; charset=utf-8") {
  response.writeHead(statusCode, { "Content-Type": contentType });
  response.end(payload);
}

export function sendBinary(response, statusCode, payload, contentType = "application/octet-stream") {
  const buffer = Buffer.isBuffer(payload) ? payload : Buffer.from(payload || []);
  response.writeHead(statusCode, {
    "Content-Type": String(contentType || "application/octet-stream"),
    "Content-Length": buffer.byteLength
  });
  response.end(buffer);
}

export async function readJsonBody(request) {
  const chunks = [];
  let totalBytes = 0;
  for await (const chunk of request) {
    totalBytes += chunk.length;
    if (totalBytes > MAX_BODY_BYTES) {
      throw new HttpError(413, "Request body is too large.");
    }
    chunks.push(chunk);
  }
  const raw = Buffer.concat(chunks).toString("utf8");
  if (!raw) {
    return {};
  }
  try {
    return JSON.parse(raw);
  } catch {
    throw new HttpError(400, "Request body is not valid JSON.");
  }
}

export async function serveFile(response, filePath) {
  try {
    const buffer = await readFile(filePath);
    response.writeHead(200, {
      "Content-Type": getMimeType(filePath),
      "Cache-Control": "no-store, max-age=0"
    });
    response.end(buffer);
  } catch {
    text(response, 404, "File not found.");
  }
}

export async function loadSoulProfile(rootDir) {
  const text = await readProjectTextFile(rootDir, ["assistant/soul.txt", "soul.txt"]);
  const nameMatch = text.match(/^Name:\s*(.+)/m);
  return { name: nameMatch ? nameMatch[1].trim() : "Case Worker", text };
}
