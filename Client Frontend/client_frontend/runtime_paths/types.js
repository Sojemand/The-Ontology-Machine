/**
 * @typedef {"node" | "python" | "powershell"} SupportedRuntime
 * @typedef {{ node: string[], python: string[], powershell: string[] }} RuntimeManifest
 * @typedef {{ ok: boolean, path: string, expected: string[] }} RuntimeStatusEntry
 * @typedef {{ ok: boolean, root_dir: string, manifest_path: string, runtimes: Record<SupportedRuntime, RuntimeStatusEntry> }} RuntimeStatusPayload
 */

export const SUPPORTED_RUNTIMES = Object.freeze(["node", "python", "powershell"]);

export const RUNTIME_LABELS = Object.freeze({
  node: "Node",
  python: "Python",
  powershell: "PowerShell"
});
