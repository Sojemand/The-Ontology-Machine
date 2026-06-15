import assert from "node:assert/strict";
import test from "node:test";

import { findMatchingRoute } from "../../server/index.js";

function route(method, name, matches) {
  return {
    method,
    name,
    matches
  };
}

test("findMatchingRoute selects the first matching route for a method", () => {
  const routes = [
    route("GET", "exact-chat", (pathname) => pathname === "/api/v2/chat"),
    route("GET", "chat-prefix", (pathname) => pathname.startsWith("/api/chat/"))
  ];

  assert.equal(findMatchingRoute(routes, "GET", "/api/v2/chat")?.name, "exact-chat");
  assert.equal(findMatchingRoute(routes, "GET", "/api/chat/123")?.name, "chat-prefix");
});

test("findMatchingRoute ignores mismatched methods and returns null on miss", () => {
  const routes = [
    route("POST", "chat-post", (pathname) => pathname === "/api/v2/chat")
  ];

  assert.equal(findMatchingRoute(routes, "GET", "/api/v2/chat"), null);
  assert.equal(findMatchingRoute(routes, "POST", "/api/other"), null);
});

