/**
 * @typedef {{
 *   id: number,
 *   owner_id: string,
 *   chat_id: string,
 *   user_message: string,
 *   assistant_summary: string,
 *   topics: string[] | string,
 *   created_at: number
 * }} MemoryRow
 */

export function serializeTopics(topics) {
  return JSON.stringify(Array.isArray(topics) ? topics.filter(Boolean) : []);
}

export function parseTopics(topicsValue) {
  if (!topicsValue) return [];
  if (Array.isArray(topicsValue)) return topicsValue.filter(Boolean);
  try {
    const parsed = JSON.parse(topicsValue);
    return Array.isArray(parsed) ? parsed.filter(Boolean) : [];
  } catch {
    return [];
  }
}

/**
 * @param {MemoryRow} row
 */
export function toPublicMemoryRow(row) {
  return {
    id: row.id,
    owner_id: row.owner_id,
    chat_id: row.chat_id,
    user_message: row.user_message,
    assistant_summary: row.assistant_summary,
    topics: parseTopics(row.topics),
    created_at: row.created_at
  };
}
