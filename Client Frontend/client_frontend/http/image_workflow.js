import { sendBinary, serveFile, text } from "./adapter.js";
import { parseImageRequest } from "./validation.js";

export const IMAGE_PREFIX = "/api/image/";

export async function handleImageRoute({ response, url, context }) {
  const { docId, page } = parseImageRequest(url.pathname);
  const image = context.agent.resolveImage(docId, page);
  if (!image.available) {
    text(response, 404, "Image not available.");
    return;
  }
  if (image.source === "db" && image.bytes) {
    sendBinary(response, 200, image.bytes, image.contentType);
    return;
  }
  if (image.source === "fs" && image.path) {
    await serveFile(response, image.path);
    return;
  }
  text(response, 404, "Image not available.");
}
