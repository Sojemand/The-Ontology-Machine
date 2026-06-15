import { buildReport } from "./write_preflight_report.js";
import { preflightStatement } from "./write_preflight_statement.js";

export function preflightOntologyWriteBatch({ database, statements = [], ontologyId = "" } = {}) {
  const state = {
    database,
    created: new Map(),
    errors: [],
    ontologyId: String(ontologyId || "")
  };
  const normalizedStatements = Array.isArray(statements) ? statements : [];
  normalizedStatements.forEach((statement, index) => preflightStatement(state, statement, index));
  return buildReport(state.errors);
}
