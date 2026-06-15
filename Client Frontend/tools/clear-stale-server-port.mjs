import { pathToFileURL } from "node:url";

export { clearStaleServerPort } from "../client_frontend/port_cleaner/clear_port.js";
export { isAllowedExecutablePath } from "../client_frontend/port_cleaner/path_policy.js";
export { parseNetstatPortOwners } from "../client_frontend/port_cleaner/process_query.js";

import { logCliFailure, runCli } from "../client_frontend/port_cleaner/cli.js";

const isDirectRun = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (isDirectRun) {
  runCli().catch((error) => logCliFailure(error));
}
