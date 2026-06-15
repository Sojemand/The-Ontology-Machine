import { maskSecret } from "./policy.js";
import { isEncryptedValue, isLegacyEncryptedValue, validateRootDir } from "./validation.js";
import {
  decryptSecretWorkflow,
  encryptSecretWorkflow,
  migrateEncryptedSecretWorkflow,
  signScopedValueWorkflow,
  verifySignedValueWorkflow
} from "./workflow.js";

export { isEncryptedValue, isLegacyEncryptedValue, maskSecret };

export function encryptSecret(rootDir, plainText) {
  return encryptSecretWorkflow(validateRootDir(rootDir), plainText);
}

export function decryptSecret(rootDir, value) {
  return decryptSecretWorkflow(validateRootDir(rootDir), value);
}

export function migrateEncryptedSecret(rootDir, value) {
  return migrateEncryptedSecretWorkflow(validateRootDir(rootDir), value);
}

export function signScopedValue(rootDir, scope, plainValue) {
  return signScopedValueWorkflow(validateRootDir(rootDir), scope, plainValue);
}

export function verifySignedValue(rootDir, scope, signedValue) {
  return verifySignedValueWorkflow(validateRootDir(rootDir), scope, signedValue);
}
