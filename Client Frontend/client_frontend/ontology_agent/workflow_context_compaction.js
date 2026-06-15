const MAX_TEXT = 700;
const MAX_PREVIEW_ITEMS = 8;

function trimText(value, maxChars = MAX_TEXT) {
  const text = String(value ?? "");
  if (text.length <= maxChars) return text;
  return `${text.slice(0, maxChars)}...[truncated ${text.length - maxChars} chars]`;
}

function safeJsonParse(text) {
  try {
    return JSON.parse(String(text || "{}"));
  } catch {
    return {};
  }
}

function jsonLength(value) {
  try {
    return JSON.stringify(value).length;
  } catch {
    return 0;
  }
}

function compactPreflight(preflight = {}) {
  const errors = Array.isArray(preflight.errors) ? preflight.errors : [];
  const repairSteps = Array.isArray(preflight.repair_steps) ? preflight.repair_steps : [];
  return {
    ok: preflight.ok,
    repairable: preflight.repairable,
    hint: trimText(preflight.hint || ""),
    repair_steps: repairSteps.slice(0, MAX_PREVIEW_ITEMS).map((step) => trimText(step, 300)),
    error_count: errors.length,
    errors: errors.slice(0, MAX_PREVIEW_ITEMS).map((error) => ({
      code: error?.code || "",
      statement_index: error?.statement_index,
      table: error?.table || "",
      message: trimText(error?.message || "", 500),
      repair: trimText(error?.repair || "", 500)
    }))
  };
}

function compactValidation(validation = null) {
  if (!validation || typeof validation !== "object") return null;
  const errors = Array.isArray(validation.errors) ? validation.errors : [];
  const warnings = Array.isArray(validation.warnings) ? validation.warnings : [];
  return {
    status: validation.status,
    error_count: errors.length,
    warning_count: warnings.length,
    errors: errors.slice(0, MAX_PREVIEW_ITEMS).map((error) => trimText(JSON.stringify(error), 700)),
    warnings: warnings.slice(0, MAX_PREVIEW_ITEMS).map((warning) => trimText(JSON.stringify(warning), 500))
  };
}

function compactEmbedding(embedding = null) {
  if (!embedding || typeof embedding !== "object") return null;
  return {
    status: embedding.status,
    reason: trimText(embedding.reason || ""),
    refreshed_count: Array.isArray(embedding.refreshed) ? embedding.refreshed.length : undefined,
    error: trimText(embedding.error || "")
  };
}

function compactSqlBatchArguments(toolCall, result, status) {
  const args = safeJsonParse(toolCall?.function?.arguments);
  const statements = Array.isArray(args.statements) ? args.statements : [];
  return {
    compacted_sql_batch_execute: true,
    status,
    reason: status === "success"
      ? "successful write batch removed from model history; use edit_unit_id/affected rows as the durable receipt"
      : "failed write batch removed from model history; re-query schema/IDs if exact SQL is needed",
    original_argument_chars: String(toolCall?.function?.arguments || "").length,
    ontology_id: trimText(args.ontology_id || result?.ontology_id || "", 220),
    edit_summary: trimText(args.edit_summary || "", 500),
    statement_count: statements.length,
    affected_tables: Array.isArray(result?.affected_tables) ? result.affected_tables : [],
    error_type: result?.error_type || "",
    error: trimText(result?.error || ""),
    repairable: result?.repairable === true,
    validation_status: result?.validation?.status || ""
  };
}

function compactSqlBatchToolCall(toolCall, result, status) {
  return {
    ...toolCall,
    function: {
      ...toolCall.function,
      arguments: JSON.stringify(compactSqlBatchArguments(toolCall, result, status))
    }
  };
}

function compactSuccessfulResult(result) {
  return {
    ok: true,
    compacted_sql_batch_execute: true,
    status: "success",
    original_result_chars: jsonLength(result),
    edit_unit_id: result?.edit_unit_id || "",
    affected_tables: Array.isArray(result?.affected_tables) ? result.affected_tables : [],
    affected_rows: result?.affected_rows || {},
    validation: compactValidation(result?.validation),
    embedding: compactEmbedding(result?.embedding)
  };
}

function compactFailedResult(result) {
  return {
    ok: false,
    compacted_sql_batch_execute: true,
    status: "failed",
    original_result_chars: jsonLength(result),
    error: trimText(result?.error || ""),
    error_type: result?.error_type || "",
    repairable: result?.repairable === true,
    hint: trimText(result?.hint || ""),
    edit_unit_id: result?.edit_unit_id || "",
    affected_tables: Array.isArray(result?.affected_tables) ? result.affected_tables : [],
    affected_rows: result?.affected_rows || {},
    preflight: compactPreflight(result?.preflight || {}),
    validation: compactValidation(result?.validation),
    embedding: compactEmbedding(result?.embedding)
  };
}

export function compactSqlBatchForHistory(toolCall, result) {
  if (toolCall?.function?.name !== "sql_batch_execute") {
    return { toolCall, toolResultContent: JSON.stringify(result) };
  }
  const success = result?.ok === true;
  const status = success ? "success" : "failed";
  const compactedToolCall = compactSqlBatchToolCall(toolCall, result, status);
  const compactedResult = success ? compactSuccessfulResult(result) : compactFailedResult(result);
  return {
    toolCall: compactedToolCall,
    toolResultContent: JSON.stringify(compactedResult)
  };
}
