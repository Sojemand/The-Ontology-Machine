import assert from "node:assert/strict";
import test from "node:test";

import { decodeVectorBase64, encodeVectorBase64 } from "../../server/vector.js";

test("encodeVectorBase64 with empty Float32Array returns empty string or valid base64", () => {
  const encoded = encodeVectorBase64(new Float32Array([]));
  assert.equal(typeof encoded, "string");
  assert.equal(encoded, "");
});

test("encodeVectorBase64 with regular array (not Float32Array)", () => {
  const encoded = encodeVectorBase64([1.0, 2.0, 3.0]);
  const decoded = decodeVectorBase64(encoded, 3);
  assert.ok(Math.abs(decoded[0] - 1.0) < 1e-5);
  assert.ok(Math.abs(decoded[2] - 3.0) < 1e-5);
});

test("encodeVectorBase64 with NaN values roundtrips correctly", () => {
  const original = new Float32Array([NaN, 0, NaN]);
  const encoded = encodeVectorBase64(original);
  const decoded = decodeVectorBase64(encoded, 3);
  assert.ok(Number.isNaN(decoded[0]));
  assert.equal(decoded[1], 0);
  assert.ok(Number.isNaN(decoded[2]));
});

test("encodeVectorBase64 with Infinity roundtrips correctly", () => {
  const original = new Float32Array([Infinity, -Infinity]);
  const encoded = encodeVectorBase64(original);
  const decoded = decodeVectorBase64(encoded, 2);
  assert.equal(decoded[0], Infinity);
  assert.equal(decoded[1], -Infinity);
});

test("decodeVectorBase64 with invalid base64 string", () => {
  const decoded = decodeVectorBase64("!!not-valid-base64!!", 0);
  assert.ok(decoded instanceof Float32Array);
});

test("decodeVectorBase64 with dimensions=0 returns empty Float32Array", () => {
  const decoded = decodeVectorBase64("", 0);
  assert.equal(decoded.length, 0);
});

test("decodeVectorBase64 roundtrip with 10000-dimension vector", () => {
  const dims = 10000;
  const original = new Float32Array(dims);
  for (let index = 0; index < dims; index += 1) {
    original[index] = (index - 5000) * 0.001;
  }
  const encoded = encodeVectorBase64(original);
  const decoded = decodeVectorBase64(encoded, dims);
  assert.equal(decoded.length, dims);
  for (let index = 0; index < dims; index += 1000) {
    assert.ok(Math.abs(decoded[index] - original[index]) < 1e-5, `mismatch at index ${index}`);
  }
});
