export async function postJson(url, { payload, headers = {}, timeoutMs = 60_000 } = {}) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...headers
    },
    body: JSON.stringify(payload || {}),
    signal: AbortSignal.timeout(timeoutMs)
  });
  const rawText = await response.text();
  let body;
  try {
    body = rawText.trim() ? JSON.parse(rawText) : {};
  } catch {
    body = { raw_text: rawText };
  }
  return {
    status_code: response.status,
    headers: Object.fromEntries(response.headers.entries()),
    body: body && typeof body === "object" ? body : { raw_text: rawText },
    raw_text: rawText
  };
}
