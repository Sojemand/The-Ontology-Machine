export function toCatalogModelIds(modelIds) {
  return (Array.isArray(modelIds) ? modelIds : [])
    .map((modelId) => String(modelId || "").trim())
    .filter(Boolean);
}

export function assertChatChoices(payload) {
  if (!payload?.choices?.length) {
    throw new Error("No model response received.");
  }
  return payload;
}

export function assertEmbeddingDimensions(payload) {
  const dimensions = payload?.data?.[0]?.embedding?.length;
  if (!dimensions) {
    throw new Error("No embedding dimensions received.");
  }
  return dimensions;
}

export function assertEmbeddingVectors(payload) {
  const rows = Array.isArray(payload?.data) ? payload.data : [];
  const vectors = rows.map((item) => item?.embedding).filter(Array.isArray);
  if (!vectors.length || vectors.length !== rows.length) {
    throw new Error("No embedding vectors received.");
  }
  return vectors;
}
