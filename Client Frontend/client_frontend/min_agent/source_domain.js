export function tryParseJsonFragment(text) {
  const raw = String(text || "").trim();
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {}
  for (const [startChar, endChar] of [["{", "}"], ["[", "]"]]) {
    const start = raw.indexOf(startChar);
    const end = raw.lastIndexOf(endChar);
    if (start >= 0 && end > start) {
      try {
        return JSON.parse(raw.slice(start, end + 1));
      } catch {}
    }
  }
  return null;
}

const DIRECT_DOCUMENT_ID_FIELDS = [
  "document_id",
  "doc_id",
  "id",
  "target_document_id",
  "first_document_id",
  "last_document_id",
  "prev_document_id",
  "next_document_id"
];

const DOCUMENT_REF_TYPES = new Set(["document", "documents", "page_document", "page_level_document"]);

function cleanString(value) {
  const text = typeof value === "string" ? value.trim() : "";
  return text || "";
}

function isDocumentRefType(value) {
  return DOCUMENT_REF_TYPES.has(cleanString(value).toLowerCase());
}

function collectTypedDocumentRefs(row, ids) {
  if (!row || typeof row !== "object") return;
  for (const [key, value] of Object.entries(row)) {
    if (key === "ref_type" && isDocumentRefType(value)) {
      const refId = cleanString(row.ref_id);
      if (refId) ids.add(refId);
      continue;
    }
    if (!key.endsWith("_ref_type") || !isDocumentRefType(value)) continue;
    const refId = cleanString(row[`${key.slice(0, -"_ref_type".length)}_ref_id`]);
    if (refId) ids.add(refId);
  }
}

function collectSourceHintsFromValue(value, hints = []) {
  if (Array.isArray(value)) {
    value.forEach((item) => collectSourceHintsFromValue(item, hints));
    return hints;
  }
  if (value && typeof value === "object") {
    for (const field of DIRECT_DOCUMENT_ID_FIELDS) {
      const docId = cleanString(value[field]);
      if (docId) hints.push({ type: "id", value: docId });
    }
    collectTypedDocumentRefs(value, {
      add(docId) {
        hints.push({ type: "id", value: docId });
      }
    });
    for (const [key, nestedValue] of Object.entries(value)) {
      const lowerKey = key.toLowerCase();
      if (typeof nestedValue === "string") {
        if (["id", "doc_id", "document_id"].includes(lowerKey)) hints.push({ type: "id", value: nestedValue.trim() });
        if (["file_path", "path", "pdf_path"].includes(lowerKey)) hints.push({ type: "path", value: nestedValue.trim() });
        if (["file_name", "document_name"].includes(lowerKey)) hints.push({ type: "file_name", value: nestedValue.trim() });
      }
      collectSourceHintsFromValue(nestedValue, hints);
    }
  }
  return hints;
}

export function extractSourceHintsFromText(text) {
  const hints = [];
  const parsed = tryParseJsonFragment(text);
  if (parsed) collectSourceHintsFromValue(parsed, hints);
  for (const value of String(text || "").match(/\bcorpus:\/\/document\/[^\s"',)]+/gi) || []) {
    const rawId = value.replace(/^corpus:\/\/document\//i, "");
    try {
      hints.push({ type: "id", value: decodeURIComponent(rawId) });
    } catch {
      hints.push({ type: "id", value: rawId });
    }
  }
  for (const value of String(text || "").match(/[A-Za-z]:\\[^\r\n"]+?\.pdf/gi) || []) {
    hints.push({ type: "path", value: value.trim() });
  }
  for (const value of String(text || "").match(/\b[\w.-]+\.pdf\b/g) || []) {
    const normalizedValue = value.trim();
    hints.push({ type: "id", value: normalizedValue }, { type: "file_name", value: normalizedValue });
  }
  return hints;
}

function collectDirectDocumentIds(row, ids) {
  for (const field of DIRECT_DOCUMENT_ID_FIELDS) {
    const docId = cleanString(row?.[field]);
    if (docId) ids.add(docId);
  }
}

export function extractDocIdsFromRows(rows) {
  const ids = new Set();
  for (const row of Array.isArray(rows) ? rows : []) {
    collectDirectDocumentIds(row, ids);
    collectTypedDocumentRefs(row, ids);
  }
  return Array.from(ids);
}
