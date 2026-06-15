import { execFile } from "node:child_process";
import { access } from "node:fs/promises";
import path from "node:path";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);
const KERNEL_MODULE_DIRNAME = "08 - Semantic Control Kernel";
const RESET_SCRIPT = `
import json
import sys

from semantic_control_kernel.repository.paths import StatePaths
from semantic_control_kernel.repository.reset import KernelStateResetService
from semantic_control_kernel.repository.run_store import WorkflowRunStore
from semantic_control_kernel.surface.background_continuation import terminate_background_continuations

paths = StatePaths.from_module_root(".")
paths.ensure_layout()
active_workflow_run_ids = [record.workflow_run_id for record in WorkflowRunStore(paths).list_active_runs()]
termination = terminate_background_continuations(paths, workflow_run_ids=active_workflow_run_ids)
manifest = KernelStateResetService(paths).reset_runtime_state(sys.argv[1])
payload = manifest.to_dict()
payload["background_process_termination"] = termination
print(json.dumps(payload, indent=2, sort_keys=True))
`.trim();

async function exists(filePath) {
  try {
    await access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function resolveKernelPython(kernelRoot) {
  for (const candidate of [
    path.join(kernelRoot, "runtime", "python", "python.exe"),
    path.join(kernelRoot, "runtime", "python", "Scripts", "python.exe"),
    path.join(kernelRoot, "runtime", "python", "bin", "python")
  ]) {
    if (await exists(candidate)) return candidate;
  }
  return "";
}

function prependPythonPath(entry, current = "") {
  const values = String(current || "").split(path.delimiter).filter(Boolean);
  return [entry, ...values.filter((value) => path.resolve(value) !== path.resolve(entry))].join(path.delimiter);
}

export async function resetKernelRuntimeState({ pipelineRoot, reason = "client frontend kernel reset" } = {}) {
  const rawRoot = String(pipelineRoot || "").trim();
  if (!rawRoot) throw new Error("Pipeline Root fehlt.");
  const root = path.resolve(rawRoot);
  const kernelRoot = path.join(root, KERNEL_MODULE_DIRNAME);
  if (!(await exists(path.join(kernelRoot, "module-manifest.json")))) {
    throw new Error("Semantic Control Kernel was not found under the Pipeline Root.");
  }
  const pythonExe = await resolveKernelPython(kernelRoot);
  if (!pythonExe) throw new Error("Semantic Control Kernel runtime Python was not found.");
  const { stdout } = await execFileAsync(
    pythonExe,
    ["-c", RESET_SCRIPT, String(reason || "client frontend kernel reset")],
    {
      cwd: kernelRoot,
      env: {
        ...process.env,
        PYTHONIOENCODING: "utf-8",
        PYTHONPATH: prependPythonPath(kernelRoot, process.env.PYTHONPATH)
      },
      maxBuffer: 10 * 1024 * 1024,
      timeout: 60_000,
      windowsHide: true
    }
  );
  return JSON.parse(String(stdout || "{}"));
}
