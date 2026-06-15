import { existsSync, readdirSync } from "node:fs";
import path from "node:path";

import { IMAGE_EXTENSIONS } from "./types.js";

function normalizeRelativeImagePath(relativePath) {
  return String(relativePath || "").trim().replaceAll("\\", "/").replace(/^\.?\//, "");
}

function normalizePageImagesPath(relativePath) {
  const normalized = path.posix.normalize(normalizeRelativeImagePath(relativePath));
  return normalized === "page_images" || normalized.startsWith("page_images/") ? normalized : null;
}

function sanitizeImageFileName(fileName) {
  return path.posix.basename(String(fileName || "").trim()).replace(/[\\/]/g, "_").replaceAll(" ", "_");
}

function resolveImageDirectory(document) {
  const relativePath = normalizePageImagesPath(document.file_path);
  if (relativePath) return /\.(?:jpe?g|png)$/i.test(relativePath) ? path.posix.dirname(relativePath) : relativePath;
  const fileName = sanitizeImageFileName(document.file_name || path.basename(String(document.file_path || "")));
  const hashPrefix = String(document.content_hash || "").trim().replace(/^sha256:/, "");
  return fileName && hashPrefix.length >= 8 ? `page_images/${fileName}.${hashPrefix.slice(0, 8)}` : null;
}

function getImageContentType(filePath) {
  if (filePath.endsWith(".png")) return "image/png";
  if (filePath.endsWith(".jpg") || filePath.endsWith(".jpeg")) return "image/jpeg";
  return "application/octet-stream";
}

export function createFileImageRepository({ dataDir }) {
  function resolveFsDirectory(document) {
    const relativeDir = resolveImageDirectory(document);
    return relativeDir ? path.resolve(dataDir, relativeDir.replace(/\//g, path.sep)) : null;
  }

  function listAvailablePages(document) {
    const imageDir = resolveFsDirectory(document);
    if (!imageDir || !existsSync(imageDir)) return [];
    return readdirSync(imageDir)
      .map((fileName) => fileName.match(/^page_(\d{3})\.(png|jpe?g)$/i))
      .filter(Boolean)
      .map((match) => Number(match[1]))
      .filter((page) => Number.isSafeInteger(page) && page > 0)
      .sort((left, right) => left - right);
  }

  return {
    listAvailablePages,
    resolveImage(document, page = 1) {
      const imageDir = resolveFsDirectory(document);
      if (!imageDir || !existsSync(imageDir)) {
        return { available: false, source: "fs", contentType: null, path: null };
      }
      const prefix = `page_${String(Math.max(1, Number(page) || 1)).padStart(3, "0")}`;
      for (const extension of IMAGE_EXTENSIONS) {
        const candidate = path.join(imageDir, `${prefix}${extension}`);
        if (existsSync(candidate)) {
          return { available: true, source: "fs", contentType: getImageContentType(candidate), path: candidate };
        }
      }
      return { available: false, source: "fs", contentType: null, path: null };
    }
  };
}
