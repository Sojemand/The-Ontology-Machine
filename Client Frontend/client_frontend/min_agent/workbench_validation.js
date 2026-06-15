import {
  POWERSHELL_ALLOWED_COMMANDS,
  POWERSHELL_ALLOWED_ENV_VARS,
  POWERSHELL_LANGUAGE_TOKENS
} from "./types.js";
import {
  buildWorkbenchScope,
  createWorkbenchPolicyError,
  looksLikeInspectablePathLiteral,
  resolveWorkbenchPathLiteral
} from "./workbench_scope.js";

function extractPowerShellStringLiterals(code) {
  return Array.from(String(code || "").matchAll(/'([^']*)'|"([^"]*)"/g), (match) => match[1] ?? match[2] ?? "");
}

function extractPythonStringLiterals(code) {
  const regex = /(?:\b(?:r|u|b|br|rb|f|fr|rf))?\s*("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')/gi;
  return Array.from(String(code || "").matchAll(regex), (match) =>
    match[1]
      .slice(1, -1)
      .replace(/\\\\/g, "\\")
      .replace(/\\'/g, "'")
      .replace(/\\"/g, "\"")
      .replace(/\\r/g, "\r")
      .replace(/\\n/g, "\n")
      .replace(/\\t/g, "\t")
      .replace(/\\u([0-9a-fA-F]{4})/g, (_whole, hex) => String.fromCharCode(Number.parseInt(hex, 16)))
  );
}

function stripPowerShellStringsAndComments(code) {
  let output = "";
  let mode = "normal";
  for (let index = 0; index < code.length; index += 1) {
    const current = code[index];
    const next = code[index + 1];
    if (mode === "normal") {
      mode = current === "#" ? "comment" : current === "'" ? "single" : current === "\"" ? "double" : "normal";
      output += mode === "normal" ? current : " ";
      continue;
    }
    if (mode === "comment") {
      output += current === "\r" || current === "\n" ? (mode = "normal", current) : " ";
      continue;
    }
    if (mode === "single") {
      if (current === "'" && next === "'") {
        output += "  ";
        index += 1;
        continue;
      }
      if (current === "'") mode = "normal";
      output += " ";
      continue;
    }
    if (current === "`" && index + 1 < code.length) {
      output += "  ";
      index += 1;
      continue;
    }
    if (current === "\"") mode = "normal";
    output += " ";
  }
  return output;
}

function containsPowerShellDynamicInvocation(code) {
  const stripped = stripPowerShellStringsAndComments(String(code || ""));
  return /(^|[\s;({|])&(?=\s*(?:\(|\$|[A-Za-z_]))/.test(stripped) || /(^|[\s;({|])\.(?=\s*(?:[\\/A-Za-z_$]))/.test(stripped) || stripped.includes("&&");
}

function extractPowerShellCommands(code) {
  const commands = new Set();
  for (const match of stripPowerShellStringsAndComments(String(code || "")).matchAll(/(?:^|[|;{}()\r\n=])\s*([A-Za-z_][A-Za-z0-9-]*)\b/g)) {
    if (!POWERSHELL_LANGUAGE_TOKENS.has(match[1].toLowerCase())) commands.add(match[1]);
  }
  return [...commands];
}

function validateWorkbenchPathLiterals(code, scope, runtime) {
  const literals = runtime === "python" ? extractPythonStringLiterals(code) : extractPowerShellStringLiterals(code);
  for (const literal of literals) {
    if (looksLikeInspectablePathLiteral(literal)) resolveWorkbenchPathLiteral(String(literal || "").trim(), scope, runtime);
  }
}

export function assertReadOnlyWorkbench(runtime, code, options = {}) {
  const normalizedRuntime = String(runtime || "").trim().toLowerCase();
  const normalizedCode = String(code || "").trim();
  if (!normalizedCode) throw new Error("workbench braucht Code.");
  if (!["python", "powershell"].includes(normalizedRuntime)) throw new Error("workbench runtime must be python or powershell.");
  const scope = buildWorkbenchScope(options);
  const forbiddenPatterns = normalizedRuntime === "python"
    ? [/\bsubprocess\b/i, /\brequests\b/i, /\burllib\b/i, /\bsocket\b/i, /\bctypes\b/i, /\bos\.(remove|unlink|rmdir|rename|replace)\b/i, /\bshutil\./i, /open\s*\([^)]*,\s*["'](?:w|a|x|wb|ab|w\+|a\+|x\+|rb\+|wb\+|ab\+)["']/i, /\.open\s*\(\s*["'](?:w|a|x|wb|ab|w\+|a\+|x\+|rb\+|wb\+|ab\+)["']/i, /["']write["']\s*\+\s*["']_(?:text|bytes)["']/i, /getattr\s*\([^)]*,[^)]*write[^)]*_(?:text|bytes)[^)]*\)/i, /\.write_text\s*\(/i, /\.write_bytes\s*\(/i, /\.write\s*\(/i]
    : [/\b(Add-Content|Add-Type|Clear-Content|Copy-Item|Export-Csv|Invoke-Command|Invoke-Expression|Invoke-Item|Move-Item|New-Item|New-Object|New-PSDrive|Remove-Item|Rename-Item|Set-Content|Set-Item|Set-Location|Start-Job|Start-Process|Start-ThreadJob)\b/i, /\b(Invoke-RestMethod|Invoke-WebRequest|Resolve-DnsName|Test-NetConnection|curl|wget)\b/i, /(^|\s)(cmd(?:\.exe)?|powershell(?:\.exe)?|pwsh(?:\.exe)?|python(?:\.exe)?)\b/i, /\[[^\]]+\]::/i, /(^|\s)(del|rm|mv|cp)\s/i, />>?|2>/i, /\b(?:iex)\b/i];
  if (forbiddenPatterns.some((pattern) => pattern.test(normalizedCode))) {
    throw createWorkbenchPolicyError("Workbench is read-only. The provided code contains disallowed write, network, or process operations.");
  }
  if (normalizedRuntime === "python") {
    validateWorkbenchPathLiterals(normalizedCode, scope, normalizedRuntime);
    return { runtime: normalizedRuntime, code: normalizedCode, scope };
  }
  if (/(^|[\\/])\.\.(?:[\\/]|$)/.test(normalizedCode)) {
    throw createWorkbenchPolicyError("PowerShell workbench blocks path traversal outside the corpus scope.");
  }
  if (containsPowerShellDynamicInvocation(normalizedCode)) {
    throw createWorkbenchPolicyError("PowerShell workbench blocks dynamic command execution via call operator or dot-sourcing.");
  }
  for (const reference of String(normalizedCode).match(/\$env:([A-Za-z_][A-Za-z0-9_]*)/g) || []) {
    const envVar = reference.slice("$env:".length);
    if (!POWERSHELL_ALLOWED_ENV_VARS.has(envVar)) {
      throw createWorkbenchPolicyError(`PowerShell workbench only allows the environment variables ${[...POWERSHELL_ALLOWED_ENV_VARS].join(", ")}.`);
    }
  }
  const disallowedCommands = extractPowerShellCommands(normalizedCode).filter((commandName) => !POWERSHELL_ALLOWED_COMMANDS.has(commandName));
  if (disallowedCommands.length) {
    throw createWorkbenchPolicyError(`PowerShell workbench allows only read-only inspection cmdlets. Not allowed: ${disallowedCommands.join(", ")}.`);
  }
  validateWorkbenchPathLiterals(normalizedCode, scope, normalizedRuntime);
  return { runtime: normalizedRuntime, code: normalizedCode, scope };
}
