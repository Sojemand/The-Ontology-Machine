export function writeOperation(sql) {
  if (/^insert\b/i.test(sql) || /^replace\b/i.test(sql)) return /^replace\b/i.test(sql) ? "replace" : "insert";
  if (/^update\b/i.test(sql)) return "update";
  if (/^delete\b/i.test(sql)) return "delete";
  return "";
}

export function parseInsert(sql, params) {
  const match = sql.match(/^(?:insert\s+(?:or\s+\w+\s+)?into|replace\s+into)\s+"?[\w]+"?\s*\(/i);
  if (!match) return null;
  const columnOpen = match[0].lastIndexOf("(");
  const columnClose = findMatchingParen(sql, columnOpen);
  const valuesIndex = sql.search(/\bvalues\b/i);
  if (columnClose < 0 || valuesIndex < 0) return null;
  const valuesOpen = sql.indexOf("(", valuesIndex);
  const valuesClose = findMatchingParen(sql, valuesOpen);
  if (valuesOpen < 0 || valuesClose < 0) return null;
  const columns = splitTopLevelComma(sql.slice(columnOpen + 1, columnClose)).map(cleanIdentifier);
  const valueTokens = splitTopLevelComma(sql.slice(valuesOpen + 1, valuesClose));
  const valuesByColumn = new Map();
  let paramCursor = 0;
  for (let index = 0; index < columns.length; index += 1) {
    const token = String(valueTokens[index] || "").trim();
    const questionCountBefore = valueTokens.slice(0, index).filter((value) => String(value || "").trim() === "?").length;
    if (token === "?") paramCursor = questionCountBefore;
    valuesByColumn.set(columns[index], valueFromToken(token, token === "?" ? params[paramCursor] : undefined));
  }
  return { columns, valueTokens, valuesByColumn };
}

export function parseUpdateColumns(sql) {
  const setMatch = sql.match(/^update\s+"?[\w]+"?\s+set\s+/i);
  if (!setMatch) return [];
  const whereIndex = sql.search(/\bwhere\b/i);
  const setText = sql.slice(setMatch[0].length, whereIndex > -1 ? whereIndex : sql.length);
  return splitTopLevelComma(setText)
    .map((assignment) => cleanIdentifier(String(assignment).split("=")[0] || ""))
    .filter(Boolean);
}

function valueFromToken(token, paramValue) {
  const normalized = String(token || "").trim();
  if (normalized === "?") return { known: true, value: paramValue };
  if (/^null$/i.test(normalized)) return { known: true, value: null };
  if (/^''$/.test(normalized) || /^""$/.test(normalized)) return { known: true, value: "" };
  const quoted = normalized.match(/^'(.*)'$/s) || normalized.match(/^"(.*)"$/s);
  if (quoted) return { known: true, value: quoted[1].replace(/''/g, "'").replace(/""/g, "\"") };
  if (/^-?\d+(?:\.\d+)?$/.test(normalized)) return { known: true, value: Number(normalized) };
  return { known: false, value: normalized };
}

export function stringValue(value) {
  if (!value || !value.known) return "";
  if (value.value === null || value.value === undefined) return "";
  return String(value.value);
}

export function cleanIdentifier(value) {
  return String(value || "").replace(/^"|"$/g, "").trim();
}

export function isBlankValue(value) {
  return value === null || value === undefined || (typeof value === "string" && !value.trim());
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
