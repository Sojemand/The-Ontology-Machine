import { randomUUID } from "node:crypto";

export function buildCallContext(base = {}) {
  return {
    conversationRef: String(base.conversationRef || ""),
    turnRef: String(base.turnRef || ""),
    clientRequestId: String(base.clientRequestId || randomUUID())
  };
}
