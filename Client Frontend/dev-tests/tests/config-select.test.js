import assert from "node:assert/strict";
import test from "node:test";
import { JSDOM } from "jsdom";

import { populateModelSelect } from "../../src/config_select.ts";

test("populateModelSelect renders provider model names as inert option text", () => {
  const dom = new JSDOM('<select id="models"></select>');
  const select = dom.window.document.querySelector("#models");

  populateModelSelect(select, ["gpt-4.1", '\"><img src=x onerror="alert(1)">'], "gpt-4.1");

  assert.equal(select.options.length, 2);
  assert.equal(select.querySelector("img"), null);
  assert.equal(select.options[1].textContent, '\"><img src=x onerror="alert(1)">');
});

test("populateModelSelect deduplicates models and preserves a missing selected value", () => {
  const dom = new JSDOM('<select id="models"></select>');
  const select = dom.window.document.querySelector("#models");

  populateModelSelect(select, ["gpt-4.1", "gpt-4.1", "gpt-4o-mini"], "custom-model");

  assert.deepEqual(
    Array.from(select.options).map((option) => option.value),
    ["custom-model", "gpt-4.1", "gpt-4o-mini"]
  );
  assert.equal(select.value, "custom-model");
});

