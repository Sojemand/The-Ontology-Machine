export function serializeMessages(messages) {
  return JSON.stringify(messages);
}

export function parseStoredMessages(rawMessages) {
  try {
    const parsed = JSON.parse(rawMessages);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function toChatListEntry(row) {
  return {
    id: row.id,
    title: row.title,
    created_at: row.created_at,
    updated_at: row.updated_at,
    message_count: parseStoredMessages(row.messages).length
  };
}

export function toChatDetail(row) {
  return {
    id: row.id,
    title: row.title,
    messages: parseStoredMessages(row.messages),
    created_at: row.created_at,
    updated_at: row.updated_at
  };
}
