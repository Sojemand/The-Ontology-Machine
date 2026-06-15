import { createChatRepository } from "./repository.js";
import { createChatWorkflow } from "./workflow.js";

/**
 * Public chat-store surface with a stable file path for server/runtime imports.
 * @param {{ rootDir: string, getFrontendPolicy?: () => object | null }} options
 */
export function createChatStore({ rootDir, getFrontendPolicy = null }) {
  const repository = createChatRepository({ rootDir });
  return createChatWorkflow({ repository, getFrontendPolicy });
}
