import { mkdir, readFile } from "node:fs/promises";
import path from "node:path";

import { writeTextAtomically } from "../atomic_file.js";
import { MODEL_CATALOG_STATE_FILE, buildEmptyGroup } from "./types.js";

function modelCatalogStatePath(stateDir) {
  return path.join(stateDir, MODEL_CATALOG_STATE_FILE);
}

function normalizeGroup(group, fallbackModels = []) {
  return buildEmptyGroup(
    group?.models || fallbackModels,
    group?.source || "seed",
    group?.refreshed_at || "",
    group?.provider_id || "",
    group?.base_url || ""
  );
}

function normalizeGroups(groups) {
  const seen = new Set();
  const normalized = [];
  for (const item of Array.isArray(groups) ? groups : []) {
    const group = normalizeGroup(item);
    const key = `${group.provider_id}|${group.base_url}`;
    if (seen.has(key) || !(group.models.length || group.source || group.provider_id || group.base_url)) continue;
    seen.add(key);
    normalized.push(group);
  }
  return normalized;
}

export async function loadStoredModelCatalogState(stateDir) {
  try {
    const payload = JSON.parse(await readFile(modelCatalogStatePath(stateDir), "utf8"));
    return {
      llm_shared: normalizeGroup(payload?.llm_shared),
      embeddings: normalizeGroup(payload?.embeddings),
      llm_shared_catalogs: normalizeGroups(payload?.llm_shared_catalogs),
      embeddings_catalogs: normalizeGroups(payload?.embeddings_catalogs)
    };
  } catch {
    return {
      llm_shared: buildEmptyGroup(),
      embeddings: buildEmptyGroup(),
      llm_shared_catalogs: [],
      embeddings_catalogs: []
    };
  }
}

export async function saveModelCatalogState(stateDir, state) {
  await mkdir(stateDir, { recursive: true });
  await writeTextAtomically(modelCatalogStatePath(stateDir), `${JSON.stringify(state, null, 2)}\n`);
}
