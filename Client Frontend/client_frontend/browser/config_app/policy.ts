import type { ConfigFormPayload, ProviderCatalogShape } from "./types.ts";

export function getConfigModel(payload: ConfigFormPayload, section: "llm" | "embedding"): string {
  return section === "llm" ? payload.llm_model : payload.embedding_model;
}

export function resolveSelectableModel(models: string[], candidates: string[]): string {
  const preferred = candidates.map((value) => String(value || "").trim()).filter(Boolean);
  if (!models.length) {
    return preferred[0] || "";
  }
  for (const candidate of preferred) {
    if (models.includes(candidate)) {
      return candidate;
    }
  }
  return models[0] || "";
}

export function resolveAutoFillBaseUrl(
  provider: string,
  currentValue: string,
  defaultBaseUrls: ProviderCatalogShape["default_base_urls"]
): string | null {
  const fallback = defaultBaseUrls[provider as keyof typeof defaultBaseUrls];
  if (!fallback) {
    return null;
  }
  const knownUrls = Object.values(defaultBaseUrls);
  return !currentValue || knownUrls.includes(currentValue) ? fallback : null;
}

function findCatalogNumber(modelId: string, maps: Array<Record<string, number | null>>): number | null {
  const lower = String(modelId || "").trim().toLowerCase();
  if (!lower) {
    return null;
  }
  for (const map of maps) {
    if (map[lower]) {
      return map[lower];
    }
    for (const [key, value] of Object.entries(map)) {
      if (value && lower.startsWith(key)) {
        return value;
      }
    }
  }
  return null;
}

export function getModelPricing(
  modelId: string,
  pricingCatalog: ProviderCatalogShape["pricing"]
): { input: number; output: number } | null {
  const lower = String(modelId || "").trim().toLowerCase();
  if (!lower) {
    return null;
  }
  if (pricingCatalog[lower]) {
    return pricingCatalog[lower];
  }
  for (const [key, pricing] of Object.entries(pricingCatalog)) {
    if (lower.startsWith(key)) {
      return pricing;
    }
  }
  return null;
}

export function buildModelStatusText(source: "live" | "fallback" | "cache" | "seed", count: number, error?: string): string {
  if (source === "live") {
    return `Model list updated (${count}).`;
  }
  if (source === "cache") {
    return `Catalog cache active${error ? `: ${error}` : "."}`;
  }
  if (source === "seed") {
    return `Seed list active${error ? `: ${error}` : "."}`;
  }
  return `Fallback list active${error ? `: ${error}` : "."}`;
}

export function estimateChatCost(
  historyBudget: number,
  toolBudget: number,
  pricing: { input: number; output: number }
): number {
  const systemTokens = 1400;
  const avgExchangeTokens = 500;
  const avgOutputPerTurn = 300;
  const turns = Math.floor(historyBudget / avgExchangeTokens);
  const totalInput =
    turns * systemTokens +
    (avgExchangeTokens * turns * (turns + 1)) / 2 +
    turns * toolBudget;
  const totalOutput = turns * avgOutputPerTurn;
  return (totalInput * pricing.input + totalOutput * pricing.output) / 1_000_000;
}

export function buildContextHint(
  limit: number,
  modelId: string,
  liveContextLimits: Record<string, number | null>,
  catalog: ProviderCatalogShape
): string {
  const historyBudget = Math.min(Math.floor(limit * 0.4), 60_000);
  const toolBudget = Math.max(1500, Math.min(Math.floor(limit * 0.05), 8_000));
  const systemOverhead = 1300;
  const usableHistory = Math.max(0, historyBudget - systemOverhead);
  const approxTurns = Math.floor(usableHistory / 450);
  const parts = [`~${approxTurns} question-answer history turns`];
  const pricing = getModelPricing(modelId, catalog.pricing);
  if (pricing) {
    const cost = estimateChatCost(historyBudget, toolBudget, pricing);
    parts.push(`~$${cost < 1 ? cost.toFixed(2) : Math.round(cost)} bis Cap`);
  }
  const modelMax = findCatalogNumber(modelId, [liveContextLimits, catalog.context_limits]);
  if (modelMax && limit > modelMax) {
    parts.push(`Warning: model limit is ${modelMax.toLocaleString("en-US")}`);
  }
  return parts.join(" | ");
}
