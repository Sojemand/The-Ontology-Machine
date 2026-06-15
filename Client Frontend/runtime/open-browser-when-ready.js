import { spawn } from "node:child_process";
import { request as httpRequest } from "node:http";
import { request as httpsRequest } from "node:https";
import { appendFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";

const DEFAULT_ATTEMPTS = 120;
const DEFAULT_INTERVAL_MS = 500;
const DEFAULT_TIMEOUT_MS = 1000;

function sleep(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function formatLogPrefix(sessionId) {
  return sessionId ? `[${sessionId}] ` : "";
}

async function appendLogLine(logFile, message, { sessionId = "" } = {}) {
  if (!logFile) {
    return;
  }

  try {
    await appendFile(logFile, `[${new Date().toISOString()}] ${formatLogPrefix(sessionId)}${message}\n`, "utf8");
  } catch {}
}

export async function probeUrl(targetUrl, { timeoutMs = DEFAULT_TIMEOUT_MS } = {}) {
  const url = new URL(targetUrl);
  const requestImpl = url.protocol === "https:" ? httpsRequest : httpRequest;

  return await new Promise((resolve) => {
    const request = requestImpl(
      url,
      {
        method: "GET",
        timeout: timeoutMs
      },
      (response) => {
        response.resume();
        response.on("end", () => {
          const statusCode = Number(response.statusCode || 0);
          resolve({
            ok: statusCode >= 200 && statusCode < 300,
            statusCode
          });
        });
      }
    );

    request.on("timeout", () => {
      request.destroy(new Error("timeout"));
    });

    request.on("error", (error) => {
      resolve({
        ok: false,
        error: error instanceof Error ? error.message : String(error)
      });
    });

    request.end();
  });
}

export async function waitForReady(
  readyUrl,
  {
    attempts = DEFAULT_ATTEMPTS,
    intervalMs = DEFAULT_INTERVAL_MS,
    probe = probeUrl,
    logFile = "",
    sessionId = "",
    sleepFn = sleep
  } = {}
) {
  let lastProbe = null;
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    lastProbe = await probe(readyUrl);
    if (lastProbe.ok) {
      await appendLogLine(logFile, `Readiness probe succeeded for ${readyUrl} with status ${lastProbe.statusCode}.`, {
        sessionId
      });
      return lastProbe;
    }

    if (attempt === 1 || attempt === attempts || attempt % 10 === 0) {
      const detail = lastProbe.error || `status ${lastProbe.statusCode || "unbekannt"}`;
      await appendLogLine(logFile, `Readiness probe ${attempt}/${attempts} pending for ${readyUrl}: ${detail}.`, {
        sessionId
      });
    }

    if (attempt < attempts) {
      await sleepFn(intervalMs);
    }
  }

  const detail = lastProbe?.error || `status ${lastProbe?.statusCode || "unbekannt"}`;
  throw new Error(`Server wurde nicht rechtzeitig bereit: ${detail}`);
}

export async function openUrlInBrowser(
  targetUrl,
  {
    platform = process.platform,
    spawnProcess = spawn,
    logFile = "",
    sessionId = ""
  } = {}
) {
  if (platform !== "win32") {
    throw new Error(`Browser-Autostart wird nur unter Windows unterstuetzt, nicht unter ${platform}.`);
  }

  const launchers = [
    { command: "explorer.exe", args: [targetUrl] },
    { command: "rundll32.exe", args: ["url.dll,FileProtocolHandler", targetUrl] }
  ];

  let lastError = null;
  for (const launcher of launchers) {
    try {
      const child = spawnProcess(launcher.command, launcher.args, {
        detached: true,
        stdio: "ignore",
        windowsHide: true
      });
      if (typeof child?.unref === "function") {
        child.unref();
      }
      await appendLogLine(logFile, `Opened ${targetUrl} via ${launcher.command}.`, { sessionId });
      return launcher;
    } catch (error) {
      lastError = error;
      await appendLogLine(
        logFile,
        `Browser launch via ${launcher.command} failed: ${error instanceof Error ? error.message : String(error)}.`,
        { sessionId }
      );
    }
  }

  throw new Error(
    `Kein Browser-Launcher verfuegbar: ${lastError instanceof Error ? lastError.message : "unbekannter Fehler"}`
  );
}

export async function runCli(argv = process.argv.slice(2)) {
  const [readyUrl, openUrl, logFile = "", sessionId = ""] = argv;
  if (!readyUrl || !openUrl) {
    throw new Error("Usage: node open-browser-when-ready.js <readyUrl> <openUrl> [logFile] [sessionId]");
  }

  await appendLogLine(logFile, `Waiting for ${readyUrl} before opening ${openUrl}.`, { sessionId });
  await waitForReady(readyUrl, { logFile, sessionId });
  await openUrlInBrowser(openUrl, { logFile, sessionId });
}

const isDirectRun = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (process.argv[1] && isDirectRun) {
  runCli().catch(async (error) => {
    const logFile = process.argv[4] || "";
    const sessionId = process.argv[5] || "";
    const message = error instanceof Error ? error.message : String(error);
    await appendLogLine(logFile, `Browser helper failed: ${message}.`, { sessionId });
    console.error(sessionId ? `[${sessionId}] ${message}` : message);
    process.exitCode = 1;
  });
}
