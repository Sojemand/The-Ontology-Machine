import assert from "node:assert/strict";
import test from "node:test";

import { cosineSimilarity } from "../../server/vector.js";

test("cosineSimilarity with single-element vectors", () => {
  const a = new Float32Array([3]);
  const b = new Float32Array([5]);
  const result = cosineSimilarity(a, b);
  assert.ok(Math.abs(result - 1.0) < 1e-5, "parallel vectors should have similarity 1.0");
});

test("cosineSimilarity with single-element opposite vectors", () => {
  const a = new Float32Array([3]);
  const b = new Float32Array([-5]);
  const result = cosineSimilarity(a, b);
  assert.ok(Math.abs(result + 1.0) < 1e-5);
});

test("cosineSimilarity with very large values does not return NaN", () => {
  const a = new Float32Array([1e30, 1e30]);
  const b = new Float32Array([1e30, 1e30]);
  const result = cosineSimilarity(a, b);
  assert.ok(!Number.isNaN(result) || result === 0, `got ${result}`);
});

test("cosineSimilarity with NaN in vector returns NaN (expected but documented)", () => {
  const a = new Float32Array([NaN, 1]);
  const b = new Float32Array([1, 1]);
  const result = cosineSimilarity(a, b);
  assert.ok(Number.isNaN(result) || result === 0);
});

test("cosineSimilarity with empty vectors (length 0) does not crash", () => {
  const a = new Float32Array([]);
  const b = new Float32Array([]);
  const result = cosineSimilarity(a, b);
  assert.equal(result, 0);
});

test("cosineSimilarity with high-dimensional vectors (1536 dims)", () => {
  const dims = 1536;
  const a = new Float32Array(dims);
  const b = new Float32Array(dims);
  for (let index = 0; index < dims; index += 1) {
    a[index] = Math.random() * 2 - 1;
    b[index] = a[index];
  }
  const result = cosineSimilarity(a, b);
  assert.ok(Math.abs(result - 1.0) < 1e-4, `expected ~1.0 for identical vectors, got ${result}`);
});

test("cosineSimilarity is symmetric", () => {
  const a = new Float32Array([1, 2, 3, 4, 5]);
  const b = new Float32Array([5, 4, 3, 2, 1]);
  const ab = cosineSimilarity(a, b);
  const ba = cosineSimilarity(b, a);
  assert.ok(Math.abs(ab - ba) < 1e-6, "cosine similarity should be symmetric");
});

test("cosineSimilarity with one nearly-zero vector", () => {
  const a = new Float32Array([1e-38, 1e-38, 1e-38]);
  const b = new Float32Array([1, 0, 0]);
  const result = cosineSimilarity(a, b);
  assert.ok(!Number.isNaN(result));
});
