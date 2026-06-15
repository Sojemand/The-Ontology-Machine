import assert from "node:assert/strict";
import test from "node:test";

import { PROVIDER_REQUEST_TIMEOUT_MS } from "../../client_frontend/provider/adapter_core.js";

test("provider requests allow long-running agent work", () => {
  assert.equal(PROVIDER_REQUEST_TIMEOUT_MS, 300_000);
});
