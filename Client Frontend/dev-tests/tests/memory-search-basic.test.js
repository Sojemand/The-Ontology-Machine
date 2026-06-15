import assert from "node:assert/strict";
import test from "node:test";

import { withMemoryStore } from "./memory-test-fixtures.js";

test("search finds memories by user message keyword", () => {
  withMemoryStore((store) => {
    store.record("chat-1", "Wie viele Rechnungen habe ich?", "Sie haben 47 Rechnungen.");
    store.record("chat-1", "Zeig mir Vertraege", "Es gibt 12 Vertraege im Archiv.");
    store.record("chat-2", "Was kostet die Versicherung?", "Die Versicherung kostet 120 Euro.");
    const results = store.search("Rechnungen");
    assert.equal(results.length, 1);
    assert.match(results[0].user_message, /Rechnungen/);
  });
});

test("search finds memories by summary keyword", () => {
  withMemoryStore((store) => {
    store.record("chat-1", "Was gibt es?", "Es gibt 12 Vertraege im Archiv.");
    store.record("chat-2", "Noch was?", "Die Versicherung kostet 120 Euro monatlich.");
    const results = store.search("Versicherung");
    assert.equal(results.length, 1);
    assert.match(results[0].assistant_summary, /Versicherung/);
  });
});

test("search with multiple keywords uses OR logic", () => {
  withMemoryStore((store) => {
    store.record("chat-1", "Rechnungen zeigen", "47 Rechnungen gefunden.");
    store.record("chat-2", "Vertraege zeigen", "12 Vertraege gefunden.");
    store.record("chat-3", "Wetter morgen", "Kann ich nicht beantworten.");
    assert.equal(store.search("Rechnungen Vertraege").length, 2);
  });
});

test("search returns info instead of unrelated recent memories for vague queries", () => {
  withMemoryStore((store) => {
    store.record({ ownerId: "user-1", chatId: "chat-1", userMsg: "Wie viele Dokumente?", assistantAnswer: "Es gibt 5 Dokumente." });
    const result = store.search({ ownerId: "user-1", query: "ab cd" });
    assert.equal(result.results.length, 0);
    assert.match(result.info, /too broad/i);
  });
});

test("search handles punctuation and natural language queries", () => {
  withMemoryStore((store) => {
    store.record({ ownerId: "user-1", chatId: "chat-1", userMsg: "Zeig mir die Telekom Rechnungen", assistantAnswer: "Es gibt 3 Rechnungen der Telekom." });
    assert.equal(store.search({ ownerId: "user-1", query: "Telekom?" }).results.length, 1);
    const naturalLanguageResult = store.search({ ownerId: "user-1", query: "Was war nochmal mit der Rechnung?" });
    assert.equal(naturalLanguageResult.results.length, 1);
    assert.match(naturalLanguageResult.results[0].assistant_summary, /Telekom/);
  });
});

test("search respects limit", () => {
  withMemoryStore((store) => {
    for (let index = 0; index < 20; index += 1) {
      store.record(`chat-${index}`, `Rechnung ${index}`, `Rechnung ${index} gefunden.`);
    }
    assert.equal(store.search("Rechnung", 3).length, 3);
  });
});

test("search is case-insensitive", () => {
  withMemoryStore((store) => {
    store.record("chat-1", "Wie viele Rechnungen?", "Sie haben 47 Rechnungen.");
    assert.equal(store.search("rechnungen").length, 1);
    assert.equal(store.search("RECHNUNGEN").length, 1);
  });
});

test("search also matches topics column", () => {
  withMemoryStore((store) => {
    store.record("chat-1", "Telekom Rechnungen", "Kurze Antwort.");
    assert.equal(store.search("Telekom").length, 1);
  });
});

test("search returns empty array when no match", () => {
  withMemoryStore((store) => {
    store.record("chat-1", "Hallo Welt", "Guten Tag.");
    assert.equal(store.search("Versicherung").length, 0);
  });
});

test("search filters query stop words", () => {
  withMemoryStore((store) => {
    store.record("chat-1", "Wie viele Mitarbeiter?", "Es sind 23 Mitarbeiter erfasst.");
    store.record("chat-2", "Zeig mir Rechnungen", "47 Rechnungen gefunden.");
    const results = store.search("Über wieviele Mitarbeiter haben wir geredet?");
    assert.equal(results.length, 1);
    assert.match(results[0].user_message, /Mitarbeiter/);
  });
});
