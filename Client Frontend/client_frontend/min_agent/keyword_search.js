import { clipText } from "./output_policy.js";
import { promotionSqlExpressions } from "./promotion_surface.js";

const STOP_WORDS = new Set(["alle", "dokument", "dokumente", "gibt", "haben", "hat", "mit", "oder", "sind", "und", "was", "welche", "welcher", "welches", "wie", "zu", "zum", "zur"]);

const CONCEPT_EXPANSIONS = [
  {
    pattern: /chem/i,
    terms: ["chem", "chemie", "chemisch", "chemical", "ammoniak", "ammonia", "harnstoff", "urea", "nh3", "katalysator"]
  },
  {
    pattern: /steuer|tax|umsatz|mwst|ust/i,
    terms: ["steuer", "tax", "umsatzsteuer", "mwst", "ust", "vat"]
  }
];

function insertScoredResult(topResults, candidate, limit) {
  let insertAt = topResults.findIndex((entry) => candidate.score > entry.score);
  if (insertAt < 0) insertAt = topResults.length;
  topResults.splice(insertAt, 0, candidate);
  if (topResults.length > limit) topResults.pop();
}

function normalizeSearchToken(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "");
}

function uniqueTerms(values) {
  const terms = [];
  const seen = new Set();
  for (const value of values) {
    const term = normalizeSearchToken(value).replace(/^[^a-z0-9]+|[^a-z0-9]+$/g, "");
    if (term.length < 3 || STOP_WORDS.has(term) || seen.has(term)) continue;
    seen.add(term);
    terms.push(term);
  }
  return terms;
}

function expandConceptTerms(text) {
  const rawText = String(text || "");
  const terms = uniqueTerms(rawText.split(/[^\p{L}\p{N}]+/u));
  const expanded = [...terms];
  for (const expansion of CONCEPT_EXPANSIONS) {
    if (expansion.pattern.test(rawText) || terms.some((term) => expansion.pattern.test(term))) expanded.push(...expansion.terms);
  }
  return uniqueTerms(expanded);
}

function countOccurrences(text, term) {
  if (!text || !term) return 0;
  let count = 0;
  let offset = 0;
  while ((offset = text.indexOf(term, offset)) >= 0) {
    count += 1;
    offset += term.length;
  }
  return count;
}

function scoreKeywordRow(row, terms) {
  const weightedParts = [
    [row.promotion_text, 5],
    [row.content_free_text, 3],
    [row.document_type, 2],
    [row.category, 2],
    [row.subcategory, 2],
    [row.content_fields_json, 1],
    [row.content_rows_json, 1]
  ];
  let score = 0;
  const matchedTerms = new Set();
  for (const [value, weight] of weightedParts) {
    const normalized = normalizeSearchToken(value);
    if (!normalized) continue;
    for (const term of terms) {
      const occurrences = countOccurrences(normalized, term);
      if (occurrences <= 0) continue;
      score += occurrences * weight;
      matchedTerms.add(term);
    }
  }
  return { score, matchedTerms: Array.from(matchedTerms) };
}

function bestKeywordSnippet(row, terms) {
  for (const value of [row.promotion_text, row.content_free_text, row.content_fields_json]) {
    const text = String(value || "").trim();
    const normalized = normalizeSearchToken(text);
    if (text && terms.some((term) => normalized.includes(term))) return clipText(text, 400);
  }
  return clipText(row.file_name || "", 400);
}

export function createKeywordSearch({ database, keywordColumns }) {
  const promotionSql = promotionSqlExpressions(database, "d");
  return function keywordSearch(text, limit = 5) {
    const normalizedLimit = Math.min(20, Math.max(1, Number(limit) || 5));
    const terms = expandConceptTerms(text);
    if (!terms.length) return { available: true, mode: "lexical_fallback", result_count: 0, terms, results: [] };
    const topResults = [];
    const statement = database.prepare(`SELECT ${keywordColumns.map((column) => `d.${column}`).join(", ")}, ${promotionSql.title} AS promotion_title, ${promotionSql.date} AS promotion_date, ${promotionSql.text} AS promotion_text FROM documents d`);
    for (const row of statement.iterate()) {
      const scored = scoreKeywordRow(row, terms);
      if (scored.score <= 0) continue;
      insertScoredResult(topResults, { row, score: scored.score, matchedTerms: scored.matchedTerms }, normalizedLimit);
    }
    return {
      available: true,
      mode: "lexical_fallback",
      result_count: topResults.length,
      terms,
      results: topResults.map(({ row, score, matchedTerms }) => ({
        id: row.id,
        file_name: row.file_name,
        file_path: row.file_path,
        date: row.promotion_date || null,
        title: row.promotion_title || row.file_name,
        score,
        match_terms: matchedTerms,
        snippet: bestKeywordSnippet(row, terms)
      }))
    };
  };
}
