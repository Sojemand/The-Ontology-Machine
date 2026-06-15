import { isAllowedExecutablePath } from "./path_policy.js";
import { queryListeningPortOwners, queryProcessDetails, stopProcess } from "./process_query.js";
import { appendLogLine, formatOwner, isMissingProcessDetail, readServerStateFile, removeFileIfPresent } from "./state_io.js";

const DEFAULT_RELEASE_ATTEMPTS = 50;
const DEFAULT_RELEASE_INTERVAL_MS = 100;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function clearStaleServerPort({
  port,
  allowedExecutablePath,
  serverStateFile = "",
  queryOwners = queryListeningPortOwners,
  killProcess = stopProcess,
  queryProcessInfoByPid = async (pid) => {
    const [detail] = await queryProcessDetails([pid]);
    return isMissingProcessDetail(detail) ? null : detail;
  },
  sleepFn = sleep,
  releaseAttempts = DEFAULT_RELEASE_ATTEMPTS,
  releaseIntervalMs = DEFAULT_RELEASE_INTERVAL_MS,
  logFile = "",
  sessionId = ""
}) {
  const recordedServer = await readServerStateFile(serverStateFile);
  if (recordedServer && Number.isInteger(Number(recordedServer.pid)) && Number(recordedServer.pid) > 0) {
    await clearRecordedServerState({
      recordedServer,
      serverStateFile,
      allowedExecutablePath,
      queryProcessInfoByPid,
      killProcess,
      logFile,
      sessionId
    });
  } else if (recordedServer) {
    await removeFileIfPresent(serverStateFile);
  }

  const owners = await queryOwners(port);
  if (owners.length === 0) {
    await appendLogLine(logFile, `Port ${port} ist frei.`, { sessionId });
    return { killed: [] };
  }
  assertOnlyAllowedOwners(port, owners, allowedExecutablePath);
  for (const owner of owners) {
    await appendLogLine(logFile, `Beende alten Sachbearbeiter-Prozess auf Port ${port}: ${formatOwner(owner)}.`, { sessionId });
    await killProcess(owner.pid);
  }
  await waitForReleasedPort(port, queryOwners, sleepFn, releaseAttempts, releaseIntervalMs, logFile, sessionId);
  return { killed: owners };
}

async function clearRecordedServerState(options) {
  const { recordedServer, serverStateFile, allowedExecutablePath, queryProcessInfoByPid, killProcess, logFile, sessionId } = options;
  const recordedPid = Number(recordedServer.pid);
  const detail = await queryProcessInfoByPid(recordedPid);
  if (isMissingProcessDetail(detail)) {
    await appendLogLine(logFile, `Entferne verwaiste Server-State-Datei ohne laufenden Prozess: PID ${recordedPid}.`, { sessionId });
    await removeFileIfPresent(serverStateFile);
    return;
  }
  if (isAllowedExecutablePath(detail.path, allowedExecutablePath) || isAllowedExecutablePath(recordedServer.executablePath, allowedExecutablePath)) {
    await appendLogLine(logFile, `Beende aufgezeichneten alten Sachbearbeiter-Prozess: ${formatOwner(detail)}.`, { sessionId });
    await killProcess(recordedPid);
    await removeFileIfPresent(serverStateFile);
    return;
  }
  throw new Error(`Server-State-Datei verweist auf einen fremden Prozess: ${formatOwner(detail)}.`);
}

function assertOnlyAllowedOwners(port, owners, allowedExecutablePath) {
  const foreignOwners = owners.filter((owner) => !isAllowedExecutablePath(owner.path, allowedExecutablePath));
  if (foreignOwners.length > 0) {
    const details = foreignOwners.map(formatOwner).join("; ");
    throw new Error(`Port ${port} ist durch einen fremden Prozess oder nicht eindeutig zugeordneten Prozess belegt: ${details}.`);
  }
}

async function waitForReleasedPort(port, queryOwners, sleepFn, releaseAttempts, releaseIntervalMs, logFile, sessionId) {
  for (let attempt = 1; attempt <= releaseAttempts; attempt += 1) {
    const remainingOwners = await queryOwners(port);
    if (remainingOwners.length === 0) {
      await appendLogLine(logFile, `Port ${port} ist nach Altprozess-Bereinigung frei.`, { sessionId });
      return;
    }
    if (attempt < releaseAttempts) {
      await sleepFn(releaseIntervalMs);
    }
  }
  throw new Error(`Port ${port} wurde nach dem Beenden alter Prozesse nicht rechtzeitig frei.`);
}
