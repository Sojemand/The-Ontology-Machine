import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";
import test from "node:test";

const PROJECT_ROOT = fileURLToPath(new URL("../../", import.meta.url));

function readProjectFile(relativePath) {
  return readFileSync(path.join(PROJECT_ROOT, relativePath), "utf8");
}

test("canonical dev-test runner executes the deploy-installer PowerShell round-trip", () => {
  const runner = readProjectFile("dev-tests/run-tests.bat");
  assert.match(runner, /deploy-installer-roundtrip\.ps1/);
  assert.match(runner, /runtime\\powershell\\pwsh\.exe/);
  assert.match(runner, /runtime\\powershell\\powershell\.exe/);
  assert.match(runner, /runtime\\powershell\\pwsh\\pwsh\.exe/);
});

test("deploy and installer immutable payloads do not include module-root data", () => {
  for (const script of ["tools/deploy.ps1", "tools/installer.ps1"]) {
    const content = readProjectFile(script);
    const immutableDirsLine = content.match(/\$immutableDirs\s*=\s*@\(([^)]*)\)/)?.[1] || "";
    assert.doesNotMatch(immutableDirsLine, /"data"/i, `${script} must not package module-root data`);
  }
});

test("runtime launcher keeps stale-port cleanup on bundled PowerShell only", () => {
  const launcher = readProjectFile("runtime/launch-server.bat");
  assert.match(launcher, /runtime\\powershell\\pwsh\.exe/);
  assert.match(launcher, /runtime\\powershell\\powershell\.exe/);
  assert.match(launcher, /runtime\\powershell\\pwsh\\pwsh\.exe/);
  assert.doesNotMatch(launcher, /set\s+"POWERSHELL_BIN=powershell\.exe"/i);
  assert.match(launcher, /Bundled PowerShell runtime fehlt/);
});

test("port cleaner direct CLI resolves bundled PowerShell instead of host fallback", () => {
  const cli = readProjectFile("client_frontend/port_cleaner/cli.js");
  assert.match(cli, /resolveBundledRuntime\("powershell"\)/);
  assert.match(cli, /queryProcessDetails\(\[pid\],\s*\{\s*powershellBin\s*\}\)/);
  assert.match(cli, /queryProcessInfoByPid:\s*async\s*\(pid\)/);
  assert.doesNotMatch(cli, /powershell\.exe"\s*\}/i);
});
