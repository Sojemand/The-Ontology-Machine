import { createServer } from "node:http";

const CALLBACK_PATH = "/auth/callback";

function writeText(response, statusCode, body) {
  const text = String(body || "");
  response.writeHead(statusCode, {
    "Content-Type": "text/plain; charset=utf-8",
    "Content-Length": Buffer.byteLength(text, "utf8")
  });
  response.end(text);
}

export function createLoopbackCallbackServer({ port, returnUrl, onCallback }) {
  let server = null;
  let callbackUrl = `http://localhost:${port}${CALLBACK_PATH}`;
  return {
    get callback_url() {
      return callbackUrl;
    },
    async start() {
      if (server) {
        return;
      }
      server = createServer(async (request, response) => {
        let shouldClose = false;
        try {
          if ((request.method || "GET") !== "GET") {
            writeText(response, 405, "Method not allowed.");
            return;
          }
          const url = new URL(request.url || "/", callbackUrl);
          if (url.pathname !== CALLBACK_PATH) {
            writeText(response, 404, "Not found.");
            return;
          }
          shouldClose = true;
          await onCallback(url.searchParams);
          response.writeHead(302, { Location: returnUrl });
          response.end();
        } catch (error) {
          shouldClose = true;
          writeText(response, 400, `OAuth callback failed: ${error instanceof Error ? error.message : error}`);
        } finally {
          if (shouldClose) {
            setTimeout(() => void server?.close(), 0);
          }
        }
      });
      await new Promise((resolve, reject) => {
        server.listen(port, "127.0.0.1", (error) => (error ? reject(error) : resolve(undefined)));
      });
      const address = server.address();
      if (address && typeof address === "object") {
        callbackUrl = `http://localhost:${address.port}${CALLBACK_PATH}`;
      }
      server.unref();
    },
    async close() {
      if (!server) {
        return;
      }
      const current = server;
      server = null;
      await new Promise((resolve) => current.close(() => resolve(undefined)));
    }
  };
}
