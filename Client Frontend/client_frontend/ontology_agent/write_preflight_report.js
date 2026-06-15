export function addError(state, code, statementIndex, tableName, message, repair) {
  state.errors.push({ code, statement_index: statementIndex, table: tableName, message, repair });
}

export function buildReport(errors) {
  const repairSteps = [...new Set(errors.map((error) => error.repair).filter(Boolean))];
  return {
    ok: errors.length === 0,
    repairable: errors.length > 0,
    error_type: errors.length ? "ontology_write_preflight" : null,
    errors,
    repair_steps: repairSteps,
    hint: repairSteps[0] || ""
  };
}

export function defaultRepairForColumn(tableName, columnName) {
  if (columnName === "attributes_json") return "Provide attributes_json='{}' explicitly.";
  if (columnName === "aliases_json") return "Provide aliases_json='[]' explicitly.";
  if (columnName.endsWith("_json")) return `Provide ${tableName}.${columnName} as valid JSON, usually '{}' or '[]'.`;
  if (columnName === "name") return "Provide a non-empty human-readable name.";
  return `Provide a non-empty value for ${tableName}.${columnName}.`;
}
