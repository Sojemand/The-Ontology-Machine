import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { createApplication } from "../../server/index.js";
import { listen } from "./server-fixtures.js";

function removeTree(targetPath) {
  rmSync(targetPath, { recursive: true, force: true, maxRetries: 5, retryDelay: 100 });
}

function createInstalledRootFixture() {
  const installRoot = mkdtempSync(path.join(os.tmpdir(), "vp-installed-root-"));
  const appHome = mkdtempSync(path.join(os.tmpdir(), "vp-installed-home-"));
  const moduleRoot = path.join(installRoot, "Client Frontend");
  mkdirSync(path.join(moduleRoot, "app"), { recursive: true });
  mkdirSync(path.join(moduleRoot, "assistant"), { recursive: true });
  mkdirSync(path.join(installRoot, "07 - MCP Server"), { recursive: true });
  mkdirSync(path.join(installRoot, "08 - Semantic Control Kernel"), { recursive: true });
  const demoDbPath = path.join(installRoot, "SampleDB", "Consciousness Travel - Default Demo", "Corpus", "corpus.db");
  mkdirSync(path.dirname(demoDbPath), { recursive: true });
  writeFileSync(demoDbPath, "demo-db", "utf8");
  return { installRoot, appHome, moduleRoot, demoDbPath };
}

function createStubAgent() {
  return {
    async initialize() {
      return true;
    },
    async status() {
      return { available: true };
    },
    countDocuments() {
      return 0;
    },
    databaseStatus() {
      return {
        base_graph: { available: false },
        ontology_lenses: { available: false, count: 0 }
      };
    },
    close() {}
  };
}

async function createApplicationWithStubAgents(options) {
  return await createApplication({
    ...options,
    createMinimalAgentFn: () => createStubAgent(),
    createOntologyAgentFn: () => createStubAgent(),
    createPipelineManagerAgentFn: options.createPipelineManagerAgentFn || (() => createStubAgent())
  });
}

test("application startup seeds the installed pipeline root and bundled demo DB into app-home config", async () => {
  const { installRoot, appHome, moduleRoot, demoDbPath } = createInstalledRootFixture();
  const capturedRoots = [];
  const app = await createApplicationWithStubAgents({
    rootDir: moduleRoot,
    appHome,
    createPipelineManagerAgentFn: ({ pipelineRoot }) => {
      capturedRoots.push(pipelineRoot);
      return {
        async initialize() {
          return true;
        },
        async status() {
          return { available: true, pipeline_root: pipelineRoot, tool_count: 0 };
        },
        close() {}
      };
    }
  });
  await listen(app.server);

  try {
    assert.equal(capturedRoots[0], installRoot);
    const savedConfig = JSON.parse(readFileSync(path.join(appHome, "config", "config.json"), "utf8"));
    assert.equal(savedConfig.pipeline_root, installRoot);
    assert.equal(savedConfig.sql_database_path, demoDbPath);
  } finally {
    await app.close();
    removeTree(installRoot);
    removeTree(appHome);
  }
});

test("application startup rebinds stale external SampleDB paths to the installed demo DB", async () => {
  const { installRoot, appHome, moduleRoot, demoDbPath } = createInstalledRootFixture();
  const staleSampleDbPath = path.join(os.tmpdir(), "SampleDB", "Sample DB - Old", "Final_Database", "Corpus", "corpus.db");
  mkdirSync(path.join(appHome, "config"), { recursive: true });
  writeFileSync(
    path.join(appHome, "config", "config.json"),
    JSON.stringify({
      customer_name: "Test Customer",
      sql_database_path: staleSampleDbPath,
      pipeline_root: "..",
      llm_provider: "openai",
      llm_base_url: "https://api.openai.com/v1",
      llm_model: "gpt-5.4",
      llm_api_key: "",
      embedding_provider: "openai",
      embedding_base_url: "https://api.openai.com/v1",
      embedding_model: "text-embedding-3-small",
      embedding_api_key: "",
      port: 3000,
      theme: "dark",
      admin_secret: "",
      context_limit: 127096
    }),
    "utf8"
  );
  const app = await createApplicationWithStubAgents({ rootDir: moduleRoot, appHome });
  await listen(app.server);

  try {
    const savedConfig = JSON.parse(readFileSync(path.join(appHome, "config", "config.json"), "utf8"));
    assert.equal(savedConfig.pipeline_root, installRoot);
    assert.equal(savedConfig.sql_database_path, demoDbPath);
  } finally {
    await app.close();
    removeTree(installRoot);
    removeTree(appHome);
  }
});

test("application startup does not let a workspace root overwrite another installed demo DB path", async () => {
  const installed = createInstalledRootFixture();
  const workspace = createInstalledRootFixture();
  const appHome = installed.appHome;
  mkdirSync(path.join(appHome, "config"), { recursive: true });
  writeFileSync(
    path.join(appHome, "config", "config.json"),
    JSON.stringify({
      customer_name: "Test Customer",
      sql_database_path: installed.demoDbPath,
      pipeline_root: installed.installRoot,
      llm_provider: "openai",
      llm_base_url: "https://api.openai.com/v1",
      llm_model: "gpt-5.4",
      llm_api_key: "",
      embedding_provider: "openai",
      embedding_base_url: "https://api.openai.com/v1",
      embedding_model: "text-embedding-3-small",
      embedding_api_key: "",
      port: 3000,
      theme: "dark",
      admin_secret: "",
      context_limit: 127096
    }),
    "utf8"
  );
  const app = await createApplicationWithStubAgents({ rootDir: workspace.moduleRoot, appHome });
  await listen(app.server);

  try {
    const savedConfig = JSON.parse(readFileSync(path.join(appHome, "config", "config.json"), "utf8"));
    assert.equal(savedConfig.pipeline_root, installed.installRoot);
    assert.equal(savedConfig.sql_database_path, installed.demoDbPath);
  } finally {
    await app.close();
    removeTree(installed.installRoot);
    removeTree(workspace.installRoot);
    removeTree(appHome);
    removeTree(workspace.appHome);
  }
});
