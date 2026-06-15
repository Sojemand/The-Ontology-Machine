import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";

import { resolveBundledRuntime } from "../runtime_paths.js";

const execFileAsync = promisify(execFile);

function resolveKernelPython(runtimeRoot = "") {
  return resolveBundledRuntime("python", runtimeRoot ? { rootDir: runtimeRoot } : {});
}

export async function runBasicRelationMiningWithKernel({
  pipelineRoot = "",
  dbPath,
  stateRoot = "",
  dryRun = false,
  runtimeRoot = "",
  execFileFn = execFileAsync
}) {
  const resolvedPipelineRoot = String(pipelineRoot || "");
  const kernelRoot = path.join(resolvedPipelineRoot, "08 - Semantic Control Kernel");
  const script = [
    "import json, sys",
    "from semantic_control_kernel.adapters.corpus import CorpusAdapter",
    "from semantic_control_kernel.workflows.ontology import basic_relation_mining",
    "pipeline_root, db_path, state_root, dry_run_text = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]",
    "adapter = CorpusAdapter(state_root=state_root, pipeline_root=pipeline_root)",
    "output, adapter_result, blocker = basic_relation_mining(adapter, target_database_path=db_path, dry_run=(dry_run_text == '1'))",
    "payload = {'status': 'blocked' if blocker else 'ok', 'database_path': db_path, 'dry_run': dry_run_text == '1', 'output': output, 'adapter_result': adapter_result.to_dict() if hasattr(adapter_result, 'to_dict') else adapter_result, 'blocker': blocker.to_dict() if blocker else None}",
    "print(json.dumps(payload, ensure_ascii=True))"
  ].join("; ");
  try {
    const env = {
      ...process.env,
      PYTHONPATH: [kernelRoot, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter)
    };
    const { stdout } = await execFileFn(resolveKernelPython(runtimeRoot), ["-c", script, resolvedPipelineRoot, dbPath, stateRoot, dryRun ? "1" : "0"], {
      cwd: kernelRoot,
      env,
      timeout: 300_000,
      windowsHide: true
    });
    const payload = JSON.parse(stdout.trim());
    if (payload.blocker) {
      return {
        ok: false,
        status: "blocked",
        blocker: payload.blocker,
        dry_run: Boolean(payload.dry_run),
        database_path: payload.database_path
      };
    }
    const output = payload.output || {};
    const status = output.warnings?.length || output.unresolved_documents?.length || output.rejected_groups?.length
      ? "warning"
      : "pass";
    return {
      ok: true,
      status,
      database_path: payload.database_path,
      dry_run: Boolean(payload.dry_run),
      report: output,
      adapter_status: payload.adapter_result?.status || null,
      adapter_call_id: payload.adapter_result?.adapter_call_id || null
    };
  } catch (error) {
    return {
      ok: false,
      status: "error",
      error: error instanceof Error ? error.message : "basic_relation_mining could not be executed.",
      database_path: dbPath,
      dry_run: Boolean(dryRun)
    };
  }
}
