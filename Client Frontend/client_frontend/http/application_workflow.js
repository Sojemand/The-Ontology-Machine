import { createServer } from "node:http";
import { fileURLToPath } from "node:url";

import { openUrlInBrowser } from "../../runtime/open-browser-when-ready.js";
import { createApiRoutes, persistDisplayMessages, persistOntologyDisplayMessages, persistPipelineDisplayMessages } from "./api_workflow.js";
import { createApplicationContext } from "./application_context.js";
import { createRouteFactory, createRequestHandler, createStaticRoutes, findMatchingRoute } from "./application_routes.js";
import { createConfigRoutes } from "./config_workflow.js";
import { createCredentialRoutes } from "./credentials_workflow.js";
import { removeServerState, writeServerState } from "./server_state.js";

export { findMatchingRoute };

export async function createApplication(options) {
  const context = await createApplicationContext(options);
  const routeFactory = createRouteFactory();
  const server = createServer(
    createRequestHandler({
      context,
      apiRoutes: createApiRoutes(routeFactory),
      configRoutes: [...createConfigRoutes(routeFactory), ...createCredentialRoutes(routeFactory)],
      staticRoutes: createStaticRoutes(routeFactory)
    })
  );
  return {
    server,
    serverStatePath: context.serverStatePath,
    configMode: context.configMode,
    async close() {
      const errors = [];
      try {
        for (const { sessionId } of context.sessionManager.listDisplaySessions()) persistDisplayMessages(context, sessionId);
        for (const { sessionId } of context.ontologySessionManager.listDisplaySessions()) persistOntologyDisplayMessages(context, sessionId);
        for (const { sessionId } of context.pipelineSessionManager.listDisplaySessions()) persistPipelineDisplayMessages(context, sessionId);
      } catch (error) {
        errors.push(error);
      }
      try {
        await closeServer(server);
      } catch (error) {
        if (error?.code !== "ERR_SERVER_NOT_RUNNING") {
          errors.push(error);
        }
      } finally {
        closeApplicationResources(context, errors);
      }
      if (errors.length > 0) {
        throw errors[0];
      }
    },
    getPort() {
      return context.configMode ? 3001 : context.getConfig().port || 3000;
    }
  };
}

async function closeServer(server) {
  if (!server.listening) return;
  await new Promise((resolve, reject) => server.close((error) => (error ? reject(error) : resolve(undefined))));
}

function closeApplicationResources(context, errors) {
  context.sessionManager.clear();
  context.ontologySessionManager.clear();
  context.pipelineSessionManager.clear();
  context.adminSessions.clear();
  for (const resource of [
    context.memoryStore,
    context.chatStore,
    context.ontologyChatStore,
    context.pipelineChatStore,
    context.agent,
    context.ontologyAgent,
    context.pipelineAgent
  ]) {
    try {
      resource.close();
    } catch (error) {
      errors.push(error);
    }
  }
}

export async function startApplication(options) {
  const app = await createApplication(options);
  try {
    await listenOnLoopback(app.server, app.getPort());
    writeServerState(app);
    const baseUrl = `http://127.0.0.1:${app.getPort()}`;
    console.log(options?.configMode ? `Case Worker configuration running at ${baseUrl}/config` : `Case Worker running at ${baseUrl}`);
    return app;
  } catch (error) {
    await app.close().catch(() => {});
    throw error;
  }
}

function listenOnLoopback(server, port) {
  return new Promise((resolve, reject) => {
    const onError = (error) => {
      server.off("listening", onListening);
      reject(error);
    };
    const onListening = () => {
      server.off("error", onError);
      resolve(undefined);
    };
    server.once("error", onError);
    server.once("listening", onListening);
    server.listen(port, "127.0.0.1");
  });
}

export function parseCliArgs(argv = []) {
  const options = {
    browserLogFile: "",
    configMode: false,
    openBrowserUrl: "",
    sessionId: ""
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--config") {
      options.configMode = true;
      continue;
    }
    if (arg === "--open-browser-url" && argv[index + 1]) {
      options.openBrowserUrl = argv[index + 1];
      index += 1;
      continue;
    }
    if (arg === "--browser-log-file" && argv[index + 1]) {
      options.browserLogFile = argv[index + 1];
      index += 1;
      continue;
    }
    if (arg === "--session-id" && argv[index + 1]) {
      options.sessionId = argv[index + 1];
      index += 1;
    }
  }

  return options;
}

async function openBrowserForCli({ openBrowserUrl, browserLogFile, sessionId }, { openBrowser, logError }) {
  if (!openBrowserUrl) return;

  try {
    await openBrowser(openBrowserUrl, { logFile: browserLogFile, sessionId });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    logError(sessionId ? `[${sessionId}] Browser startup failed: ${message}` : `Browser startup failed: ${message}`);
  }
}

export async function runCli(
  argv = process.argv.slice(2),
  {
    logError = console.error,
    openBrowser = openUrlInBrowser,
    processObject = process,
    startApp = startApplication
  } = {}
) {
  const cliOptions = parseCliArgs(argv);
  const app = await startApp({
    rootDir: fileURLToPath(new URL("../../", import.meta.url)),
    configMode: cliOptions.configMode
  });
  const shutdown = async () => {
    try {
      removeServerState(app);
      await app.close();
    } catch {}
  };
  for (const signal of ["SIGINT", "SIGTERM", "SIGHUP"]) {
    processObject.once(signal, () => {
      shutdown().finally(() => {
        if (typeof processObject.exit === "function") {
          processObject.exit(0);
        }
      });
    });
  }
  processObject.once("exit", () => {
    try {
      removeServerState(app);
    } catch {}
  });
  await openBrowserForCli(cliOptions, { openBrowser, logError });
  return app;
}
