const ALLOWED_WRITE_TABLES = new Set([
  "ontology_lenses",
  "ontology_runs",
  "ontology_terms",
  "ontology_nodes",
  "ontology_edges",
  "ontology_assertions",
  "ontology_evidence_links",
  "ontology_activation",
  "ontology_embedding_chunks",
  "relations",
  "entity_relations",
  "source_documents",
  "source_document_pages",
  "source_document_classifications"
]);

const BLOCKED_KEYWORDS = /\b(attach|detach|pragma|vacuum|reindex|analyze|drop|alter|create|truncate)\b/i;

const REQUIRED_INSERT_COLUMNS = new Map([
  ["ontology_lenses", ["ontology_id"]],
  ["ontology_runs", ["run_id", "ontology_id"]],
  ["ontology_terms", ["term_id", "ontology_id"]],
  ["ontology_nodes", ["node_id", "ontology_id"]],
  ["ontology_edges", ["edge_id", "ontology_id", "source_node_id", "target_node_id"]],
  ["ontology_assertions", ["assertion_id", "ontology_id"]],
  ["ontology_evidence_links", ["evidence_link_id", "ontology_id", "target_type", "target_id", "evidence_ref_type", "evidence_ref_id"]],
  ["ontology_activation", ["ontology_id"]],
  ["ontology_embedding_chunks", ["chunk_id", "ontology_id", "object_type", "object_id"]],
  ["source_document_classifications", ["source_document_id", "classification_scope", "status"]]
]);

export function affectedTableForWrite(sql) {
  const normalized = normalizeSql(sql);
  let match = normalized.match(/^insert\s+(?:or\s+\w+\s+)?into\s+("?[\w]+"?)/i);
  if (match) return cleanIdentifier(match[1]);
  match = normalized.match(/^replace\s+into\s+("?[\w]+"?)/i);
  if (match) return cleanIdentifier(match[1]);
  match = normalized.match(/^update\s+("?[\w]+"?)/i);
  if (match) return cleanIdentifier(match[1]);
  match = normalized.match(/^delete\s+from\s+("?[\w]+"?)/i);
  if (match) return cleanIdentifier(match[1]);
  throw new Error("sql_batch_execute accepts only INSERT, REPLACE, UPDATE or DELETE statements.");
}

export function assertOntologyWriteSql(sql, params = []) {
  const normalized = normalizeSql(sql);
  if (!normalized) throw new Error("SQL statement is required.");
  if (normalized.includes(";")) throw new Error("Multiple SQL statements are not allowed in one batch item.");
  if (BLOCKED_KEYWORDS.test(normalized)) throw new Error("DDL, PRAGMA and database attachment commands are not allowed.");
  const tableName = affectedTableForWrite(normalized);
  if (!ALLOWED_WRITE_TABLES.has(tableName)) {
    throw new Error(`Ontology Agent cannot write table '${tableName}'. Allowed write layer: ontology/source relation tables only.`);
  }
  assertRequiredInsertColumns(normalized, tableName);
  assertRequiredIdentifierValues(normalized, tableName, params);
  return { sql: normalized, tableName };
}

export function normalizeSql(sql) {
  return String(sql || "").trim().replace(/;+\s*$/, "");
}

function cleanIdentifier(value) {
  return String(value || "").replace(/^"|"$/g, "").trim();
}

function assertRequiredInsertColumns(sql, tableName) {
  const requiredColumns = REQUIRED_INSERT_COLUMNS.get(tableName);
  if (!requiredColumns || !/^(insert|replace)\b/i.test(sql)) return;
  const columns = extractInsertColumns(sql, tableName);
  if (!columns) {
    throw new Error(`Writes to ${tableName} must use an explicit column list including ${requiredColumns.join(", ")}.`);
  }
  if (!extractInsertValues(sql)) {
    throw new Error(`Writes to ${tableName} must use explicit VALUES so required identifiers can be validated.`);
  }
  const present = new Set(columns.map((column) => cleanIdentifier(column).toLowerCase()));
  const missing = requiredColumns.filter((column) => !present.has(column));
  if (missing.length) {
    throw new Error(`Writes to ${tableName} must provide stable non-empty identifiers. Missing required column(s): ${missing.join(", ")}.`);
  }
}

function extractInsertColumns(sql, tableName) {
  const tablePattern = tableName.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = sql.match(new RegExp(`^(?:insert\\s+(?:or\\s+\\w+\\s+)?into|replace\\s+into)\\s+"?${tablePattern}"?\\s*\\(`, "i"));
  if (!match) return null;
  const openIndex = match[0].lastIndexOf("(");
  const closeIndex = findMatchingParen(sql, openIndex);
  if (closeIndex < 0) return null;
  return sql.slice(openIndex + 1, closeIndex).split(",").map((column) => column.trim()).filter(Boolean);
}

function assertRequiredIdentifierValues(sql, tableName, params = []) {
  const requiredColumns = REQUIRED_INSERT_COLUMNS.get(tableName);
  if (!requiredColumns || !/^(insert|replace)\b/i.test(sql)) return;
  const columns = extractInsertColumns(sql, tableName);
  const values = extractInsertValues(sql);
  if (!columns || !values || columns.length !== values.length) return;
  for (const requiredColumn of requiredColumns) {
    const columnIndex = columns.findIndex((column) => cleanIdentifier(column).toLowerCase() === requiredColumn);
    if (columnIndex < 0) continue;
    const valueToken = values[columnIndex].trim();
    if (/^null$/i.test(valueToken) || /^''$/.test(valueToken) || /^""$/.test(valueToken)) {
      throw new Error(`Writes to ${tableName} must provide a non-empty value for ${requiredColumn}.`);
    }
    if (valueToken === "?") {
      const paramIndex = values.slice(0, columnIndex + 1).filter((value) => value.trim() === "?").length - 1;
      if (paramIndex < params.length && isBlankParam(params[paramIndex])) {
        throw new Error(`Writes to ${tableName} must provide a non-empty value for ${requiredColumn}.`);
      }
    }
  }
}

function extractInsertValues(sql) {
  const valuesIndex = sql.search(/\bvalues\b/i);
  if (valuesIndex < 0) return null;
  const openIndex = sql.indexOf("(", valuesIndex);
  if (openIndex < 0) return null;
  const closeIndex = findMatchingParen(sql, openIndex);
  if (closeIndex < 0) return null;
  return splitTopLevelComma(sql.slice(openIndex + 1, closeIndex));
}

function splitTopLevelComma(text) {
  const parts = [];
  let current = "";
  let depth = 0;
  let quote = "";
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    const next = text[index + 1];
    if (quote) {
      current += char;
      if (char === quote && next === quote) {
        current += next;
        index += 1;
      } else if (char === quote) {
        quote = "";
      }
      continue;
    }
    if (char === "'" || char === "\"") {
      quote = char;
      current += char;
      continue;
    }
    if (char === "(") depth += 1;
    if (char === ")") depth -= 1;
    if (char === "," && depth === 0) {
      parts.push(current.trim());
      current = "";
      continue;
    }
    current += char;
  }
  if (current.trim()) parts.push(current.trim());
  return parts;
}

function isBlankParam(value) {
  return value === null || value === undefined || (typeof value === "string" && !value.trim());
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

export { ALLOWED_WRITE_TABLES, REQUIRED_INSERT_COLUMNS };
