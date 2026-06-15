import { access, readdir, readFile, stat } from "node:fs/promises";
import path from "node:path";

const SKIP_DIRS = new Set([".git", ".pytest_cache", "__pycache__", "node_modules"]);
const PIPELINE_MANAGER_AGENT_LEVEL = "L2_OPERATOR";

async function exists(filePath) {
  try {
    await access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function isDirectory(filePath) {
  try {
    return (await stat(filePath)).isDirectory();
  } catch {
    return false;
  }
}

async function readManifest(dir) {
  try {
    return JSON.parse(await readFile(path.join(dir, "module-manifest.json"), "utf8"));
  } catch {
    return null;
  }
}

async function findPythonExecutable(runtimeDir) {
  for (const candidate of [
    path.join(runtimeDir, "python.exe"),
    path.join(runtimeDir, "Scripts", "python.exe"),
    path.join(runtimeDir, "bin", "python")
  ]) {
    if (await exists(candidate)) return candidate;
  }
  return "";
}

export async function discoverMcpServer(pipelineRoot) {
  const rawRoot = String(pipelineRoot || "").trim();
  if (!rawRoot) return null;
  const root = path.resolve(rawRoot);
  if (!(await isDirectory(root))) return null;
  const queue = [root];
  let visited = 0;
  while (queue.length && visited < 5000) {
    const dir = queue.shift();
    visited += 1;
    const manifest = await readManifest(dir);
    if (manifest?.module_key === "mcp_server" && manifest?.mcp_transport?.kind === "stdio") {
      return await buildMcpServerDescriptor(dir, manifest);
    }
    let entries = [];
    try {
      entries = await readdir(dir, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const entry of entries) {
      if (entry.isDirectory() && !SKIP_DIRS.has(entry.name)) queue.push(path.join(dir, entry.name));
    }
  }
  return null;
}

async function buildMcpServerDescriptor(dir, manifest) {
  const runBat = path.join(dir, "run.bat");
  const runtimeDir = path.resolve(dir, String(manifest.runtime_dir || ""));
  const pythonExe = await findPythonExecutable(runtimeDir);
  const launcherModule = String(manifest.launcher_module || "").trim();
  if (pythonExe && launcherModule) return { root: dir, runBat: (await exists(runBat)) ? runBat : "", pythonExe, launcherModule };
  return (await exists(runBat)) ? { root: dir, runBat, pythonExe: "", launcherModule: "" } : null;
}

export function resolveMcpLaunchCommand(server) {
  if (server?.pythonExe && server?.launcherModule) {
    return { command: server.pythonExe, args: ["-m", server.launcherModule], mode: "python" };
  }
  const comspec = process.env.ComSpec || "cmd.exe";
  return { command: comspec, args: ["/d", "/c", "call", server.runBat], mode: "batch" };
}

function prependDelimitedPath(entry, current = "") {
  const normalizedEntry = String(entry || "").trim();
  if (!normalizedEntry) return String(current || "");
  const values = String(current || "").split(path.delimiter).filter(Boolean);
  return [normalizedEntry, ...values.filter((value) => path.resolve(value) !== path.resolve(normalizedEntry))].join(path.delimiter);
}

export function resolveMcpLaunchEnvironment(baseEnv = process.env, { pythonPathEntries = [], hostBridgeToken = "" } = {}) {
  const env = { ...baseEnv };
  const configuredPrimary = String(env.VISION_MCP_AGENT_LEVEL || "").trim();
  const configuredFallback = String(env.MCP_AGENT_LEVEL || "").trim();
  if (!configuredPrimary && !configuredFallback) env.VISION_MCP_AGENT_LEVEL = PIPELINE_MANAGER_AGENT_LEVEL;
  const token = String(hostBridgeToken || "").trim();
  if (token) env.VISION_MCP_HOST_BRIDGE_TOKEN = token;
  for (const entry of pythonPathEntries) {
    env.PYTHONPATH = prependDelimitedPath(entry, env.PYTHONPATH);
  }
  return env;
}
