import { fileURLToPath } from "node:url";

import { getBundledRuntimeStatus } from "../server/runtime_paths.js";

async function buildNodeProcessStatus() {
  try {
    await import("node:sqlite");
    if (typeof fetch !== "function") {
      throw new Error("global fetch fehlt");
    }
    if (typeof AbortSignal === "undefined" || typeof AbortSignal.timeout !== "function") {
      throw new Error("AbortSignal.timeout fehlt");
    }

    return {
      ok: true,
      path: process.execPath,
      version: process.version
    };
  } catch (error) {
    return {
      ok: false,
      path: process.execPath,
      version: process.version,
      error: error instanceof Error ? error.message : String(error)
    };
  }
}

async function main() {
  const rootDir = fileURLToPath(new URL("../", import.meta.url));
  try {
    const runtimeStatus = getBundledRuntimeStatus(rootDir);
    const nodeProcess = await buildNodeProcessStatus();
    const payload = {
      ...runtimeStatus,
      node_process: nodeProcess,
      ok: runtimeStatus.ok && nodeProcess.ok
    };
    console.log(JSON.stringify(payload, null, 2));
    if (!payload.ok) {
      process.exitCode = 1;
    }
  } catch (error) {
    console.log(
      JSON.stringify(
        {
          ok: false,
          root_dir: rootDir,
          error: error instanceof Error ? error.message : String(error)
        },
        null,
        2
      )
    );
    process.exitCode = 1;
  }
}

await main();
