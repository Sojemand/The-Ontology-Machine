import { spawn } from "node:child_process";
import { randomBytes } from "node:crypto";

export { discoverMcpServer, resolveMcpLaunchCommand, resolveMcpLaunchEnvironment } from "./mcp_discovery.js";
import { resolveMcpLaunchCommand, resolveMcpLaunchEnvironment } from "./mcp_discovery.js";

const DEFAULT_REQUEST_TIMEOUT_MS = 60_000;

export class LocalMcpClient {
  constructor({ serverDir = "", root = "", runBat, pythonExe = "", launcherModule = "", requestTimeoutMs = DEFAULT_REQUEST_TIMEOUT_MS, hostBridgeToken = "" }) {
    this.serverDir = serverDir || root;
    this.runBat = runBat;
    this.pythonExe = pythonExe;
    this.launcherModule = launcherModule;
    this.hostBridgeToken = String(hostBridgeToken || randomBytes(32).toString("hex"));
    this.child = null;
    this.buffer = Buffer.alloc(0);
    this.nextId = 1;
    this.pending = new Map();
    this.stderrTail = "";
    this.requestTimeoutMs = requestTimeoutMs;
  }

  async start() {
    if (this.child) return;
    const cmd = resolveMcpLaunchCommand(this);
    this.child = spawn(cmd.command, cmd.args, {
      cwd: this.serverDir,
      env: resolveMcpLaunchEnvironment(process.env, {
        pythonPathEntries: cmd.mode === "python" ? [this.serverDir] : [],
        hostBridgeToken: this.hostBridgeToken
      }),
      stdio: ["pipe", "pipe", "pipe"],
      windowsHide: true
    });
    this.child.stdout.on("data", (chunk) => this.receive(chunk));
    this.child.stderr.on("data", (chunk) => {
      this.stderrTail = `${this.stderrTail}${chunk.toString("utf8")}`.slice(-4000);
    });
    this.child.on("exit", (code, signal) => {
      const detail = this.stderrTail.trim();
      const suffix = detail ? ` ${detail}` : code != null ? ` Exit-Code ${code}.` : signal ? ` Signal ${signal}.` : "";
      this.rejectAll(new Error(`MCP Server wurde beendet.${suffix}`.trim()));
    });
    await this.request("initialize", {
      protocolVersion: "2024-11-05",
      capabilities: {},
      clientInfo: { name: "vision-pipeline-client-frontend", version: "1" }
    });
    this.notify("notifications/initialized", {});
  }

  async listTools() {
    await this.start();
    const result = await this.request("tools/list", {});
    return Array.isArray(result?.tools) ? result.tools : [];
  }

  async callTool(name, argumentsPayload = {}) {
    await this.start();
    const result = await this.request("tools/call", { name, arguments: argumentsPayload });
    if (result?.isError) {
      const message = result.content?.map((item) => item?.text).filter(Boolean).join("\n") || "MCP tool call failed.";
      throw new Error(message);
    }
    return result?.structuredContent ?? result;
  }

  request(method, params) {
    const id = this.nextId++;
    this.write({ jsonrpc: "2.0", id, method, params });
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        this.child?.kill();
        this.child = null;
        reject(new Error(`MCP request timed out: ${method}`));
      }, this.requestTimeoutMs);
      this.pending.set(id, { resolve, reject, timer });
    });
  }

  notify(method, params) {
    this.write({ jsonrpc: "2.0", method, params });
  }

  write(message) {
    const body = Buffer.from(JSON.stringify(message), "utf8");
    this.child.stdin.write(Buffer.concat([Buffer.from(`Content-Length: ${body.length}\r\n\r\n`, "ascii"), body]));
  }

  receive(chunk) {
    this.buffer = Buffer.concat([this.buffer, chunk]);
    while (true) {
      const headerEnd = this.buffer.indexOf("\r\n\r\n");
      if (headerEnd < 0) return;
      const header = this.buffer.slice(0, headerEnd).toString("ascii");
      const match = header.match(/content-length:\s*(\d+)/i);
      if (!match) throw new Error("MCP response without Content-Length.");
      const length = Number(match[1]);
      const messageEnd = headerEnd + 4 + length;
      if (this.buffer.length < messageEnd) return;
      const payload = JSON.parse(this.buffer.slice(headerEnd + 4, messageEnd).toString("utf8"));
      this.buffer = this.buffer.slice(messageEnd);
      this.resolve(payload);
    }
  }

  resolve(payload) {
    const pending = this.pending.get(payload.id);
    if (!pending) return;
    this.pending.delete(payload.id);
    clearTimeout(pending.timer);
    if (payload.error) pending.reject(new Error(payload.error.message || "MCP error."));
    else pending.resolve(payload.result);
  }

  rejectAll(error) {
    for (const pending of this.pending.values()) {
      clearTimeout(pending.timer);
      pending.reject(error);
    }
    this.pending.clear();
    this.child = null;
  }

  close() {
    if (this.child) this.child.kill();
    this.rejectAll(new Error("MCP Client geschlossen."));
  }
}
