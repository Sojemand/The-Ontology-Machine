import { execFile as execFileCallback } from "node:child_process";
import { promisify } from "node:util";

const execFile = promisify(execFileCallback);

async function runPowerShell(command, { powershellBin = "powershell.exe" } = {}) {
  const { stdout } = await execFile(powershellBin, ["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command], {
    windowsHide: true,
    maxBuffer: 1024 * 1024
  });
  return String(stdout || "").trim();
}

function endpointPort(endpoint) {
  const match = String(endpoint || "").match(/:(\d+)$/);
  return match ? Number(match[1]) : null;
}

export function parseNetstatPortOwners(output, port) {
  const numericPort = Number(port);
  const pids = new Set();
  for (const line of String(output || "").split(/\r?\n/)) {
    const parts = line.trim().split(/\s+/);
    if (parts.length < 5 || parts[0].toUpperCase() !== "TCP") continue;

    const [, localAddress, foreignAddress, , pidText] = parts;
    if (endpointPort(localAddress) !== numericPort) continue;
    if (endpointPort(foreignAddress) !== 0) continue;

    const pid = Number(pidText);
    if (Number.isInteger(pid) && pid > 0) {
      pids.add(pid);
    }
  }
  return [...pids].map((pid) => ({ pid, processName: null, path: null }));
}

async function queryNetstatPortOwners(port, { netstatBin = "netstat.exe" } = {}) {
  const { stdout } = await execFile(netstatBin, ["-ano", "-p", "tcp"], {
    windowsHide: true,
    maxBuffer: 1024 * 1024
  });
  return parseNetstatPortOwners(stdout, port);
}

export async function queryProcessDetails(pids, { powershellBin = "powershell.exe" } = {}) {
  const uniquePids = [...new Set(pids.map((pid) => Number(pid)).filter((pid) => Number.isInteger(pid) && pid > 0))];
  if (uniquePids.length === 0) return [];

  const pidList = uniquePids.join(",");
  const command = [
    "$ErrorActionPreference = 'Stop'",
    `$items = @(${pidList} | ForEach-Object {`,
    "  $process = Get-Process -Id $_ -ErrorAction SilentlyContinue",
    "  if ($process) {",
    "    [PSCustomObject]@{",
    "      pid = [int]$process.Id",
    "      processName = $process.ProcessName",
    "      path = $process.Path",
    "    }",
    "  } else {",
    "    [PSCustomObject]@{",
    "      pid = [int]$_",
    "      processName = $null",
    "      path = $null",
    "    }",
    "  }",
    "})",
    "ConvertTo-Json -InputObject $items -Compress"
  ].join("\n");

  const output = await runPowerShell(command, { powershellBin });
  if (!output) return [];
  const parsed = JSON.parse(output);
  return Array.isArray(parsed) ? parsed : [parsed];
}

export async function queryListeningPortOwners(port, { powershellBin = "powershell.exe", netstatBin = "netstat.exe" } = {}) {
  const numericPort = Number(port);
  if (!Number.isInteger(numericPort) || numericPort < 1 || numericPort > 65535) {
    throw new Error(`Ungueltiger Port: ${port}`);
  }

  const owners = await queryNetstatPortOwners(numericPort, { netstatBin });
  const details = await queryProcessDetails(
    owners.map((owner) => owner.pid),
    { powershellBin }
  );
  const detailsByPid = new Map(details.map((owner) => [Number(owner.pid), owner]));
  return owners.map((owner) => detailsByPid.get(Number(owner.pid)) || owner);
}

export async function stopProcess(pid, { powershellBin = "powershell.exe" } = {}) {
  const numericPid = Number(pid);
  if (!Number.isInteger(numericPid) || numericPid < 1) {
    throw new Error(`Ungueltige Prozess-ID: ${pid}`);
  }
  await runPowerShell(`Stop-Process -Id ${numericPid} -Force -ErrorAction Stop`, { powershellBin });
}
