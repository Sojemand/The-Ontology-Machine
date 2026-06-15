import assert from "node:assert/strict";
import test from "node:test";

import { withMemoryStore } from "./memory-test-fixtures.js";

test("search ranks multi-keyword matches higher", () => {
  withMemoryStore((store) => {
    store.record("chat-1", "Rechnungen anzeigen", "47 Rechnungen gefunden.");
    store.record("chat-2", "Telekom Rechnungen anzeigen", "12 Rechnungen der Telekom gefunden.");
    store.record("chat-3", "Telekom Kontakt", "Die Telekom Hotline ist erreichbar.");
    const results = store.search("Telekom Rechnungen");
    assert.ok(results.length >= 2);
    assert.match(results[0].user_message, /Telekom/);
    assert.match(results[0].user_message, /Rechnungen/);
  });
});

test("search deduplicates by chat_id", () => {
  withMemoryStore((store) => {
    store.record("chat-1", "Rechnungen zeigen", "47 Rechnungen gefunden.");
    store.record("chat-1", "Mehr Rechnungen", "Weitere 10 Rechnungen geladen.");
    store.record("chat-1", "Alle Rechnungen", "Alle 57 Rechnungen angezeigt.");
    store.record("chat-2", "Telekom Rechnungen", "3 Rechnungen der Telekom.");
    const chatIds = store.search("Rechnungen").map((result) => result.chat_id);
    assert.equal(chatIds.length, new Set(chatIds).size);
    assert.equal(chatIds.length, 2);
  });
});

test("search ranks recent memories higher", () => {
  withMemoryStore((store) => {
    store.record("chat-old", "Alte Rechnungen", "Es gab 10 Rechnungen.");
    store.record("chat-new", "Neue Rechnungen", "Es gibt 47 Rechnungen.");
    const results = store.search("Rechnungen");
    assert.ok(results.length >= 2);
    assert.equal(results[0].chat_id, "chat-new");
  });
});

test("search isolates memories by owner scope", () => {
  withMemoryStore((store) => {
    store.record({ ownerId: "user-a", chatId: "chat-a-1", userMsg: "Telekom Rechnungen", assistantAnswer: "Es gibt 3 Telekom Rechnungen." });
    store.record({ ownerId: "user-a", chatId: "chat-a-2", userMsg: "Mehr Telekom Rechnungen", assistantAnswer: "Es gibt 5 Telekom Rechnungen." });
    store.record({ ownerId: "user-b", chatId: "chat-b-1", userMsg: "Telekom Rechnungen", assistantAnswer: "Es gibt 9 Telekom Rechnungen." });
    const resultA = store.search({ ownerId: "user-a", query: "Telekom Rechnungen" });
    const resultB = store.search({ ownerId: "user-b", query: "Telekom Rechnungen" });
    assert.equal(resultA.results.length, 2);
    assert.equal(resultB.results.length, 1);
    assert.match(resultA.results[0].assistant_summary, /(3|5) Telekom/);
    assert.match(resultB.results[0].assistant_summary, /9 Telekom/);
  });
});

test("search matches umlaut aliases and lowercase unicode", () => {
  withMemoryStore((store) => {
    store.record({ ownerId: "user-1", chatId: "chat-1", userMsg: "Ärztekammer München", assistantAnswer: "Die Über-Öffnungszeiten der Ärztekammer sind verfügbar." });
    assert.equal(store.search({ ownerId: "user-1", query: "ärztekammer" }).results.length, 1);
    assert.equal(store.search({ ownerId: "user-1", query: "aerztekammer" }).results.length, 1);
    assert.equal(store.search({ ownerId: "user-1", query: "uber" }).results.length, 1);
  });
});
