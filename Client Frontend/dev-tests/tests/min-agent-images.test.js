import assert from "node:assert/strict";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";

import { createImageRepository } from "../../client_frontend/min_agent/image_repository.js";
import { createMinimalRepository } from "../../client_frontend/min_agent/repository.js";
import { createSourceRepository } from "../../client_frontend/min_agent/source_repository.js";
import { cleanupAgentFixture, createTempAgentFixture, insertDocument, insertDocumentPageImage } from "./min-agent-test-fixtures.js";

function trackDatabase(database, statements) {
  return {
    prepare(sql) {
      statements.push(String(sql));
      return database.prepare(sql);
    }
  };
}

test("buildSource marks viewer availability from DB metadata without reading image blobs", () => {
  const fixture = createTempAgentFixture("vp-min-agent-images-");
  fixture.database.exec(`
    CREATE TABLE document_page_images (
      document_id TEXT NOT NULL,
      page INTEGER NOT NULL,
      content_type TEXT NOT NULL,
      image_blob BLOB NOT NULL
    );
  `);
  insertDocument(fixture.database, { page_count: 0 });
  insertDocumentPageImage(fixture.database, {
    document_id: "doc-1",
    page: 2,
    content_type: "image/jpeg",
    image_blob: Buffer.from([0xff, 0xd8, 0xff])
  });

  try {
    const statements = [];
    const trackedDatabase = trackDatabase(fixture.database, statements);
    const imageRepository = createImageRepository({ database: trackedDatabase, dataDir: fixture.dataDir });
    const sourceRepository = createSourceRepository({ database: trackedDatabase, imageRepository });
    const source = sourceRepository.buildSource("doc-1");

    assert.equal(source.viewer_available, true);
    assert.equal(source.page_count, 2);
    assert.equal(statements.some((sql) => /image_blob/i.test(sql)), false);
    assert.equal(statements.some((sql) => /SELECT page FROM document_page_images/i.test(sql)), true);
  } finally {
    cleanupAgentFixture(fixture);
  }
});

test("resolveImage prefers DB bytes over filesystem fallback paths", () => {
  const fixture = createTempAgentFixture("vp-min-agent-images-");
  fixture.database.exec(`
    CREATE TABLE document_page_images (
      document_id TEXT NOT NULL,
      page INTEGER NOT NULL,
      content_type TEXT NOT NULL,
      image_blob BLOB NOT NULL
    );
  `);
  insertDocument(fixture.database, { content_hash: "sha256:aaaaaaaa" });
  const dbBytes = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d]);
  insertDocumentPageImage(fixture.database, { image_blob: dbBytes });
  const fallbackDir = path.join(fixture.dataDir, "page_images", "alpha.pdf.aaaaaaaa");
  mkdirSync(fallbackDir, { recursive: true });
  writeFileSync(path.join(fallbackDir, "page_001.png"), Buffer.from([0x00, 0x11, 0x22]));

  try {
    const imageRepository = createImageRepository({ database: fixture.database, dataDir: fixture.dataDir });
    const image = imageRepository.resolveImage("doc-1", 1);

    assert.equal(image.available, true);
    assert.equal(image.source, "db");
    assert.equal(image.contentType, "image/png");
    assert.deepEqual([...image.bytes], [...dbBytes]);
  } finally {
    cleanupAgentFixture(fixture);
  }
});

test("repository sees embedded page images added after initialization", () => {
  const fixture = createTempAgentFixture("vp-min-agent-images-");
  insertDocument(fixture.database, { page_count: 1 });
  const repository = createMinimalRepository({ dbPath: fixture.dbPath, dataDir: fixture.dataDir });
  const dbBytes = Buffer.from([0xff, 0xd8, 0xff, 0xe0]);

  try {
    fixture.database.exec(`
      CREATE TABLE document_page_images (
        document_id TEXT NOT NULL,
        page INTEGER NOT NULL,
        content_type TEXT NOT NULL,
        image_blob BLOB NOT NULL
      );
    `);
    insertDocumentPageImage(fixture.database, {
      content_type: "image/jpeg",
      image_blob: dbBytes
    });

    const source = repository.buildSource("doc-1");
    const image = repository.resolveImage("doc-1", 1);

    assert.equal(source.viewer_available, true);
    assert.equal(image.available, true);
    assert.equal(image.source, "db");
    assert.equal(image.contentType, "image/jpeg");
    assert.deepEqual([...image.bytes], [...dbBytes]);
  } finally {
    repository.close();
    cleanupAgentFixture(fixture);
  }
});

test("page-scoped source viewer resolves sibling page images across the original document", () => {
  const fixture = createTempAgentFixture("vp-min-agent-page-siblings-", `
    CREATE TABLE documents (
      id TEXT PRIMARY KEY,
      file_name TEXT NOT NULL,
      file_path TEXT NOT NULL,
      source_file_path TEXT,
      source_page INTEGER,
      source_page_count INTEGER,
      content_hash TEXT NOT NULL,
      document_type TEXT,
      page_count INTEGER DEFAULT 1
    );
    CREATE TABLE document_page_images (
      document_id TEXT NOT NULL,
      page INTEGER NOT NULL,
      content_type TEXT NOT NULL,
      image_blob BLOB NOT NULL
    );
  `);
  const insertPage = fixture.database.prepare(`
    INSERT INTO documents (
      id, file_name, file_path, source_file_path, source_page, source_page_count,
      content_hash, document_type, page_count
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);
  const sourceFile = "../../source/story.odt";
  for (const page of [1, 2, 3]) {
    const id = `story.p00${page}`;
    insertPage.run(
      id,
      "story.odt",
      `${sourceFile}::page=00${page}-of-003`,
      sourceFile,
      page,
      3,
      `sha256:page${page}`,
      "story",
      3
    );
    insertDocumentPageImage(fixture.database, {
      document_id: id,
      page,
      content_type: "image/png",
      image_blob: Buffer.from([0x89, 0x50, 0x4e, 0x47, page])
    });
  }
  fixture.database.close();
  fixture.database = null;
  const repository = createMinimalRepository({ dbPath: fixture.dbPath, dataDir: fixture.dataDir });

  try {
    const source = repository.buildSource("story.p002");
    const document = repository.getDocument("story.p002");
    const pageOne = repository.resolveImage("story.p002", 1);
    const pageTwo = repository.resolveImage("story.p002", 2);
    const pageThree = repository.resolveImage("story.p002", 3);

    assert.equal(source.page, 2);
    assert.equal(source.page_count, 3);
    assert.equal(source.viewer_available, true);
    assert.equal(source.image_url, "/api/image/story.p002/2");
    assert.deepEqual(document.pages.map((page) => [page.page, page.available]), [[1, true], [2, true], [3, true]]);
    assert.deepEqual([...pageOne.bytes], [0x89, 0x50, 0x4e, 0x47, 1]);
    assert.deepEqual([...pageTwo.bytes], [0x89, 0x50, 0x4e, 0x47, 2]);
    assert.deepEqual([...pageThree.bytes], [0x89, 0x50, 0x4e, 0x47, 3]);
  } finally {
    repository.close();
    cleanupAgentFixture(fixture);
  }
});
