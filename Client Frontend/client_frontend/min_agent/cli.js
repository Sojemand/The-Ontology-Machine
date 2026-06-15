import path from "node:path";
import { fileURLToPath } from "node:url";

import { loadConfigState, resolveRuntimeConfig } from "../config.js";
import { createMinimalAgent } from "./workflow.js";

function parseCliArgs(argv) {
  const args = { message: "", dbPath: "", model: "", dataDir: "" };
  const parts = [...argv];
  while (parts.length) {
    const token = parts.shift();
    if (token === "--db") args.dbPath = parts.shift() || "";
    else if (token === "--data-dir") args.dataDir = parts.shift() || "";
    else if (token === "--model") args.model = parts.shift() || "";
    else if (token === "--help" || token === "-h") args.help = true;
    else args.message = [args.message, token].filter(Boolean).join(" ");
  }
  return args;
}

export async function runCli(argv = process.argv.slice(2)) {
  const cli = parseCliArgs(argv);
  if (cli.help || !cli.message) {
    console.log("Usage: node server/min_agent.js --db <path-to-corpus.db> [--data-dir <dir>] [--model <id>] \"Your question\"");
    return;
  }
  const rootDir = fileURLToPath(new URL("../../", import.meta.url));
  const { config, frontendPolicy } = await loadConfigState(rootDir);
  const runtimeConfig = resolveRuntimeConfig(rootDir, config);
  if (cli.model) runtimeConfig.llm_model = cli.model;
  const dbPath = path.resolve(cli.dbPath);
  const agent = createMinimalAgent({
    dbPath,
    dataDir: cli.dataDir ? path.resolve(cli.dataDir) : path.dirname(dbPath),
    rootDir,
    runtimeConfig,
    frontendPolicy
  });
  try {
    const result = await agent.chat({ message: cli.message });
    console.log(result.answer);
    if (!result.sources.length) return;
    console.log("\nSources:");
    result.sources.forEach((source, index) => {
      console.log(
        `${index + 1}. ${source.file_name || source.id} | ${source.date || "-"} | viewer ${source.viewer_available ? "ja" : "nein"}`
      );
    });
  } finally {
    agent.close();
  }
}
