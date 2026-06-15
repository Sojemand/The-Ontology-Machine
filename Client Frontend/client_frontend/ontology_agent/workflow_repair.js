export const MAX_SQL_REPAIR_ROUNDS = 3;

export function isRepairableSqlBatchFailure(toolCall, result) {
  return toolCall?.function?.name === "sql_batch_execute"
    && result
    && result.ok === false
    && (result.repairable === true || result.error_type === "ontology_write_preflight");
}

export function buildRepairInstruction(result, attempt, { nudge = false } = {}) {
  const preflight = result?.preflight || {};
  const repairSteps = Array.isArray(preflight.repair_steps) ? preflight.repair_steps : [];
  const errors = Array.isArray(preflight.errors) ? preflight.errors : [];
  return [
    `[internal ontology write repair ${attempt}/${MAX_SQL_REPAIR_ROUNDS}]`,
    nudge
      ? "The previous assistant response did not issue a repair tool call after a repairable sql_batch_execute failure."
      : "The previous sql_batch_execute call failed in a repairable way.",
    "Do not answer the user yet and do not ask for permission.",
    "Use sql_query if you need schema, existing IDs, or target rows, then issue a corrected sql_batch_execute call.",
    "Repair the exact relational/schema issues before attempting new content.",
    repairSteps.length ? `Repair steps: ${JSON.stringify(repairSteps)}` : "",
    errors.length ? `Preflight errors: ${JSON.stringify(errors.slice(0, 8))}` : "",
    "Remember: ontology_edges are node-to-node; terms are vocabulary, not edge endpoints. Required JSON columns need explicit '{}' or '[]' when provided."
  ].filter(Boolean).join("\n");
}
