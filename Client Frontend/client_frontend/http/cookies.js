import { randomUUID } from "node:crypto";

import { signScopedValue, verifySignedValue } from "../vault.js";

const SESSION_COOKIE_NAME = "vp_session";
const PIPELINE_SESSION_COOKIE_NAME = "vp_pipeline_session";
const ONTOLOGY_SESSION_COOKIE_NAME = "vp_ontology_session";
const ADMIN_COOKIE_NAME = "vp_admin";
const ADMIN_SESSION_TTL_SECONDS = 15 * 60;
const USER_COOKIE_NAME = "vp_user";
const USER_COOKIE_MAX_AGE_SECONDS = 365 * 24 * 60 * 60;
const COOKIE_SCOPE_PREFIX = "http-cookie";

function safeDecodeURIComponent(value) {
  try {
    return decodeURIComponent(value);
  } catch {
    return null;
  }
}

function appendCookie(response, cookieValue) {
  const existing = response.getHeader("Set-Cookie");
  if (!existing) {
    response.setHeader("Set-Cookie", cookieValue);
    return;
  }
  response.setHeader("Set-Cookie", [...(Array.isArray(existing) ? existing : [existing]), cookieValue]);
}

function cookieScope(name) {
  return `${COOKIE_SCOPE_PREFIX}:${name}`;
}

function getVerifiedCookieValue(rootDir, cookies, name) {
  return verifySignedValue(rootDir, cookieScope(name), cookies?.[name]) || null;
}

function shouldUseSecureCookies(request) {
  if (!request) return false;
  if (request.socket?.encrypted) return true;
  const forwardedProto = String(request.headers?.["x-forwarded-proto"] || "").toLowerCase();
  return forwardedProto.split(",").map((item) => item.trim()).includes("https");
}

function serializeCookieAttributes(request, { path: cookiePath = "/", maxAgeSeconds = null } = {}) {
  const parts = [`Path=${cookiePath}`, "HttpOnly", "SameSite=Strict"];
  if (Number.isFinite(maxAgeSeconds)) parts.push(`Max-Age=${Math.trunc(Number(maxAgeSeconds))}`);
  if (shouldUseSecureCookies(request)) parts.push("Secure");
  return parts.join("; ");
}

function setSignedCookie(rootDir, response, name, value, attributes) {
  appendCookie(response, `${name}=${signScopedValue(rootDir, cookieScope(name), value)}; ${attributes}`);
}

function setUserCookie(rootDir, response, userId, request = null) {
  setSignedCookie(
    rootDir,
    response,
    USER_COOKIE_NAME,
    userId,
    serializeCookieAttributes(request, { path: "/", maxAgeSeconds: USER_COOKIE_MAX_AGE_SECONDS })
  );
}

export function parseCookies(cookieHeader) {
  return String(cookieHeader || "")
    .split(";")
    .map((part) => part.trim())
    .filter(Boolean)
    .reduce((cookies, part) => {
      const separatorIndex = part.indexOf("=");
      if (separatorIndex < 0) {
        return cookies;
      }
      const key = part.slice(0, separatorIndex).trim();
      const value = safeDecodeURIComponent(part.slice(separatorIndex + 1));
      if (key && value != null) {
        cookies[key] = value;
      }
      return cookies;
    }, {});
}

export function getSessionIdFromCookies(rootDir, cookies) {
  return getVerifiedCookieValue(rootDir, cookies, SESSION_COOKIE_NAME);
}

export function getPipelineSessionIdFromCookies(rootDir, cookies) {
  return getVerifiedCookieValue(rootDir, cookies, PIPELINE_SESSION_COOKIE_NAME);
}

export function getOntologySessionIdFromCookies(rootDir, cookies) {
  return getVerifiedCookieValue(rootDir, cookies, ONTOLOGY_SESSION_COOKIE_NAME);
}

export function getAdminTokenFromCookies(rootDir, cookies) {
  return getVerifiedCookieValue(rootDir, cookies, ADMIN_COOKIE_NAME);
}

export function getExistingUserId(rootDir, cookies) {
  return getVerifiedCookieValue(rootDir, cookies, USER_COOKIE_NAME);
}

export function resolveUserId(rootDir, response, cookies, fallbackId, request = null) {
  const existingUserId = getExistingUserId(rootDir, cookies);
  if (existingUserId) {
    return existingUserId;
  }
  const userId = fallbackId || getSessionIdFromCookies(rootDir, cookies) || randomUUID();
  setUserCookie(rootDir, response, userId, request);
  return userId;
}

export function setSessionCookie(rootDir, response, sessionId, request = null) {
  setSignedCookie(rootDir, response, SESSION_COOKIE_NAME, sessionId, serializeCookieAttributes(request));
}

export function setPipelineSessionCookie(rootDir, response, sessionId, request = null) {
  setSignedCookie(rootDir, response, PIPELINE_SESSION_COOKIE_NAME, sessionId, serializeCookieAttributes(request));
}

export function setOntologySessionCookie(rootDir, response, sessionId, request = null) {
  setSignedCookie(rootDir, response, ONTOLOGY_SESSION_COOKIE_NAME, sessionId, serializeCookieAttributes(request));
}

export function setAdminCookie(rootDir, response, token, request = null) {
  setSignedCookie(
    rootDir,
    response,
    ADMIN_COOKIE_NAME,
    token,
    serializeCookieAttributes(request, { path: "/config/api", maxAgeSeconds: ADMIN_SESSION_TTL_SECONDS })
  );
}
