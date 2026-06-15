export function toFloat32Array(value, dimensions) {
  if (value instanceof Float32Array) {
    return value;
  }

  if (Array.isArray(value)) {
    return Float32Array.from(value);
  }

  if (!Buffer.isBuffer(value) && !(value instanceof Uint8Array)) {
    throw new Error("Vector is neither a Buffer nor an array.");
  }

  const expectedDimensions = dimensions || value.byteLength / 4;
  return new Float32Array(value.buffer, value.byteOffset, expectedDimensions);
}

export function encodeVectorBase64(vector) {
  const array = vector instanceof Float32Array ? vector : Float32Array.from(vector);
  return Buffer.from(array.buffer, array.byteOffset, array.byteLength).toString("base64");
}

export function decodeVectorBase64(base64, dimensions) {
  const buffer = Buffer.from(base64, "base64");
  return toFloat32Array(buffer, dimensions);
}

export function cosineSimilarity(left, right) {
  if (left.length !== right.length) {
    throw new Error("Vectors have different dimensions.");
  }

  let dot = 0;
  let leftNorm = 0;
  let rightNorm = 0;

  for (let index = 0; index < left.length; index += 1) {
    const a = left[index];
    const b = right[index];
    dot += a * b;
    leftNorm += a * a;
    rightNorm += b * b;
  }

  if (!leftNorm || !rightNorm) {
    return 0;
  }

  return dot / (Math.sqrt(leftNorm) * Math.sqrt(rightNorm));
}
