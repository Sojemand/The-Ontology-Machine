import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";

import { setOntologySessionCookie, setPipelineSessionCookie, setSessionCookie } from "../../client_frontend/http/adapter.js";

function createResponseMock() {
  const headers = new Map();
  return {
    getHeader(name) {
      return headers.get(String(name).toLowerCase());
    },
    setHeader(name, value) {
      headers.set(String(name).toLowerCase(), value);
    }
  };
}

test("pipeline session cookies omit Secure on plain localhost http", () => {
  const rootDir = mkdtempSync(path.join(tmpdir(), "vp-cookie-http-"));
  mkdirSync(rootDir, { recursive: true });
  const response = createResponseMock();
  const request = {
    headers: { host: "127.0.0.1:3000" },
    socket: { encrypted: false }
  };

  setPipelineSessionCookie(rootDir, response, "session-1", request);

  const cookie = String(response.getHeader("set-cookie") || "");
  assert.match(cookie, /vp_pipeline_session=/);
  assert.doesNotMatch(cookie, /;\s*Secure/i);
});

test("ontology session cookies use the ontology session namespace", () => {
  const rootDir = mkdtempSync(path.join(tmpdir(), "vp-cookie-ontology-"));
  mkdirSync(rootDir, { recursive: true });
  const response = createResponseMock();

  setOntologySessionCookie(rootDir, response, "session-ontology");

  const cookie = String(response.getHeader("set-cookie") || "");
  assert.match(cookie, /vp_ontology_session=/);
});

test("query session cookies keep Secure on https requests", () => {
  const rootDir = mkdtempSync(path.join(tmpdir(), "vp-cookie-https-"));
  mkdirSync(rootDir, { recursive: true });
  const response = createResponseMock();
  const request = {
    headers: { host: "example.invalid", "x-forwarded-proto": "https" },
    socket: { encrypted: true }
  };

  setSessionCookie(rootDir, response, "session-2", request);

  const cookie = String(response.getHeader("set-cookie") || "");
  assert.match(cookie, /vp_session=/);
  assert.match(cookie, /;\s*Secure/i);
});
