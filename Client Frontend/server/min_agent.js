import path from "node:path";
import { fileURLToPath } from "node:url";

export {
  assertReadOnlySql,
  assertReadOnlyWorkbench,
  buildSchemaSummary,
  computeHistoryBudget,
  createMinimalAgent,
  estimateMemoryTurns,
  resolveWorkbenchCommandPlans,
  runCli,
  trimHistoryForContext
} from "../client_frontend/min_agent.js";
import { runCli } from "../client_frontend/min_agent.js";

const isDirectRun = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isDirectRun) {
  runCli().catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
}
