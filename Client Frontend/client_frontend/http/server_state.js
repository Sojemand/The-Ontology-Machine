import { mkdirSync, rmSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { writeTextAtomicallySync } from "../atomic_file.js";

export function writeServerState(app) {
  const serverStatePath = app.serverStatePath;
  if (!serverStatePath) return;
  mkdirSync(path.dirname(serverStatePath), { recursive: true });
  writeTextAtomicallySync(
    serverStatePath,
    JSON.stringify(
      {
        pid: process.pid,
        port: app.getPort(),
        configMode: Boolean(app.configMode),
        executablePath: process.execPath,
        serverEntry: fileURLToPath(new URL("../../server/index.js", import.meta.url)),
        writtenAt: new Date().toISOString()
      },
      null,
      2
    ) + "\n"
  );
}

export function removeServerState(app) {
  const serverStatePath = app.serverStatePath;
  if (!serverStatePath) return;
  rmSync(serverStatePath, { force: true });
}
