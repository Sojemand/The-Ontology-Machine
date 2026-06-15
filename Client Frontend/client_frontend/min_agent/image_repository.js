import { createDbImageRepository } from "./image_db_repository.js";
import { createFileImageRepository } from "./image_file_repository.js";
import { getAvailableColumns, tableExists } from "./corpus_tables.js";

function buildPageCount(document, availablePages = []) {
  const maxAvailablePage = availablePages.length ? availablePages[availablePages.length - 1] : 0;
  return Math.max(1, Number(document?.page_count) || 0, maxAvailablePage);
}

export function createImageRepository({ database, dataDir }) {
  const dbRepository = createDbImageRepository({ database });
  const fileRepository = createFileImageRepository({ dataDir });
  const sourceColumns = getAvailableColumns(database, "documents", ["source_file_path", "source_page", "source_page_count"]);
  const imageColumns = getAvailableColumns(database, "document_page_images", ["document_id", "page"]);
  const documentColumns = ["id", "file_path", "file_name", "content_hash", "page_count", ...sourceColumns];
  const documentStatement = database.prepare(`SELECT ${documentColumns.join(", ")} FROM documents WHERE id = ?`);
  const hasSourcePageGrouping = tableExists(database, "document_page_images")
    && imageColumns.length === 2
    && sourceColumns.includes("source_file_path")
    && sourceColumns.includes("source_page");
  const sourcePageStatement = hasSourcePageGrouping
    ? database.prepare(`
      SELECT DISTINCT i.page
      FROM document_page_images i
      JOIN documents d ON d.id = i.document_id
      WHERE lower(d.source_file_path) = lower(?)
      ORDER BY i.page ASC
    `)
    : null;
  const sourcePageDocumentStatement = hasSourcePageGrouping
    ? database.prepare(`
      SELECT ${documentColumns.map((column) => `d.${column}`).join(", ")}
      FROM documents d
      JOIN document_page_images i ON i.document_id = d.id
      WHERE lower(d.source_file_path) = lower(?) AND i.page = ?
      ORDER BY CASE WHEN COALESCE(d.source_page, 0) = ? THEN 0 ELSE 1 END, d.id
      LIMIT 1
    `)
    : null;

  function sourcePageCount(document) {
    return Math.max(0, Number(document?.source_page_count) || Number(document?.page_count) || 0);
  }

  function sourceFilePath(document) {
    return String(document?.source_file_path || "").trim();
  }

  function listSourcePages(document) {
    const sourceFile = sourceFilePath(document);
    if (!sourcePageStatement || !sourceFile) return [];
    const maxPage = sourcePageCount(document);
    return sourcePageStatement
      .all(sourceFile)
      .map((row) => Number(row.page))
      .filter((page) => Number.isSafeInteger(page) && page > 0 && (!maxPage || page <= maxPage));
  }

  function sourceDocumentForPage(document, page) {
    const sourceFile = sourceFilePath(document);
    const targetPage = Math.max(1, Number(page) || 1);
    return sourcePageDocumentStatement && sourceFile
      ? sourcePageDocumentStatement.get(sourceFile, targetPage, targetPage) || null
      : null;
  }

  function listAvailablePages(document) {
    if (!document?.id) return [];
    const dbPages = dbRepository.listAvailablePages(document.id);
    const sourcePages = listSourcePages(document);
    if (dbPages.length || sourcePages.length) {
      return [...new Set([...dbPages, ...sourcePages])].sort((left, right) => left - right);
    }
    return fileRepository.listAvailablePages(document);
  }

  return {
    describeDocument(document) {
      if (!document?.id) {
        return { viewerAvailable: false, pageCount: 1 };
      }
      const availablePages = listAvailablePages(document);
      if (availablePages.length) {
        return { viewerAvailable: true, pageCount: buildPageCount(document, availablePages) };
      }
      const filePages = fileRepository.listAvailablePages(document);
      return { viewerAvailable: filePages.length > 0, pageCount: buildPageCount(document, filePages) };
    },
    buildPages(document) {
      const availablePages = new Set(listAvailablePages(document));
      return Array.from({ length: buildPageCount(document, [...availablePages].sort((left, right) => left - right)) }, (_value, index) => ({
        page: index + 1,
        image_url: `/api/image/${encodeURIComponent(document.id)}/${index + 1}`,
        available: availablePages.has(index + 1)
      }));
    },
    resolveImage(docId, page = 1) {
      const dbImage = dbRepository.resolveImage(docId, page);
      if (dbImage.available) return dbImage;
      const document = documentStatement.get(docId);
      if (!document) {
        return { available: false, source: null, contentType: null, bytes: null, path: null };
      }
      const sourceDocument = sourceDocumentForPage(document, page);
      if (sourceDocument && sourceDocument.id !== document.id) {
        const sourceDbImage = dbRepository.resolveImage(sourceDocument.id, page);
        if (sourceDbImage.available) return sourceDbImage;
        const sourceFileImage = fileRepository.resolveImage(sourceDocument, page);
        if (sourceFileImage.available) return sourceFileImage;
      }
      return fileRepository.resolveImage(document, page);
    }
  };
}
