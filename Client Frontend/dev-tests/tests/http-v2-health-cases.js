import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import test from "node:test";

import { createApplication } from "../../server/index.js";
import { createHttpServerFixture } from "./http-server-fixtures.js";
import { cleanupFixture, listen } from "./server-fixtures.js";

test("v2 health route exposes minimal-agent health fields", async () => {
  const fixture = createHttpServerFixture("vp-http-v2-");
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome });
  const baseUrl = await listen(app.server);

  try {
    const res = await fetch(`${baseUrl}/api/v2/health`);
    assert.equal(res.status, 200);
    const body = await res.json();
    assert.equal(body.api_version, "v2");
    assert.equal(body.corpus_docs, 1);
    assert.equal(body.llm_model, "gpt-5.4");
    assert.equal(body.agent_name, "TestBot");
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("v2 health route exposes base graph and ontology lens counts from the active corpus", async () => {
  const fixture = createHttpServerFixture("vp-http-v2-");
  const db = new DatabaseSync(fixture.dbPath);
  db.exec(`
    CREATE TABLE source_documents (source_document_id TEXT PRIMARY KEY, source_title TEXT);
    CREATE TABLE source_document_pages (source_document_id TEXT, document_id TEXT, page_index INTEGER);
    CREATE TABLE structural_units (unit_id TEXT PRIMARY KEY, unit_type TEXT, document_id TEXT);
    CREATE TABLE relations (relation_id TEXT PRIMARY KEY, relation_origin TEXT);
    CREATE TABLE ontology_lenses (ontology_id TEXT PRIMARY KEY, name TEXT, status TEXT);
    CREATE TABLE ontology_activation (ontology_id TEXT, scope TEXT, scope_ref TEXT, is_active INTEGER, is_primary INTEGER, activated_at TEXT);
  `);
  db.prepare("INSERT INTO source_documents (source_document_id, source_title) VALUES (?, ?)").run("src-1", "Source One");
  db.prepare("INSERT INTO source_document_pages (source_document_id, document_id, page_index) VALUES (?, ?, ?)").run("src-1", "doc-1", 0);
  db.prepare("INSERT INTO structural_units (unit_id, unit_type, document_id) VALUES (?, ?, ?)").run("unit-src-1", "base_unit", "doc-1");
  db.prepare("INSERT INTO structural_units (unit_id, unit_type, document_id) VALUES (?, ?, ?)").run("unit-page-1", "page_unit", "doc-1");
  db.prepare("INSERT INTO relations (relation_id, relation_origin) VALUES (?, ?)").run("rel-1", "base_graph");
  db.prepare("INSERT INTO ontology_lenses (ontology_id, name, status) VALUES (?, ?, ?)").run("lens-1", "Story Lens", "ready");
  db.prepare("INSERT INTO ontology_lenses (ontology_id, name, status) VALUES (?, ?, ?)").run("lens-2", "Tone Lens", "draft");
  db.prepare("INSERT INTO ontology_activation (ontology_id, scope, scope_ref, is_active, is_primary, activated_at) VALUES (?, ?, ?, ?, ?, ?)").run("lens-1", "corpus", "self", 1, 1, "2026-06-06T10:00:00Z");
  db.close();
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome });
  const baseUrl = await listen(app.server);

  try {
    const res = await fetch(`${baseUrl}/api/v2/health`);
    assert.equal(res.status, 200);
    const body = await res.json();
    assert.equal(body.database_status.base_graph.available, true);
    assert.equal(body.database_status.base_graph.dirty, false);
    assert.equal(body.database_status.base_graph.document_count, 1);
    assert.equal(body.database_status.base_graph.unmapped_document_count, 0);
    assert.equal(body.database_status.base_graph.source_document_count, 1);
    assert.equal(body.database_status.base_graph.source_page_count, 1);
    assert.equal(body.database_status.base_graph.relation_count, 1);
    assert.equal(body.database_status.ontology_lenses.count, 2);
    assert.equal(body.database_status.ontology_lenses.active_count, 1);
    assert.equal(body.database_status.ontology_lenses.primary_ontology_id, "lens-1");
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("v2 health route marks an existing base graph dirty when new documents are unmapped", async () => {
  const fixture = createHttpServerFixture("vp-http-v2-");
  const db = new DatabaseSync(fixture.dbPath);
  db.exec(`
    CREATE TABLE source_documents (source_document_id TEXT PRIMARY KEY, source_title TEXT);
    CREATE TABLE source_document_pages (source_document_id TEXT, document_id TEXT, page_index INTEGER);
  `);
  db.prepare("INSERT INTO source_documents (source_document_id, source_title) VALUES (?, ?)").run("src-1", "Source One");
  db.prepare("INSERT INTO source_document_pages (source_document_id, document_id, page_index) VALUES (?, ?, ?)").run("src-1", "doc-1", 0);
  db.prepare(`
    INSERT INTO documents (
      id, file_name, file_path, content_hash, document_type, category, subcategory,
      page_count, content_free_text
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(
    "doc-2",
    "beta.pdf",
    "./page_images/beta.pdf.hash",
    "sha256:doc-2",
    "letter",
    "test",
    "sample",
    1,
    "Fresh document after Base Graph construction"
  );
  db.close();
  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome });
  const baseUrl = await listen(app.server);

  try {
    const res = await fetch(`${baseUrl}/api/v2/health`);
    assert.equal(res.status, 200);
    const body = await res.json();
    assert.equal(body.database_status.base_graph.available, true);
    assert.equal(body.database_status.base_graph.dirty, true);
    assert.equal(body.database_status.base_graph.document_count, 2);
    assert.equal(body.database_status.base_graph.unmapped_document_count, 1);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("v2 health route does not wait for a blocked pipeline manager status", async () => {
  const fixture = createHttpServerFixture("vp-http-v2-", { pipeline_root: "C:\\Pipeline" });
  const app = await createApplication({
    rootDir: fixture.moduleRoot,
    appHome: fixture.appHome,
    createPipelineManagerAgentFn: () => ({
      initialize() {
        return new Promise(() => {});
      },
      status() {
        return new Promise(() => {});
      },
      close() {}
    })
  });
  const baseUrl = await listen(app.server);

  try {
    const res = await fetch(`${baseUrl}/api/v2/health`, { signal: AbortSignal.timeout(1_000) });
    assert.equal(res.status, 200);
    const body = await res.json();
    assert.equal(body.api_version, "v2");
    assert.equal(body.pipeline_manager.available, false);
    assert.equal(body.pipeline_manager.startup_pending, true);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});
