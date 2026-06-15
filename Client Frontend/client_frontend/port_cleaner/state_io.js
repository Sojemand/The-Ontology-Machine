import { appendFile, readFile, rm } from "node:fs/promises";

function formatLogPrefix(sessionId) {
  return sessionId ? `[${sessionId}] ` : "";
}

export async function appendLogLine(logFile, message, { sessionId = "" } = {}) {
  if (!logFile) return;
  try {
    await appendFile(logFile, `[${new Date().toISOString()}] ${formatLogPrefix(sessionId)}${message}\n`, "utf8");
  } catch {}
}

export async function removeFileIfPresent(filePath) {
  if (!filePath) return;
  try {
    await rm(filePath, { force: true });
  } catch {}
}

export async function readServerStateFile(serverStateFile) {
  if (!serverStateFile) return null;
  try {
    const text = await readFile(serverStateFile, "utf8");
    const parsed = JSON.parse(String(text || "{}"));
    return parsed && typeof parsed === "object" ? parsed : null;
  } catch {
    return null;
  }
}

export function formatOwner(owner) {
  const name = owner.processName ? `${owner.processName}` : "unbekannter Prozess";
  const path = owner.path ? ` (${owner.path})` : "";
  return `PID ${owner.pid} ${name}${path}`;
}

export function isMissingProcessDetail(detail) {
  return !detail || (!detail.processName && !detail.path);
}
