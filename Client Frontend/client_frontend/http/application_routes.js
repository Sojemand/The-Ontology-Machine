import path from "node:path";

import { json, serveFile, text } from "./adapter.js";
import { HttpError, resolveAssetPath } from "./validation.js";

function createExactRoute(name, stage, method, pathname, handle) {
  return { name, stage, method, pathname, matches: (candidatePathname) => candidatePathname === pathname, handle };
}

function createPrefixRoute(name, stage, method, pathname, handle) {
  return { name, stage, method, pathname, matches: (candidatePathname) => candidatePathname.startsWith(pathname), handle };
}

export function createRouteFactory() {
  return { exact: createExactRoute, prefix: createPrefixRoute };
}

export function findMatchingRoute(routes, method, pathname) {
  return routes.find((route) => route.method === method && route.matches(pathname)) || null;
}

async function handleRootRoute({ response, context }) {
  if (context.configMode) {
    response.writeHead(302, { Location: "/config" });
    response.end();
    return;
  }
  await serveFile(response, path.join(context.appDir, "index.html"));
}

async function handleConfigPageRoute({ response, context }) {
  await serveFile(response, path.join(context.appDir, "config.html"));
}

async function handleAssetRoute({ response, url, context }) {
  await serveFile(response, resolveAssetPath(context.appDir, url.pathname));
}

export function createStaticRoutes({ exact, prefix }) {
  return [
    exact("root", "surface", "GET", "/", handleRootRoute),
    exact("config-page", "surface", "GET", "/config", handleConfigPageRoute),
    prefix("asset", "adapter", "GET", "/assets/", handleAssetRoute)
  ];
}

async function dispatchRoutes(routes, request, response, url, context) {
  const route = findMatchingRoute(routes, request.method || "GET", url.pathname);
  if (!route) return null;
  await route.handle({ request, response, url, context });
  return route;
}

function logRouteError(route, error) {
  if (!route || error instanceof HttpError) return;
  console.error(`[http/${route.stage}] ${route.name}`, error);
}

export function createRequestHandler({ context, apiRoutes, configRoutes, staticRoutes }) {
  return async function handleRequest(request, response) {
    let activeRoute = null;
    try {
      const url = new URL(request.url || "/", "http://127.0.0.1");
      activeRoute = await dispatchRoutes(apiRoutes, request, response, url, context);
      if (activeRoute) return;
      activeRoute = await dispatchRoutes(configRoutes, request, response, url, context);
      if (activeRoute) return;
      activeRoute = await dispatchRoutes(staticRoutes, request, response, url, context);
      if (activeRoute) return;
      text(response, 404, "Nicht gefunden.");
    } catch (error) {
      logRouteError(activeRoute, error);
      if (response.headersSent) {
        response.end();
        return;
      }
      json(response, error instanceof HttpError ? error.statusCode : 500, {
        error: error instanceof Error ? error.message : "Internal error."
      });
    }
  };
}
