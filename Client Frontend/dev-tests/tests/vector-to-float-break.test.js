import assert from "node:assert/strict";
import test from "node:test";

import { toFloat32Array } from "../../server/vector.js";

test("toFloat32Array with empty Float32Array returns empty Float32Array", () => {
  const input = new Float32Array([]);
  const result = toFloat32Array(input);
  assert.equal(result.length, 0);
  assert.ok(result instanceof Float32Array);
});

test("toFloat32Array with empty Array returns empty Float32Array", () => {
  const result = toFloat32Array([]);
  assert.equal(result.length, 0);
  assert.ok(result instanceof Float32Array);
});

test("toFloat32Array with empty Buffer and 0 dimensions", () => {
  const buffer = Buffer.alloc(0);
  const result = toFloat32Array(buffer, 0);
  assert.equal(result.length, 0);
});

test("toFloat32Array with Buffer where dimensions param mismatches actual size", () => {
  const source = new Float32Array([1.0, 2.0, 3.0, 4.0]);
  const buffer = Buffer.from(source.buffer);
  const result = toFloat32Array(buffer, 2);
  assert.equal(result.length, 2);
  assert.ok(Math.abs(result[0] - 1.0) < 1e-6);
  assert.ok(Math.abs(result[1] - 2.0) < 1e-6);
});

test("toFloat32Array with Buffer and oversized dimensions throws RangeError", () => {
  const source = new Float32Array([1.0]);
  const buffer = Buffer.from(source.buffer);
  assert.throws(() => toFloat32Array(buffer, 100), RangeError);
});

test("toFloat32Array rejects null input", () => {
  assert.throws(() => toFloat32Array(null), /neither a Buffer nor an array/);
});

test("toFloat32Array rejects undefined input", () => {
  assert.throws(() => toFloat32Array(undefined), /neither a Buffer nor an array/);
});

test("toFloat32Array rejects boolean input", () => {
  assert.throws(() => toFloat32Array(true), /neither a Buffer nor an array/);
});

test("toFloat32Array with NaN values in array preserves NaN", () => {
  const result = toFloat32Array([NaN, 1.0, NaN]);
  assert.equal(result.length, 3);
  assert.ok(Number.isNaN(result[0]));
  assert.ok(Math.abs(result[1] - 1.0) < 1e-6);
  assert.ok(Number.isNaN(result[2]));
});

test("toFloat32Array with Infinity values in array", () => {
  const result = toFloat32Array([Infinity, -Infinity, 0]);
  assert.equal(result[0], Infinity);
  assert.equal(result[1], -Infinity);
  assert.equal(result[2], 0);
});

test("toFloat32Array with very large values truncates to Float32 precision", () => {
  const result = toFloat32Array([1e40, -1e40]);
  assert.equal(result[0], Infinity);
  assert.equal(result[1], -Infinity);
});

test("toFloat32Array with subnormal float values", () => {
  const result = toFloat32Array([1e-45, -1e-45]);
  assert.equal(result.length, 2);
  assert.ok(result[0] >= 0);
});
