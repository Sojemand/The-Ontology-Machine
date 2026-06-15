import { MAX_TEXT_LENGTH, MAX_WORKBENCH_OUTPUT } from "./types.js";

export function clipText(value, maxLength = MAX_TEXT_LENGTH) {
  const text = String(value || "");
  return text.length > maxLength ? `${text.slice(0, maxLength)}\n...[truncated]` : text;
}

export function clipValue(value, maxLength = 500) {
  if (value == null || typeof value !== "string") {
    return value;
  }
  return clipText(value, maxLength);
}

export function corpusRef(row) {
  const id = String(row?.document_id || row?.id || "").trim();
  return id ? `corpus://document/${encodeURIComponent(id)}` : "corpus://document";
}

function isLocalPathKey(key) {
  return ["file_path", "source_file_path", "pdf_path", "absolute_path"].includes(String(key || "").toLowerCase());
}

export function cleanArtifactFileName(value, row = {}) {
  const text = String(value || "");
  const title = String(row?.title || "").trim();
  if (/\.structured\.normalized\.json$/i.test(text)) {
    return title || text.replace(/\.structured\.normalized\.json$/i, "");
  }
  if (/\.structured\.json$/i.test(text)) {
    return title || text.replace(/\.structured\.json$/i, "");
  }
  return clipValue(text);
}

export function sanitizeRow(row) {
  return Object.fromEntries(
    Object.entries(row).map(([key, value]) => {
      if (isLocalPathKey(key)) {
        return [key, corpusRef(row)];
      }
      if (String(key || "").toLowerCase() === "file_name" && typeof value === "string") {
        return [key, cleanArtifactFileName(value, row)];
      }
      return [key, clipValue(value)];
    })
  );
}

export function clipWorkbenchOutput(value, runtimePolicy = null) {
  return clipText(value, runtimePolicy?.max_workbench_output || MAX_WORKBENCH_OUTPUT);
}
