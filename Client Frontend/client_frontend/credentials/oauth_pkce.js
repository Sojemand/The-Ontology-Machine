import { createHash, randomBytes } from "node:crypto";

function toBase64Url(buffer) {
  return buffer.toString("base64").replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

export function generateCodeVerifier(length = 64) {
  const targetLength = Math.max(43, Number(length) || 64);
  return toBase64Url(randomBytes(targetLength)).slice(0, targetLength);
}

export function buildCodeChallenge(verifier) {
  return toBase64Url(createHash("sha256").update(String(verifier || ""), "ascii").digest());
}

export function generateState() {
  return toBase64Url(randomBytes(24));
}
