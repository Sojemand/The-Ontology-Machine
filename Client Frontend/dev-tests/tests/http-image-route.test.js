import assert from "node:assert/strict";
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { DatabaseSync } from "node:sqlite";
import test from "node:test";

import { createApplication } from "../../server/index.js";
import { createSimpleServerFixture } from "./http-server-fixtures.js";
import { cleanupFixture, listen } from "./server-fixtures.js";

function withFixtureDatabase(fixture, callback) {
  const database = new DatabaseSync(fixture.dbPath);
  try {
    callback(database);
  } finally {
    database.close();
  }
}

test("image route serves embedded DB page bytes before filesystem fallback", async () => {
  const fixture = createSimpleServerFixture("vp-http-image-");
  const dbBytes = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a]);
  withFixtureDatabase(fixture, (database) => {
    database.prepare("UPDATE documents SET content_hash = ? WHERE id = ?").run("sha256:aaaaaaaa", "doc-1");
    database.exec(`
      CREATE TABLE document_page_images (
        document_id TEXT NOT NULL,
        page INTEGER NOT NULL,
        content_type TEXT NOT NULL,
        image_blob BLOB NOT NULL
      );
    `);
    database.prepare(`
      INSERT INTO document_page_images (document_id, page, content_type, image_blob)
      VALUES (?, ?, ?, ?)
    `).run("doc-1", 1, "image/png", dbBytes);
  });
  const fallbackDir = path.join(fixture.dataDir, "page_images", "alpha.pdf.aaaaaaaa");
  mkdirSync(fallbackDir, { recursive: true });
  writeFileSync(path.join(fallbackDir, "page_001.png"), Buffer.from([0x00, 0x11, 0x22]));

  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome });
  const baseUrl = await listen(app.server);

  try {
    const response = await fetch(`${baseUrl}/api/image/doc-1/1`);
    const payload = Buffer.from(await response.arrayBuffer());
    assert.equal(response.status, 200);
    assert.equal(response.headers.get("content-type"), "image/png");
    assert.deepEqual([...payload], [...dbBytes]);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});

test("image route falls back to filesystem images for corpora without embedded pages", async () => {
  const fixture = createSimpleServerFixture("vp-http-image-");
  const fileBytes = Buffer.from([0xff, 0xd8, 0xff, 0xe0]);
  withFixtureDatabase(fixture, (database) => {
    database.prepare("UPDATE documents SET content_hash = ? WHERE id = ?").run("sha256:aaaaaaaa", "doc-1");
  });
  const fallbackDir = path.join(fixture.dataDir, "page_images", "alpha.pdf.aaaaaaaa");
  mkdirSync(fallbackDir, { recursive: true });
  writeFileSync(path.join(fallbackDir, "page_001.jpg"), fileBytes);

  const app = await createApplication({ rootDir: fixture.moduleRoot, appHome: fixture.appHome });
  const baseUrl = await listen(app.server);

  try {
    const response = await fetch(`${baseUrl}/api/image/doc-1/1`);
    const payload = Buffer.from(await response.arrayBuffer());
    assert.equal(response.status, 200);
    assert.equal(response.headers.get("content-type"), "image/jpeg");
    assert.deepEqual([...payload], [...fileBytes]);
  } finally {
    await app.close();
    cleanupFixture(fixture);
  }
});
