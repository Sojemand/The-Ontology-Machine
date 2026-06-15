import assert from "node:assert/strict";
import test from "node:test";

import { assertReadOnlyWorkbench } from "../../server/min_agent.js";
import { cleanupWorkbenchFixture, createWorkbenchFixture } from "./min-agent-workbench-test-fixtures.js";

test("powershell workbench allows read-only corpus-adjacent paths", () => {
  const fixture = createWorkbenchFixture();
  try {
    const result = assertReadOnlyWorkbench("powershell", "Get-Content (Join-Path $env:MIN_AGENT_DATA_DIR 'notes.txt') | ConvertTo-Json", fixture);
    assert.equal(result.runtime, "powershell");
    const policyResult = assertReadOnlyWorkbench("powershell", "Get-Content 'frontend_policy.json' | ConvertTo-Json", fixture);
    assert.equal(policyResult.runtime, "powershell");
  } finally {
    cleanupWorkbenchFixture(fixture.rootDir);
  }
});

test("powershell workbench blocks writes, network paths, outside paths and process launch", () => {
  const fixture = createWorkbenchFixture();
  try {
    assert.throws(() => assertReadOnlyWorkbench("powershell", "Set-Content (Join-Path $env:MIN_AGENT_DATA_DIR 'notes.txt') 'hack'", fixture), /read-only/i);
    assert.throws(() => assertReadOnlyWorkbench("powershell", "Get-Content '\\\\server\\share\\secret.txt'", fixture), /network|UNC/i);
    assert.throws(() => assertReadOnlyWorkbench("powershell", "Get-Content '..\\secret.txt'", fixture), /Traversal|active corpus|Config|soul/i);
    assert.throws(() => assertReadOnlyWorkbench("powershell", "Start-Process powershell.exe", fixture), /process|read-only/i);
    assert.throws(() => assertReadOnlyWorkbench("powershell", "Get-Content 'C:\\Windows\\win.ini'", fixture), /active corpus|Config|soul/i);
    assert.throws(() => assertReadOnlyWorkbench("powershell", "ni (Join-Path $env:MIN_AGENT_DATA_DIR 'notes.txt') -ItemType File", fixture), /Not allowed|read-only/i);
    assert.throws(() => assertReadOnlyWorkbench("powershell", "md (Join-Path $env:MIN_AGENT_DATA_DIR 'newdir')", fixture), /Not allowed|read-only/i);
    assert.throws(() => assertReadOnlyWorkbench("powershell", "$item = ni (Join-Path $env:MIN_AGENT_DATA_DIR 'notes.txt') -ItemType File", fixture), /Not allowed|read-only/i);
    assert.throws(() => assertReadOnlyWorkbench("powershell", "&('Start'+'-Process') 'calc.exe'", fixture), /dynamic command execution|read-only/i);
    assert.throws(() => assertReadOnlyWorkbench("powershell", "&('Invoke'+'-RestMethod') 'https://example.com'", fixture), /dynamic command execution|read-only/i);
    assert.throws(() => assertReadOnlyWorkbench("powershell", "&('New'+'-Item') (Join-Path $env:MIN_AGENT_DATA_DIR 'notes.txt') -ItemType File", fixture), /dynamic command execution|read-only/i);
  } finally {
    cleanupWorkbenchFixture(fixture.rootDir);
  }
});

test("python workbench blocks filesystem and network writes", () => {
  const fixture = createWorkbenchFixture();
  try {
    assert.throws(() => assertReadOnlyWorkbench("python", "from pathlib import Path\nPath('x.txt').write_text('hack')", fixture), /read-only/i);
    assert.throws(() => assertReadOnlyWorkbench("python", "import urllib.request\nurllib.request.urlopen('https://example.com')", fixture), /read-only/i);
    assert.throws(() => assertReadOnlyWorkbench("python", "import subprocess\nsubprocess.run(['cmd'])", fixture), /read-only/i);
    assert.throws(() => assertReadOnlyWorkbench("python", "from pathlib import Path\nprint(Path('.salt').read_text())", fixture), /active corpus|Config|soul/i);
    assert.throws(() => assertReadOnlyWorkbench("python", "print(open('../secret.txt').read())", fixture), /active corpus|Config|soul/i);
    assert.throws(() => assertReadOnlyWorkbench("python", "import socket\nsocket.create_connection(('example.com', 443))", fixture), /read-only/i);
    assert.throws(
      () => assertReadOnlyWorkbench("python", "from pathlib import Path\nimport os\nwriter = getattr(Path(os.environ['MIN_AGENT_DATA_DIR']) / 'notes.txt', 'write' + '_text')\nwriter('hack')", fixture),
      /read-only/i
    );
  } finally {
    cleanupWorkbenchFixture(fixture.rootDir);
  }
});
