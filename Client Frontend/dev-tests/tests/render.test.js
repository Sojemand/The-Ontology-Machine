import assert from "node:assert/strict";
import test from "node:test";
import { JSDOM } from "jsdom";

import {
  buildViewerPresentation,
  collectMessageSources,
  extractReferencedSources,
  getMessageReferencedSources,
  getMessageRenderSources,
  renderMessagesHtml,
  renderSourcesHtml
} from "../../src/ui/render.ts";

function source(overrides = {}) {
  return {
    id: "doc-1",
    title: "Titel",
    type: "invoice",
    date: "2024-01-10",
    actor: "ACME",
    page: 1,
    page_count: 3,
    source_refs: ["page1"],
    snippet: "Snippet",
    image_url: "/api/image/doc-1/1",
    viewer_available: true,
    file_name: "alpha.pdf",
    ...overrides
  };
}

test("renderMessagesHtml escapes HTML and links exact citation tokens", () => {
  const messageSource = source({ id: "doc-special", file_name: "alpha(1)+?.pdf", source_page: 7, page: 7 });
  const html = renderMessagesHtml([
    {
      role: "assistant",
      content: 'Bitte pruefen Sie alpha(1)+?.pdf, page 7 {{cite:doc:doc-special}} und <script>alert("xss")</script> [1]',
      sources: [messageSource]
    }
  ]);
  const dom = new JSDOM(`<body>${html}</body>`);

  assert.equal(dom.window.document.querySelector("script"), null);
  assert.match(dom.window.document.body.textContent, /<script>alert\("xss"\)<\/script>/);
  assert.equal(dom.window.document.querySelectorAll(".source-inline-tag").length, 1);
  assert.equal(dom.window.document.querySelector(".source-inline-tag")?.textContent, "p.7");
  assert.match(dom.window.document.body.textContent, /\[1\]/);
});

test("renderMessagesHtml marks unresolved citation tokens as suspect", () => {
  const html = renderMessagesHtml([
    {
      role: "assistant",
      content: "Bitte alpha.pdf pruefen. Suspekt: {{cite:doc:missing-doc}} und [2].",
      sources: [source({ id: "doc-1", file_name: "alpha.pdf" })]
    }
  ]);
  const dom = new JSDOM(`<body>${html}</body>`);

  assert.equal(dom.window.document.querySelectorAll(".source-inline-tag").length, 0);
  assert.equal(dom.window.document.querySelectorAll(".source-unresolved-tag").length, 1);
  assert.equal(dom.window.document.querySelector(".source-unresolved-tag")?.textContent, "unresolved source");
});

test("renderMessagesHtml leaves plain file names as text when no citation token exists", () => {
  const html = renderMessagesHtml([
    {
      role: "assistant",
      content: "Quelle: Fantasy Story 3.odt",
      sources: [source({ id: "doc-1", file_name: "alpha.pdf" })]
    }
  ]);
  const dom = new JSDOM(`<body>${html}</body>`);

  assert.equal(dom.window.document.querySelectorAll(".source-unresolved-tag").length, 0);
  assert.equal(dom.window.document.querySelectorAll(".citation-button").length, 0);
  assert.match(dom.window.document.body.textContent || "", /Fantasy Story 3\.odt/);
});

test("renderSourcesHtml escapes untrusted source text without creating nodes", () => {
  const html = renderSourcesHtml(
    [
      source({
        title: '<img src=x onerror="alert(1)">',
        snippet: '<svg><script>alert(1)</script></svg>',
        actor: "A < B",
        source_refs: ['"><b>bad</b>']
      })
    ],
    null
  );
  const dom = new JSDOM(`<body>${html}</body>`);

  assert.equal(dom.window.document.querySelector("img"), null);
  assert.equal(dom.window.document.querySelector("script"), null);
  assert.match(dom.window.document.body.textContent, /<img src=x onerror="alert\(1\)">/);
  assert.match(dom.window.document.body.textContent, /<svg><script>alert\(1\)<\/script><\/svg>/);
  assert.match(dom.window.document.body.textContent, /A < B/);
});

test("extractReferencedSources resolves only exact citation tokens", () => {
  const first = source({ id: "doc-1", file_name: "alpha.pdf" });
  const second = source({ id: "doc-2", file_name: "beta.pdf" });

  const referenced = extractReferencedSources("Siehe beta.pdf [1] und {{cite:doc:doc-2}}", [first, second]);

  assert.deepEqual(
    referenced.map((item) => item.id),
    ["doc-2"]
  );
});

test("extractReferencedSources keeps page-wise sources distinct when file names repeat", () => {
  const page10 = source({ id: "book.pdf.p010.of102", file_name: "book.pdf", source_page: 10, page: 10 });
  const page95 = source({ id: "book.pdf.p095.of102", file_name: "book.pdf", source_page: 95, page: 95 });

  const referenced = extractReferencedSources("book.pdf, page 10 {{cite:doc:book.pdf.p010.of102}}", [page95, page10]);

  assert.deepEqual(
    referenced.map((item) => [item.id, item.page]),
    [["book.pdf.p010.of102", 10]]
  );
});

test("collectMessageSources deduplicates the chat source catalog by source id", () => {
  const merged = collectMessageSources([
    { role: "assistant", content: "A", sources: [source(), source({ id: "doc-2", file_name: "beta.pdf" })] },
    { role: "assistant", content: "B", sources: [source({ id: "doc-1", title: "ignored" }), source({ id: "doc-3" })] }
  ]);

  assert.deepEqual(
    merged.map((item) => item.id),
    ["doc-1", "doc-2", "doc-3"]
  );
});

test("collectMessageSources deduplicates page bundle sources by source key", () => {
  const merged = collectMessageSources([
    { role: "assistant", content: "A", sources: [source({ id: "doc-1", source_key: "hash:bundle" })] },
    { role: "assistant", content: "B", sources: [source({ id: "doc-2", source_key: "hash:bundle", title: "same bundle" })] }
  ]);

  assert.deepEqual(
    merged.map((item) => item.id),
    ["doc-1"]
  );
});

test("message source helpers resolve tokens only against the current message sources", () => {
  const alpha = source({ id: "doc-1", file_name: "alpha.pdf" });
  const beta = source({ id: "doc-2", file_name: "beta.pdf" });
  const message = { role: "assistant", content: "Nur {{cite:doc:doc-1}}", sources: [beta] };

  assert.deepEqual(getMessageRenderSources(message, [alpha, beta]).map((item) => item.id), ["doc-2"]);
  assert.deepEqual(getMessageReferencedSources(message, [alpha, beta]).map((item) => item.id), []);
});

test("message source helpers ignore invalid citation tokens", () => {
  const alpha = source({ id: "doc-1", file_name: "alpha.pdf" });
  const referenced = getMessageReferencedSources({ role: "assistant", content: "Nur {{cite:doc:doc-3}}", sources: [alpha] }, [alpha]);

  assert.deepEqual(referenced, []);
});

test("renderMessagesHtml does not resolve restored tokens from previous-turn sources", () => {
  const html = renderMessagesHtml([
    {
      role: "assistant",
      content: "Fruehere Antwort zu alpha.pdf {{cite:doc:doc-1}}",
      sources: [source()]
    },
    {
      role: "assistant",
      content: "Spaetere Notiz: Quelle alpha.pdf {{cite:doc:doc-1}}",
      sources: []
    }
  ]);
  const dom = new JSDOM(`<body>${html}</body>`);
  const messages = dom.window.document.querySelectorAll(".message-assistant");

  assert.equal(messages[0].querySelectorAll(".citation-button").length, 1);
  assert.equal(messages[1].querySelectorAll(".citation-button").length, 0);
  assert.equal(messages[1].querySelectorAll(".source-unresolved-tag").length, 1);
});

test("renderMessagesHtml reconstructs collapsed inline markdown tables from stored chat text", () => {
  const html = renderMessagesHtml([
    {
      role: "assistant",
      content:
        "Vor der Tabelle | Feld | Wert | |---|---| | alpha | beta | | gamma | delta |",
      sources: []
    }
  ]);
  const dom = new JSDOM(`<body>${html}</body>`);
  const table = dom.window.document.querySelector(".message-table");

  assert.ok(table);
  assert.match(dom.window.document.body.textContent || "", /Vor der Tabelle/);
  assert.match(table.textContent || "", /alpha/);
  assert.match(table.textContent || "", /gamma/);
});

test("buildViewerPresentation handles empty, failed and successful viewer states", () => {
  const empty = buildViewerPresentation({
    selectedSource: null,
    page: 1,
    imageFailed: false
  });
  assert.equal(empty.imageSrc, null);

  const failed = buildViewerPresentation({
    selectedSource: source({ id: "doc-2", page_count: 2, viewer_available: true }),
    page: 2,
    imageFailed: true
  });
  assert.equal(failed.imageSrc, null);
  assert.match(failed.placeholderText, /unavailable/i);

  const success = buildViewerPresentation({
    selectedSource: source({ id: "doc-3", page_count: 2, viewer_available: true }),
    page: 2,
    imageFailed: false
  });
  assert.equal(success.imageSrc, "/api/image/doc-3/2");
  assert.equal(success.disablePrev, false);
  assert.equal(success.disableNext, true);
});

