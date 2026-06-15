import assert from "node:assert/strict";
import test from "node:test";

import { withMemoryStore } from "./memory-test-fixtures.js";

test("topics extract capitalized German nouns", () => {
  withMemoryStore((store) => {
    store.record("chat-1", "Zeig mir Rechnungen von Telekom", "Hier sind 3 Rechnungen der Telekom aus dem Jahr 2024.");
    const topics = store.recent(1)[0].topics;
    assert.ok(topics.includes("Rechnungen"));
    assert.ok(topics.includes("Telekom"));
  });
});

test("topics filter out stop words", () => {
  withMemoryStore((store) => {
    store.record("chat-1", "Sind diese Dokumente relevant?", "Die Dokumente sind alle relevant. Nicht alle haben Betraege.");
    const topics = store.recent(1)[0].topics;
    assert.ok(!topics.includes("Die"));
    assert.ok(!topics.includes("Nicht"));
    assert.ok(topics.includes("Dokumente"));
  });
});

test("topics cap at 6 entries", () => {
  withMemoryStore((store) => {
    store.record("chat-1", "Zeig Rechnungen Vertraege Angebote Briefe Policen Quittungen Belege", "Hier sind Rechnungen, Vertraege, Angebote, Briefe, Policen, Quittungen und Belege.");
    assert.ok(store.recent(1)[0].topics.length <= 6);
  });
});

test("topics extract numbers with units", () => {
  withMemoryStore((store) => {
    store.record("chat-1", "Wie viele Rechnungen?", "Es gibt 47 Rechnungen im Archiv mit einem Gesamtwert von 3.500 Euro.");
    const topics = store.recent(1)[0].topics;
    assert.ok(topics.some((topic) => topic.includes("47 Rechnungen")));
    assert.ok(topics.some((topic) => topic.includes("3.500 Euro")));
  });
});

test("topics extract numbers with any noun, not just whitelisted units", () => {
  withMemoryStore((store) => {
    store.record("chat-1", "Wie viele Mitarbeiter sind erfasst?", "Es sind 23 Mitarbeiter in den Dokumenten erfasst.");
    assert.ok(store.recent(1)[0].topics.some((topic) => topic.includes("23 Mitarbeiter")));
  });
});

test("topics skip number+stop-word combinations", () => {
  withMemoryStore((store) => {
    store.record("chat-1", "Test", "In 3 Faellen wurden 5 Policen gefunden.");
    const topics = store.recent(1)[0].topics;
    assert.ok(topics.some((topic) => topic.includes("5 Policen")));
    assert.ok(!topics.some((topic) => /\d+\s+(Die|Der|Das|Nicht|Alle)/.test(topic)));
  });
});

test("handles unicode in messages and summaries", () => {
  withMemoryStore((store) => {
    store.record("chat-1", "Ärztekammer München Straßenbahn", "Die Über-Öffnungszeiten der Ärztekammer sind verfügbar.");
    const memory = store.recent(1)[0];
    assert.match(memory.user_message, /Ärztekammer/);
    assert.match(memory.assistant_summary, /Über-Öffnungszeiten/);
    assert.ok(memory.topics.some((topic) => topic === "Ärztekammer"));
  });
});
