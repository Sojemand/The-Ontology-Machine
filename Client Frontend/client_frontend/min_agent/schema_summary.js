export function buildSchemaSummary(database) {
  const tableRows = database.prepare("SELECT name, sql FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name").all();
  const tableNames = new Set(tableRows.map(({ name }) => String(name || "")));
  const layerGuide = ["Layer guide:"];
  if (tableNames.has("documents")) layerGuide.push("- documents: primary normalized-first document metadata layer for counts, filtering and grouping");
  if (tableNames.has("document_promotions")) layerGuide.push("- document_promotions: active top-level semantic fact surface; join by document_id and filter is_current = 1 for document titles, identifiers, dates, actors, amounts and custom taxonomy slots");
  if (tableNames.has("extracted_fields")) layerGuide.push("- extracted_fields: primary normalized-first field layer with structured fallback aliases preserved when available");
  if (tableNames.has("extracted_rows")) layerGuide.push("- extracted_rows: primary normalized-first row layer with structured fallback values when available");
  if (tableNames.has("tags") || tableNames.has("people") || tableNames.has("organizations")) layerGuide.push("- tags / people / organizations: primary normalized-first entity layer");
  if (tableNames.has("documents_fts")) layerGuide.push("- documents_fts: wording and recall layer over the active document view; use MATCH only on documents_fts");
  if (tableNames.has("document_payloads")) layerGuide.push("- document_payloads.normalized_json: preferred raw payload layer when present", "- document_payloads.structured_json: structured fallback and audit payload layer");
  if (tableNames.has("vw_document_promotions_current")) layerGuide.push("- vw_document_promotions_current: convenience read view for current document_promotions rows");
  if (tableNames.has("evidence_atoms") || tableNames.has("slot_candidates") || tableNames.has("candidate_evidence")) layerGuide.push("- evidence_atoms / slot_candidates / candidate_evidence: provenance and verification layer, not the default source for direct document facts");
  if (tableNames.has("embeddings") || tableNames.has("embedding_chunks")) layerGuide.push("- embeddings / embedding_chunks: semantic retrieval layer built from normalized document content; if empty, use documents_fts or SQL keyword expansion");
  const tableSummary = tableRows
    .map(({ name, sql }) => {
      const columns = database.prepare(`PRAGMA table_info(${JSON.stringify(name)})`).all().map((column) => column.name).join(", ");
      const checks = extractCheckConstraints(sql);
      return checks.length ? `${name}(${columns}) CHECKS: ${checks.join("; ")}` : `${name}(${columns})`;
    })
    .join("\n");
  if (layerGuide.length > 1 && tableSummary) return `${layerGuide.join("\n")}\n\nTables:\n${tableSummary}`;
  return layerGuide.length > 1 ? layerGuide.join("\n") : tableSummary;
}

export function extractCheckConstraints(createSql) {
  const sql = String(createSql || "");
  const checks = [];
  let searchFrom = 0;
  while (searchFrom < sql.length) {
    const checkIndex = sql.toLowerCase().indexOf("check", searchFrom);
    if (checkIndex < 0) break;
    const openIndex = sql.indexOf("(", checkIndex);
    if (openIndex < 0) break;
    const closeIndex = findMatchingParen(sql, openIndex);
    if (closeIndex < 0) break;
    checks.push(sql.slice(openIndex + 1, closeIndex).replace(/\s+/g, " ").trim());
    searchFrom = closeIndex + 1;
  }
  return checks;
}

function findMatchingParen(text, openIndex) {
  let depth = 0;
  let quote = "";
  for (let index = openIndex; index < text.length; index += 1) {
    const char = text[index];
    const next = text[index + 1];
    if (quote) {
      if (char === quote && next === quote) {
        index += 1;
      } else if (char === quote) {
        quote = "";
      }
      continue;
    }
    if (char === "'" || char === "\"") {
      quote = char;
      continue;
    }
    if (char === "(") depth += 1;
    if (char === ")") {
      depth -= 1;
      if (depth === 0) return index;
    }
  }
  return -1;
}

export function buildSqlErrorResult(error, query, schemaSummary) {
  const message = error instanceof Error ? error.message : "SQL query failed.";
  const hint = /documents_fts_content/i.test(message) || /documents_fts_content/i.test(String(query || ""))
    ? "For full-text search, use MATCH only with documents_fts. documents_fts_content is only the internal FTS backing table."
    : "Check table and column names against the schema summary and correct the query.";
  return { ok: false, error: message, attempted_query: String(query || ""), hint, schema_summary: schemaSummary };
}
