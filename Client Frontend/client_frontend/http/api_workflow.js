import { createChatRoutes, persistDisplayMessages, persistOntologyDisplayMessages, persistPipelineDisplayMessages } from "./chat_routes.js";
import { handleAdminUpdateKeyRoute } from "./api_workflow_admin.js";
import { handleHealthRouteV2 } from "./api_workflow_health.js";
import {
  handleKernelEventsRoute,
  handleKernelInteractionRoute,
  handleKernelResetRoute,
  handlePipelineRunCancelRoute,
  KERNEL_EVENTS_ROUTE,
  KERNEL_INTERACTIONS_PREFIX,
  KERNEL_RESET_ROUTE
} from "./api_workflow_kernel.js";
import { handleImageRoute, IMAGE_PREFIX } from "./image_workflow.js";

export { persistDisplayMessages, persistOntologyDisplayMessages, persistPipelineDisplayMessages } from "./chat_routes.js";

export function createApiRoutes(routeFactory) {
  const { exact, prefix } = routeFactory;
  return [
    exact("v2-health", "workflow", "GET", "/api/v2/health", handleHealthRouteV2),
    ...createChatRoutes(routeFactory),
    exact("pipeline-kernel-events", "workflow", "GET", KERNEL_EVENTS_ROUTE, handleKernelEventsRoute),
    prefix("pipeline-kernel-interactions", "workflow", "POST", KERNEL_INTERACTIONS_PREFIX, handleKernelInteractionRoute),
    exact("pipeline-run-cancel", "workflow", "POST", "/api/v2/pipeline-manager/run/cancel", handlePipelineRunCancelRoute),
    exact("pipeline-kernel-reset", "workflow", "POST", KERNEL_RESET_ROUTE, handleKernelResetRoute),
    prefix("image", "workflow", "GET", IMAGE_PREFIX, handleImageRoute),
    exact("admin-update-key", "workflow", "POST", "/api/admin/update-key", handleAdminUpdateKeyRoute)
  ];
}
