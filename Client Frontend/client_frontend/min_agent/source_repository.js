import { createHash } from "node:crypto";
import path from "node:path";

import { getAvailableColumns, normalizePathForLookup } from "./corpus_tables.js";
import { cleanArtifactFileName, clipText } from "./output_policy.js";
import { listDocumentPromotions, promotionActor, promotionDate, promotionSummary, promotionTitle } from "./promotion_surface.js";
import { extractSourceHintsFromText } from "./source_domain.js";

export function createSourceRepository({ database, imageRepository }) {
  const sourceColumns = getAvailableColumns(database, "documents", ["source_file_path", "source_page", "source_page_count"]);
  const selectColumns = [
    "id",
    "file_name",
    "file_path",
    ...sourceColumns,
    "document_type",
    "content_hash",
    "page_count"
  ];
  const sourceSelect = `SELECT ${selectColumns.join(", ")} FROM documents WHERE id = ?`;
  const hasSourceFilePath = sourceColumns.includes("source_file_path");
  const hasSourcePage = sourceColumns.includes("source_page");
  const pathLookupSql = hasSourceFilePath
    ? `SELECT id FROM documents WHERE lower(file_path) = lower(?) OR lower(source_file_path) = lower(?) ORDER BY ${hasSourcePage ? "COALESCE(source_page, 999999), " : ""}id LIMIT 1`
    : "SELECT id FROM documents WHERE lower(file_path) = lower(?) LIMIT 1";

  function sourceKey(row) {
    const material = String(row?.content_hash || row?.source_file_path || row?.file_path || row?.file_name || row?.id || "").trim();
    if (!material) return "";
    if (row?.content_hash) return `hash:${material.toLowerCase()}`;
    return `source:${createHash("sha256").update(material.toLowerCase()).digest("hex").slice(0, 32)}`;
  }

  function buildSource(docId) {
    const row = database.prepare(sourceSelect).get(docId);
    if (!row) return null;
    const promotions = listDocumentPromotions(database, docId, 40);
    const fileName = cleanArtifactFileName(row.file_name, row);
    const title = promotionTitle(promotions, fileName);
    const initialPage = Math.max(1, Number(row.source_page) || 1);
    const viewer = imageRepository.describeDocument(row);
    return {
      id: row.id,
      source_key: sourceKey(row),
      title,
      type: row.document_type || null,
      date: promotionDate(promotions),
      actor: promotionActor(promotions),
      source_page: row.source_page || null,
      source_page_count: row.source_page_count || null,
      page: initialPage,
      page_count: viewer.pageCount,
      source_refs: [],
      snippet: clipText(promotionSummary(promotions) || title || row.file_name, 300),
      image_url: `/api/image/${encodeURIComponent(row.id)}/${initialPage}`,
      viewer_available: viewer.viewerAvailable,
      file_name: fileName
    };
  }

  function resolveSourceHint(hint) {
    if (!hint?.value) return null;
    if (hint.type === "id") return buildSource(hint.value);
    if (hint.type === "path") {
      const normalizedPath = normalizePathForLookup(hint.value);
      const byPath = hasSourceFilePath
        ? database.prepare(pathLookupSql).get(normalizedPath, normalizedPath)
        : database.prepare(pathLookupSql).get(normalizedPath);
      return byPath ? buildSource(byPath.id) : null;
    }
    if (hint.type !== "file_name") return null;
    const byName = database.prepare("SELECT id FROM documents WHERE lower(file_name) = lower(?) LIMIT 1").get(path.basename(String(hint.value || "").trim()));
    return byName ? buildSource(byName.id) : null;
  }

  function collectSources(hints) {
    const seen = new Set();
    const sources = [];
    for (const hint of hints) {
      const source = resolveSourceHint(hint);
      const key = source?.source_key || source?.id;
      if (source && !seen.has(key)) {
        seen.add(key);
        sources.push(source);
      }
    }
    return sources;
  }

  return {
    buildSource,
    extractSourcesFromWorkbenchOutput(stdout, stderr) {
      return collectSources([...extractSourceHintsFromText(stdout), ...extractSourceHintsFromText(stderr)]);
    },
    extractSourcesFromText(text) {
      return collectSources(extractSourceHintsFromText(text));
    }
  };
}
