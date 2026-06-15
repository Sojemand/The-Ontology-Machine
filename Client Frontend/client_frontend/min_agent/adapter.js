import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { resolveBundledRuntime } from "../runtime_paths.js";
import { clipText, clipWorkbenchOutput } from "./output_policy.js";
import { DEFAULT_WORKBENCH_TIMEOUT_MS } from "./types.js";
import { assertReadOnlyWorkbench } from "./workbench_validation.js";

export function resolveWorkbenchCommandPlans(runtime, options = {}) {
  const normalizedRuntime = String(runtime || "").trim().toLowerCase();
  const rootDir = path.resolve(options.rootDir || fileURLToPath(new URL("../../", import.meta.url)));
  if (normalizedRuntime === "python") {
    return [{
      command: resolveBundledRuntime("python", { rootDir }),
      args: ["-I", fileURLToPath(new URL("../../server/workbench_python_runner.py", import.meta.url))]
    }];
  }
  if (normalizedRuntime === "powershell") {
    return [{
      command: resolveBundledRuntime("powershell", { rootDir }),
      args: ["-NoLogo", "-NoProfile", "-NonInteractive", "-Command", "-"]
    }];
  }
  throw new Error("workbench runtime must be python or powershell.");
}

export function buildWorkbenchErrorResult(error, runtime, code) {
  const errorCode = typeof error?.code === "string" ? error.code : null;
  const unavailable = errorCode === "EPERM" || errorCode === "ENOENT";
  const blockedByPolicy = errorCode === "WORKBENCH_POLICY";
  return {
    ok: false,
    available: !unavailable,
    error: error instanceof Error ? error.message : "Workbench failed.",
    error_code: errorCode,
    runtime,
    attempted_code: clipText(code, 2_000),
    hint:
      unavailable
        ? "The bundled Workbench runtime is missing or cannot be started. Use sql_query, get_document, or semantic_search where possible."
        : blockedByPolicy && runtime === "powershell"
          ? "PowerShell is only allowed for read-only corpus inspection inside the active corpus directory and explicitly allowed config/soul files. Use sql_query, get_document, or semantic_search otherwise."
          : runtime === "python"
            ? "Correct the Python code and return compact JSON output. For SQLite, use MIN_AGENT_DB_PATH in read-only mode where possible."
            : "Correct the PowerShell script and avoid write operations. Return compact, readable output."
  };
}

export async function runWorkbench({ runtime, code, timeoutMs, env, rootDir, dataDir, allowedFiles, configDir, runtimePolicy = null }) {
  const normalizedTimeout = Math.min(30_000, Math.max(1_000, Number(timeoutMs) || runtimePolicy?.default_workbench_timeout_ms || DEFAULT_WORKBENCH_TIMEOUT_MS));
  const { runtime: normalizedRuntime, code: normalizedCode, scope } = assertReadOnlyWorkbench(runtime, code, {
    rootDir,
    dataDir,
    configDir,
    allowedFiles
  });
  const commandPlans = resolveWorkbenchCommandPlans(normalizedRuntime, { rootDir });
  async function spawnOnce(command, args) {
    return await new Promise((resolve, reject) => {
      const child = spawn(command, args, {
        windowsHide: true,
        cwd: rootDir || dataDir || process.cwd(),
        env: {
          ...process.env,
          ...env,
          MIN_AGENT_WORKBENCH_ALLOWED_ROOTS: JSON.stringify(scope?.allowedRoots || []),
          MIN_AGENT_WORKBENCH_ALLOWED_FILES: JSON.stringify(scope?.allowedFiles || [])
        }
      });
      let stdout = "";
      let stderr = "";
      let settled = false;
      const timer = setTimeout(() => {
        if (settled) return;
        settled = true;
        child.kill();
        resolve({
          ok: false,
          runtime: normalizedRuntime,
          exit_code: null,
          command,
          stdout: clipWorkbenchOutput(stdout, runtimePolicy),
          stderr: clipWorkbenchOutput(`${stderr}\nTimed out after ${normalizedTimeout}ms.`.trim(), runtimePolicy)
        });
      }, normalizedTimeout);
      child.stdout.on("data", (chunk) => { stdout += String(chunk); });
      child.stderr.on("data", (chunk) => { stderr += String(chunk); });
      child.on("error", (error) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        reject(error);
      });
      child.on("close", (exitCode) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        resolve({
          ok: exitCode === 0,
          runtime: normalizedRuntime,
          exit_code: exitCode,
          command,
          stdout: clipWorkbenchOutput(stdout, runtimePolicy),
          stderr: clipWorkbenchOutput(stderr, runtimePolicy)
        });
      });
      child.stdin.end(normalizedCode);
    });
  }
  let lastError = null;
  for (const plan of commandPlans) {
    try {
      return await spawnOnce(plan.command, plan.args);
    } catch (error) {
      lastError = error;
      if (error?.code !== "ENOENT") throw error;
    }
  }
  throw lastError || new Error("Workbench could not start a runtime process.");
}
