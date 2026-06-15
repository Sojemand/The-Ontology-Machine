import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";

import {
  discoverMcpServer,
  LocalMcpClient,
  resolveMcpLaunchCommand,
  resolveMcpLaunchEnvironment
} from "../../client_frontend/pipeline_agent/mcp_client.js";
import { probePipelineClient } from "../../client_frontend/pipeline_agent/workflow_boot.js";
import { PERMANENT_AGENT_TOOL_NAMES } from "../../client_frontend/pipeline_agent/kernel_tool_surface.js";

test("discoverMcpServer prefers the manifest Python launcher for stdio MCP", async () => {
  const root = mkdtempSync(path.join(tmpdir(), "vp-mcp-"));
  try {
    const serverDir = path.join(root, "nested", "07 - MCP Server");
    const runtimeDir = path.join(serverDir, "runtime", "python");
    mkdirSync(runtimeDir, { recursive: true });
    writeFileSync(path.join(runtimeDir, "python.exe"), "");
    writeFileSync(path.join(serverDir, "run.bat"), "@echo off\r\n");
    writeFileSync(
      path.join(serverDir, "module-manifest.json"),
      JSON.stringify({
        module_key: "mcp_server",
        runtime_dir: "runtime/python",
        launcher_module: "mcp_server",
        mcp_transport: { kind: "stdio" }
      })
    );

    const discovered = await discoverMcpServer(root);
    const command = resolveMcpLaunchCommand(discovered);

    assert.equal(discovered.root, serverDir);
    assert.equal(discovered.pythonExe, path.join(runtimeDir, "python.exe"));
    assert.equal(discovered.launcherModule, "mcp_server");
    assert.equal(command.mode, "python");
    assert.equal(command.command, path.join(runtimeDir, "python.exe"));
    assert.deepEqual(command.args, ["-m", "mcp_server"]);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("resolveMcpLaunchEnvironment grants Pipeline Manager operator capability by default", () => {
  const env = resolveMcpLaunchEnvironment({ PATH: "fixture" });

  assert.equal(env.VISION_MCP_AGENT_LEVEL, "L2_OPERATOR");
  assert.equal(env.PATH, "fixture");
});

test("resolveMcpLaunchEnvironment adds the MCP server directory to Python imports", () => {
  const env = resolveMcpLaunchEnvironment(
    { PYTHONPATH: path.join("C:", "existing") },
    { pythonPathEntries: [path.join("C:", "Pipeline", "07 - MCP Server")] }
  );

  assert.equal(env.PYTHONPATH.split(path.delimiter)[0], path.join("C:", "Pipeline", "07 - MCP Server"));
  assert.equal(env.PYTHONPATH.split(path.delimiter)[1], path.join("C:", "existing"));
});

test("resolveMcpLaunchEnvironment preserves explicit MCP agent level", () => {
  const env = resolveMcpLaunchEnvironment({ VISION_MCP_AGENT_LEVEL: "L0_READONLY" });

  assert.equal(env.VISION_MCP_AGENT_LEVEL, "L0_READONLY");
});

test("resolveMcpLaunchEnvironment forwards the host bridge token to the MCP process", () => {
  const env = resolveMcpLaunchEnvironment({}, { hostBridgeToken: "host-token" });

  assert.equal(env.VISION_MCP_HOST_BRIDGE_TOKEN, "host-token");
});

test("LocalMcpClient rejects hung requests with a timeout", async () => {
  let writes = 0;
  let kills = 0;
  const client = new LocalMcpClient({ serverDir: "", runBat: "", requestTimeoutMs: 5 });
  client.child = {
    stdin: {
      write() {
        writes += 1;
      }
    },
    kill() {
      kills += 1;
    }
  };

  await assert.rejects(() => client.request("tools/list", {}), /MCP request timed out: tools\/list/);
  assert.equal(writes, 1);
  assert.equal(kills, 1);
  assert.equal(client.pending.size, 0);
});

test("LocalMcpClient accepts discovered MCP descriptors directly", () => {
  const client = new LocalMcpClient({ root: "C:\\Pipeline\\07 - MCP Server", runBat: "run.bat" });

  assert.equal(client.serverDir, "C:\\Pipeline\\07 - MCP Server");
  assert.ok(client.hostBridgeToken);
});

test("probePipelineClient attaches host bridge token only to host-only Kernel calls", async () => {
  const calls = [];
  const candidate = {
    hostBridgeToken: "host-token",
    async listTools() {
      return PERMANENT_AGENT_TOOL_NAMES.map((name) => ({
        name,
        description: name,
        inputSchema: { type: "object", properties: {}, required: [], additionalProperties: false }
      }));
    },
    async callTool(name, args = {}) {
      calls.push({ name, args });
      if (name === "kernel_list_client_frontend_events") return { schema_version: "kernel.client_frontend_event_batch.v1", cursor: "0", events: [] };
      if (name === "kernel_status") return { schema_version: "semantic_control_kernel.mcp_response.v1", status: "ok", tool_name: name };
      throw new Error(`unexpected tool ${name}`);
    }
  };

  const { adapter } = await probePipelineClient(candidate);
  await adapter.callVisibleTool("kernel_status", {});
  await adapter.listKernelEvents("");

  const visibleCall = calls.find((call) => call.name === "kernel_status");
  const hostOnlyCall = calls.find((call) => call.name === "kernel_list_client_frontend_events");
  assert.equal(visibleCall.args.host_bridge_token, undefined);
  assert.equal(hostOnlyCall.args.host_bridge_token, "host-token");
});
