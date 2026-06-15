import path from "node:path";
import { fileURLToPath } from "node:url";

export { createApplication, createSessionManager, findMatchingRoute, runCli, startApplication } from "./http/surface.js";
import { runCli } from "./http/surface.js";

const isDirectRun = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isDirectRun) {
  runCli().catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
}
