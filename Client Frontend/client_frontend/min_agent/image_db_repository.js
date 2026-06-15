import { getAvailableColumns, tableExists } from "./corpus_tables.js";

const IMAGE_TABLE = "document_page_images";
const REQUIRED_COLUMNS = ["document_id", "page", "content_type", "image_blob"];

function hasImageContract(database) {
  if (!tableExists(database, IMAGE_TABLE)) return false;
  return getAvailableColumns(database, IMAGE_TABLE, REQUIRED_COLUMNS).length === REQUIRED_COLUMNS.length;
}

function sniffImageContentType(bytes) {
  if (bytes.length >= 4 && bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4e && bytes[3] === 0x47) {
    return "image/png";
  }
  if (bytes.length >= 3 && bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) {
    return "image/jpeg";
  }
  return "application/octet-stream";
}

function normalizeImageContentType(value, bytes) {
  const contentType = String(value || "").trim().toLowerCase();
  if (contentType === "image/png" || contentType === "image/jpeg") {
    return contentType;
  }
  if (contentType === "image/jpg") {
    return "image/jpeg";
  }
  return sniffImageContentType(bytes);
}

export function createDbImageRepository({ database }) {
  let metadataStatements = null;
  let imageStatement = null;

  function getMetadataStatements() {
    if (metadataStatements) return metadataStatements;
    if (!hasImageContract(database)) return null;
    metadataStatements = {
      meta: database.prepare(`SELECT MAX(page) AS max_page FROM ${IMAGE_TABLE} WHERE document_id = ?`),
      pages: database.prepare(`SELECT page FROM ${IMAGE_TABLE} WHERE document_id = ? ORDER BY page ASC`)
    };
    return metadataStatements;
  }

  function getImageStatement() {
    if (imageStatement) return imageStatement;
    if (!hasImageContract(database)) return null;
    imageStatement = database.prepare(`SELECT content_type, image_blob FROM ${IMAGE_TABLE} WHERE document_id = ? AND page = ? LIMIT 1`);
    return imageStatement;
  }

  return {
    readMeta(docId) {
      const prepared = getMetadataStatements();
      if (!prepared) return { viewerAvailable: false, maxPage: 0 };
      const maxPage = Number(prepared.meta.get(docId)?.max_page) || 0;
      return { viewerAvailable: maxPage > 0, maxPage };
    },
    listAvailablePages(docId) {
      const prepared = getMetadataStatements();
      if (!prepared) return [];
      return prepared.pages
        .all(docId)
        .map((row) => Number(row.page))
        .filter((page) => Number.isSafeInteger(page) && page > 0);
    },
    resolveImage(docId, page) {
      const prepared = getImageStatement();
      if (!prepared) {
        return { available: false, source: "db", contentType: null, bytes: null };
      }
      const row = prepared.get(docId, page);
      if (!row?.image_blob) {
        return { available: false, source: "db", contentType: null, bytes: null };
      }
      const bytes = Buffer.from(row.image_blob);
      return {
        available: true,
        source: "db",
        contentType: normalizeImageContentType(row.content_type, bytes),
        bytes
      };
    }
  };
}
