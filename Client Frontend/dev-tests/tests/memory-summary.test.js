import assert from "node:assert/strict";
import test from "node:test";

import { withMemoryStore } from "./memory-test-fixtures.js";

test("record stores a memory that appears in recent()", () => {
  withMemoryStore((store) => {
    store.record("chat-1", "Wie viele Rechnungen habe ich?", "Sie haben insgesamt 47 Rechnungen im Archiv.");
    const memories = store.recent(5);
    assert.equal(memories.length, 1);
    assert.equal(memories[0].chat_id, "chat-1");
    assert.equal(memories[0].user_message, "Wie viele Rechnungen habe ich?");
    assert.ok(memories[0].assistant_summary.length > 0);
    assert.ok(memories[0].assistant_summary.length <= 150);
    assert.ok(memories[0].created_at > 0);
    assert.ok(Array.isArray(memories[0].topics));
  });
});

test("summary extracts first meaningful sentence", () => {
  withMemoryStore((store) => {
    store.record("chat-1", "Was kostet der Vertrag?", "Der Vertrag kostet monatlich 49,90 Euro. Weitere Details finden Sie im Dokument.");
    assert.match(store.recent(1)[0].assistant_summary, /Der Vertrag kostet monatlich 49,90 Euro/);
  });
});

test("summary keeps answer-centric content", () => {
  withMemoryStore((store) => {
    store.record("chat-1", "Was gibt es Neues?", "Es gibt 3 neue Dokumente im Archiv.");
    const memories = store.recent(1);
    assert.equal(memories[0].assistant_summary, "Es gibt 3 neue Dokumente im Archiv.");
    assert.ok(!memories[0].assistant_summary.includes("Was gibt es Neues"));
  });
});

test("summary strips citations and markdown before storage", () => {
  withMemoryStore((store) => {
    store.record({ ownerId: "user-1", chatId: "chat-1", userMsg: "Worum geht es?", assistantAnswer: "**Der Vertrag** kostet 120 Euro [1]. Mehr Details finden Sie im Dokument." });
    const memories = store.recent({ ownerId: "user-1", limit: 1 });
    assert.equal(memories[0].assistant_summary, "Der Vertrag kostet 120 Euro .");
    assert.ok(!memories[0].assistant_summary.includes("[1]"));
    assert.ok(!memories[0].assistant_summary.includes("**"));
  });
});

test("summary truncates very long first sentences", () => {
  withMemoryStore((store) => {
    store.record("chat-1", "Frage", `${"A".repeat(200)}. Zweiter Satz.`);
    assert.ok(store.recent(1)[0].assistant_summary.length <= 150);
  });
});

test("summary skips filler sentences", () => {
  withMemoryStore((store) => {
    store.record("chat-1", "Zeig mir Rechnungen", "Ich habe dazu folgende Ergebnisse gefunden. Es gibt 47 Rechnungen im Archiv.");
    const summary = store.recent(1)[0].assistant_summary;
    assert.match(summary, /47 Rechnungen/);
    assert.ok(!summary.includes("Ich habe dazu"));
  });
});

test("summary skips multiple filler patterns", () => {
  withMemoryStore((store) => {
    store.record("chat-1", "Was kostet das?", "Gerne! Basierend auf den Daten kostet der Vertrag 120 Euro monatlich.");
    assert.match(store.recent(1)[0].assistant_summary, /120 Euro/);
  });
});

test("record skips smalltalk messages", () => {
  withMemoryStore((store) => {
    store.record("chat-1", "Hallo", "Guten Tag!");
    store.record("chat-1", "Danke!", "Gerne geschehen!");
    store.record("chat-1", "Ok", "Alles klar.");
    store.record("chat-1", "Tschüss!", "Auf Wiedersehen!");
    assert.equal(store.recent(10).length, 0);
  });
});

test("record stores non-smalltalk messages", () => {
  withMemoryStore((store) => {
    store.record("chat-1", "Hallo", "Guten Tag!");
    store.record("chat-1", "Wie viele Rechnungen habe ich?", "Sie haben 47 Rechnungen.");
    assert.equal(store.recent(10).length, 1);
    assert.match(store.recent(10)[0].user_message, /Rechnungen/);
  });
});

test("record skips generic fallback answers", () => {
  withMemoryStore((store) => {
    const stored = store.record({
      ownerId: "user-1",
      chatId: "chat-1",
      userMsg: "Mach eine Auswertung",
      assistantAnswer: "Die Anfrage hat zu viele Zwischenergebnisse erzeugt. Bitte formulieren Sie konkreter."
    });
    assert.equal(stored, false);
    assert.equal(store.recent({ ownerId: "user-1", limit: 10 }).length, 0);
  });
});
