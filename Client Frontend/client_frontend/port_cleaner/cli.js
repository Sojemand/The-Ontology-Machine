import { clearStaleServerPort } from "./clear_port.js";
import { queryListeningPortOwners, queryProcessDetails, stopProcess } from "./process_query.js";
import { appendLogLine } from "./state_io.js";
import { resolveBundledRuntime } from "../runtime_paths.js";

export function parseArgs(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (!arg.startsWith("--")) continue;
    const key = arg.slice(2);
    const value = argv[index + 1] && !argv[index + 1].startsWith("--") ? argv[++index] : "true";
    result[key] = value;
  }
  return result;
}

export async function runCli(argv = process.argv.slice(2)) {
  const args = parseArgs(argv);
  const port = Number(args.port);
  const allowedExecutablePath = args["allowed-exe"];
  if (!Number.isInteger(port) || !allowedExecutablePath) {
    throw new Error("Usage: node clear-stale-server-port.js --port <port> --allowed-exe <node.exe> [--server-state-file <file>] [--powershell <powershell.exe>] [--log-file <log>] [--session-id <id>]");
  }
  const powershellBin = String(args.powershell || "").trim() || resolveBundledRuntime("powershell");

  const result = await clearStaleServerPort({
    port,
    allowedExecutablePath,
    serverStateFile: args["server-state-file"] || "",
    logFile: args["log-file"] || "",
    sessionId: args["session-id"] || "",
    queryOwners: (targetPort) => queryListeningPortOwners(targetPort, { powershellBin }),
    queryProcessInfoByPid: async (pid) => {
      const [detail] = await queryProcessDetails([pid], { powershellBin });
      return detail;
    },
    killProcess: (pid) => stopProcess(pid, { powershellBin })
  });
  if (result.killed.length > 0) {
    console.log(`Beendet: ${result.killed.map((owner) => owner.pid).join(", ")}`);
  } else {
    console.log(`Port ${port} ist frei.`);
  }
}

export async function logCliFailure(error, argv = process.argv.slice(2)) {
  const args = parseArgs(argv);
  const message = error instanceof Error ? error.message : String(error);
  await appendLogLine(args["log-file"] || "", `Altprozess-Bereinigung fehlgeschlagen: ${message}`, {
    sessionId: args["session-id"] || ""
  });
  console.error(message);
  process.exitCode = 1;
}
