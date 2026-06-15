import assert from "node:assert/strict";
import test from "node:test";

import {
  cosineSimilarity,
  decodeVectorBase64,
  encodeVectorBase64,
  toFloat32Array
} from "../../server/vector.js";

// ---------------------------------------------------------------------------
// toFloat32Array
// ---------------------------------------------------------------------------

test("toFloat32Array returns input unchanged when already Float32Array", () => {
  const input = new Float32Array([1, 2, 3]);
  const result = toFloat32Array(input);
  assert.equal(result, input);
});

test("toFloat32Array converts plain Array to Float32Array", () => {
  const result = toFloat32Array([1.5, 2.5, 3.5]);
  assert.ok(result instanceof Float32Array);
  assert.equal(result.length, 3);
  assert.ok(Math.abs(result[0] - 1.5) < 1e-6);
});

test("toFloat32Array converts Buffer using explicit dimensions parameter", () => {
  const source = new Float32Array([1.0, 2.0, 3.0]);
  const buffer = Buffer.from(source.buffer);
  const result = toFloat32Array(buffer, 3);
  assert.ok(result instanceof Float32Array);
  assert.equal(result.length, 3);
  assert.ok(Math.abs(result[0] - 1.0) < 1e-6);
  assert.ok(Math.abs(result[2] - 3.0) < 1e-6);
});

test("toFloat32Array infers dimensions from Buffer byteLength when omitted", () => {
  const source = new Float32Array([4.0, 5.0]);
  const buffer = Buffer.from(source.buffer);
  const result = toFloat32Array(buffer);
  assert.equal(result.length, 2);
  assert.ok(Math.abs(result[1] - 5.0) < 1e-6);
});

test("toFloat32Array throws for non-Buffer non-Array input", () => {
  assert.throws(() => toFloat32Array("hello"), /neither a Buffer nor an array/);
  assert.throws(() => toFloat32Array(42), /neither a Buffer nor an array/);
  assert.throws(() => toFloat32Array({}), /neither a Buffer nor an array/);
});

// ---------------------------------------------------------------------------
// cosineSimilarity
// ---------------------------------------------------------------------------

test("cosineSimilarity returns 1.0 for identical unit vectors", () => {
  const vec = new Float32Array([0, 0, 1]);
  assert.ok(Math.abs(cosineSimilarity(vec, vec) - 1.0) < 1e-5);
});

test("cosineSimilarity returns -1.0 for opposite vectors", () => {
  const a = new Float32Array([1, 0]);
  const b = new Float32Array([-1, 0]);
  assert.ok(Math.abs(cosineSimilarity(a, b) - (-1.0)) < 1e-5);
});

test("cosineSimilarity returns ~0 for orthogonal vectors", () => {
  const a = new Float32Array([1, 0, 0]);
  const b = new Float32Array([0, 1, 0]);
  assert.ok(Math.abs(cosineSimilarity(a, b)) < 1e-5);
});

test("cosineSimilarity returns 0 for zero vector -- no NaN", () => {
  const zero = new Float32Array([0, 0, 0]);
  const other = new Float32Array([1, 2, 3]);
  const result = cosineSimilarity(zero, other);
  assert.equal(result, 0);
  assert.ok(!Number.isNaN(result), "must not return NaN");
});

test("cosineSimilarity returns 0 when both vectors are zero", () => {
  const zero = new Float32Array([0, 0]);
  const result = cosineSimilarity(zero, zero);
  assert.equal(result, 0);
  assert.ok(!Number.isNaN(result), "must not return NaN for both-zero case");
});

test("cosineSimilarity throws for mismatched dimensions", () => {
  const a = new Float32Array([1, 2]);
  const b = new Float32Array([1, 2, 3]);
  assert.throws(() => cosineSimilarity(a, b), /different dimensions/);
});

// ---------------------------------------------------------------------------
// encodeVectorBase64 / decodeVectorBase64 roundtrip
// ---------------------------------------------------------------------------

test("encodeVectorBase64 and decodeVectorBase64 roundtrip preserves values", () => {
  const original = new Float32Array([0.1, -0.5, 3.14, 0, -999.99]);
  const encoded = encodeVectorBase64(original);
  assert.equal(typeof encoded, "string");
  const decoded = decodeVectorBase64(encoded, original.length);
  assert.equal(decoded.length, original.length);
  for (let i = 0; i < original.length; i++) {
    assert.ok(Math.abs(decoded[i] - original[i]) < 1e-5, `index ${i} mismatch`);
  }
});

test("decodeVectorBase64 works with explicit dimensions parameter", () => {
  const original = new Float32Array([42.0, -1.0]);
  const encoded = encodeVectorBase64(original);
  const decoded = decodeVectorBase64(encoded, 2);
  assert.equal(decoded.length, 2);
  assert.ok(Math.abs(decoded[0] - 42.0) < 1e-5);
});

