import { mkdirSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

import { defaultKernelCallTool } from "./pipeline-agent-kernel-call-fixtures.js";
import { NON_KERNEL_MCP_TOOLS, PERMANENT_MCP_TOOLS } from "./pipeline-agent-tool-fixtures.js";

export function createPipelineRoot() {
  const root = mkdtempSync(path.join(tmpdir(), "vp-pipeline-agent-"));
  const serverDir = path.join(root, "07 - MCP Server");
  const runtimeDir = path.join(serverDir, "runtime", "python");
  mkdirSync(runtimeDir, { recursive: true });
  writeFileSync(path.join(runtimeDir, "python.exe"), "");
  writeFileSync(
    path.join(serverDir, "module-manifest.json"),
    JSON.stringify({
      module_key: "mcp_server",
      runtime_dir: "runtime/python",
      launcher_module: "mcp_server",
      mcp_transport: { kind: "stdio" }
    })
  );
  return root;
}

export function createFakeClient({
  listTools = async () => [...PERMANENT_MCP_TOOLS, ...NON_KERNEL_MCP_TOOLS],
  callTool = defaultKernelCallTool,
  onClose = () => {}
}) {
  return {
    closed: false,
    async listTools() {
      return await listTools();
    },
    async callTool(name, args) {
      return await callTool(name, args);
    },
    close() {
      this.closed = true;
      onClose();
    }
  };
}
