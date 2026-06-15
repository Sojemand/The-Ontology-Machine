import { createMemoryRepository } from "./repository.js";
import { createMemoryWorkflow } from "./workflow.js";

/**
 * Public memory-store surface with a stable file path for server/runtime imports.
 * @param {{ rootDir: string, getFrontendPolicy?: () => object | null }} options
 */
export function createMemoryStore({ rootDir, getFrontendPolicy = null }) {
  const repository = createMemoryRepository({ rootDir });
  return createMemoryWorkflow({ repository, getFrontendPolicy });
}
