import { randomUUID } from "node:crypto";

const DEFAULT_SESSION_TTL_MS = 30 * 60 * 1000;
const DEFAULT_ADMIN_SESSION_TTL_SECONDS = 15 * 60;

export function createSessionManager({ maxSessions = 64, ttlMs = DEFAULT_SESSION_TTL_MS } = {}) {
  const sessions = new Map();
  const sessionMessages = new Map();
  const sessionLastSeen = new Map();
  const sessionQueues = new Map();
  const sessionOwners = new Map();

  function deleteSession(sessionId) {
    sessions.delete(sessionId);
    sessionMessages.delete(sessionId);
    sessionLastSeen.delete(sessionId);
    sessionQueues.delete(sessionId);
    sessionOwners.delete(sessionId);
  }

  function purgeExpired(now = Date.now()) {
    for (const [sessionId, lastSeen] of sessionLastSeen) {
      if (now - lastSeen > ttlMs) {
        deleteSession(sessionId);
      }
    }
  }

  function touch(sessionId) {
    const now = Date.now();
    if (sessionLastSeen.has(sessionId)) {
      sessionLastSeen.delete(sessionId);
    }
    sessionLastSeen.set(sessionId, now);
    if (sessionLastSeen.size > maxSessions) {
      purgeExpired(now);
      if (sessionLastSeen.size > maxSessions) {
        const oldest = sessionLastSeen.entries().next().value;
        if (oldest) {
          deleteSession(oldest[0]);
        }
      }
    }
  }

  function runSerialized(sessionId, task) {
    const previous = sessionQueues.get(sessionId) || Promise.resolve();
    const next = previous.catch(() => {}).then(task);
    const tracked = next.catch(() => {});
    sessionQueues.set(sessionId, tracked);
    return next.finally(() => {
      if (sessionQueues.get(sessionId) === tracked) {
        sessionQueues.delete(sessionId);
      }
    });
  }

  return {
    deleteSession,
    touch,
    runSerialized,
    getHistory(sessionId) {
      return sessions.get(sessionId) || [];
    },
    setHistory(sessionId, history) {
      sessions.set(sessionId, history);
    },
    getOwnerId(sessionId) {
      return sessionOwners.get(sessionId) || "";
    },
    setOwnerId(sessionId, ownerId) {
      if (ownerId) {
        sessionOwners.set(sessionId, ownerId);
        return;
      }
      sessionOwners.delete(sessionId);
    },
    getDisplayMessages(sessionId) {
      return sessionMessages.get(sessionId) || [];
    },
    setDisplayMessages(sessionId, messages) {
      sessionMessages.set(sessionId, messages);
    },
    listDisplaySessions() {
      return Array.from(sessionMessages.entries()).map(([sessionId, messages]) => ({
        sessionId,
        ownerId: sessionOwners.get(sessionId) || "",
        messages: Array.isArray(messages) ? [...messages] : []
      }));
    },
    clear() {
      sessions.clear();
      sessionMessages.clear();
      sessionLastSeen.clear();
      sessionQueues.clear();
      sessionOwners.clear();
    }
  };
}

export function createAdminSessionManager({ ttlSeconds = DEFAULT_ADMIN_SESSION_TTL_SECONDS } = {}) {
  const adminSessions = new Map();
  const ttlMs = ttlSeconds * 1000;

  function purgeExpired(now = Date.now()) {
    for (const [token, session] of adminSessions) {
      if (session.expiresAt <= now) {
        adminSessions.delete(token);
      }
    }
  }

  return {
    create(secret) {
      purgeExpired();
      const token = randomUUID();
      adminSessions.set(token, { expiresAt: Date.now() + ttlMs, secret });
      return token;
    },
    has(token, secret) {
      if (!secret) {
        return true;
      }
      purgeExpired();
      if (!token) {
        return false;
      }
      const session = adminSessions.get(token);
      if (!session || session.secret !== secret) {
        adminSessions.delete(token);
        return false;
      }
      session.expiresAt = Date.now() + ttlMs;
      return true;
    },
    clear() {
      adminSessions.clear();
    }
  };
}
