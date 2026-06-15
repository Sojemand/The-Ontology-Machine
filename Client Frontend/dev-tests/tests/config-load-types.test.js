import assert from "node:assert/strict";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { DEFAULT_CONFIG, loadConfig } from "../../server/config.js";

test("loadConfig normalizes invalid field types back to safe defaults", async () => {
  const tempDir = mkdtempSync(path.join(os.tmpdir(), "vp-config-types-"));
  try {
    writeFileSync(
      path.join(tempDir, "config.json"),
      JSON.stringify({
        customer_name: { bad: true },
        llm_provider: true,
        llm_base_url: 123,
        llm_model: false,
        llm_api_key: { secret: "x" },
        embedding_provider: ["mammouth"],
        embedding_base_url: { nope: true },
        embedding_model: 42,
        embedding_api_key: ["secret"],
        sql_database_path: { invalid: true },
        port: "not-a-port",
        theme: null,
        admin_secret: { secret: "admin" },
        context_limit: "invalid"
      }),
      "utf8"
    );

    const config = await loadConfig(tempDir);

    assert.equal(config.customer_name, DEFAULT_CONFIG.customer_name);
    assert.equal(config.llm_provider, DEFAULT_CONFIG.llm_provider);
    assert.equal(config.llm_base_url, DEFAULT_CONFIG.llm_base_url);
    assert.equal(config.llm_model, DEFAULT_CONFIG.llm_model);
    assert.equal(config.llm_api_key, "");
    assert.equal(config.embedding_provider, DEFAULT_CONFIG.embedding_provider);
    assert.equal(config.embedding_base_url, DEFAULT_CONFIG.embedding_base_url);
    assert.equal(config.embedding_model, DEFAULT_CONFIG.embedding_model);
    assert.equal(config.embedding_api_key, "");
    assert.equal(config.sql_database_path, DEFAULT_CONFIG.sql_database_path);
    assert.equal(config.port, DEFAULT_CONFIG.port);
    assert.equal(config.theme, DEFAULT_CONFIG.theme);
    assert.equal(config.admin_secret, "");
    assert.equal(config.context_limit, DEFAULT_CONFIG.context_limit);
  } finally {
    rmSync(tempDir, { recursive: true, force: true });
  }
});

test("loadConfig keeps unknown fields while normalizing known ones", async () => {
  const tempDir = mkdtempSync(path.join(os.tmpdir(), "vp-config-types-"));
  try {
    writeFileSync(
      path.join(tempDir, "config.json"),
      JSON.stringify({
        customer_name: "Kunde",
        custom_flag: { keep: true },
        nested_unknown: ["x", "y"]
      }),
      "utf8"
    );

    const config = await loadConfig(tempDir);

    assert.equal(config.customer_name, "Kunde");
    assert.deepEqual(config.custom_flag, { keep: true });
    assert.deepEqual(config.nested_unknown, ["x", "y"]);
  } finally {
    rmSync(tempDir, { recursive: true, force: true });
  }
});

test("loadConfig accepts UTF-8 BOM config files", async () => {
  const tempDir = mkdtempSync(path.join(os.tmpdir(), "vp-config-types-"));
  try {
    writeFileSync(
      path.join(tempDir, "config.json"),
      `\uFEFF${JSON.stringify({ customer_name: "BOM Kunde", sql_database_path: "C:\\Corpus\\corpus.db" })}`,
      "utf8"
    );

    const config = await loadConfig(tempDir);

    assert.equal(config.customer_name, "BOM Kunde");
    assert.equal(config.sql_database_path, "C:\\Corpus\\corpus.db");
  } finally {
    rmSync(tempDir, { recursive: true, force: true });
  }
});
