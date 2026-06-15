import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";

import { resolveBundledRuntime } from "../runtime_paths.js";

const execFileAsync = promisify(execFile);

function resolveKernelPython(runtimeRoot = "") {
  return resolveBundledRuntime("python", runtimeRoot ? { rootDir: runtimeRoot } : {});
}

export async function validateOntologyPatchWithKernel({ pipelineRoot = "", dbPath, ontologyId = "", runtimeRoot = "", execFileFn = execFileAsync }) {
  const kernelRoot = path.join(String(pipelineRoot || ""), "08 - Semantic Control Kernel");
  const script = [
    "import json, sys",
    "from semantic_control_kernel.validation.ontology_validation import ontology_patch_validation",
    "ontology_id = sys.argv[2] or None",
    "print(json.dumps(ontology_patch_validation(sys.argv[1], ontology_id=ontology_id), ensure_ascii=True))"
  ].join("; ");
  try {
    const env = {
      ...process.env,
      PYTHONPATH: [kernelRoot, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter)
    };
    const { stdout } = await execFileFn(resolveKernelPython(runtimeRoot), ["-c", script, dbPath, ontologyId], {
      cwd: kernelRoot,
      env,
      timeout: 30_000,
      windowsHide: true
    });
    return JSON.parse(stdout.trim());
  } catch (error) {
    return {
      status: "warning",
      database_path: dbPath,
      ontology_id: ontologyId || null,
      checks: [],
      warnings: [
        {
          code: "kernel_validation_unavailable",
          message: error instanceof Error ? error.message : "Kernel validation could not be executed."
        }
      ],
      errors: []
    };
  }
}
