/**
 * Token estimation utilities for context window management.
 *
 * Uses chars / 3.5 heuristic -- conservative for German compound words,
 * overestimates by ~10-15% which is the safe direction (trim sooner
 * rather than hit the API limit).
 */

const CHARS_PER_TOKEN = 3.5;
const MESSAGE_OVERHEAD = 4; // per-message framing tokens (role, delimiters)

/**
 * Estimate token count for a single string.
 * @param {string} text
 * @returns {number}
 */
export function estimateTokens(text) {
  const len = String(text || "").length;
  return len === 0 ? 0 : Math.ceil(len / CHARS_PER_TOKEN);
}

/**
 * Estimate total token count for an array of chat messages.
 * Accounts for content, tool_calls arguments, and per-message overhead.
 * @param {Array<{content?: string, tool_calls?: Array<{function?: {arguments?: string}}>}>} messages
 * @returns {number}
 */
export function estimateMessagesTokens(messages) {
  if (!Array.isArray(messages)) return 0;

  let total = 0;
  for (const msg of messages) {
    total += MESSAGE_OVERHEAD;
    total += estimateTokens(msg.content);
    if (Array.isArray(msg.tool_calls)) {
      for (const tc of msg.tool_calls) {
        total += estimateTokens(tc.function?.arguments);
      }
    }
  }
  return total;
}
