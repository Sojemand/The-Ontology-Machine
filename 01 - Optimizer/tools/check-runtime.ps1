[CmdletBinding()]
param(
    [string]$RootDir = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Resolve-RootDir {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return (Split-Path -Parent $PSScriptRoot)
    }
    return [System.IO.Path]::GetFullPath($Value)
}

function Join-ProjectPath {
    param(
        [string]$BaseDir,
        [string]$RelativePath
    )

    return Join-Path $BaseDir ($RelativePath.Replace("/", "\"))
}

$projectRoot = Resolve-RootDir $RootDir
$manifestPath = Join-ProjectPath $projectRoot "runtime/runtime-manifest.json"

if (-not (Test-Path -LiteralPath $manifestPath)) {
    [PSCustomObject]@{
        ok = $false
        root_dir = $projectRoot
        manifest_path = $manifestPath
        error = "Runtime-Manifest fehlt."
    } | ConvertTo-Json -Depth 6
    exit 1
}

$manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
$requiredFiles = @($manifest.required_files)
$pythonCandidates = @($manifest.runtime_candidates.python)
$missingFiles = @()

foreach ($relativePath in $requiredFiles) {
    $candidate = Join-ProjectPath $projectRoot ([string]$relativePath)
    if (-not (Test-Path -LiteralPath $candidate)) {
        $missingFiles += $candidate
    }
}

$pythonPath = ""
foreach ($relativePath in $pythonCandidates) {
    $candidate = Join-ProjectPath $projectRoot ([string]$relativePath)
    if (Test-Path -LiteralPath $candidate) {
        $pythonPath = $candidate
        break
    }
}

if ([string]::IsNullOrWhiteSpace($pythonPath)) {
    $missingFiles += ($pythonCandidates | ForEach-Object { Join-ProjectPath $projectRoot ([string]$_) })
}

$payload = [ordered]@{
    ok = $false
    root_dir = $projectRoot
    manifest_path = $manifestPath
    missing_files = $missingFiles
    python = [ordered]@{
        path = $pythonPath
        version = ""
        executable = ""
        base_prefix = ""
    }
    provenance = [ordered]@{
        encodings = ""
        yaml = ""
        sys_path = @()
    }
    violations = @()
    error = ""
}

if ($missingFiles.Count -gt 0) {
    $payload.error = "Gebuendelte Runtime ist unvollstaendig."
    $payload | ConvertTo-Json -Depth 8
    exit 1
}

$probeCode = @'
from __future__ import annotations

import encodings
import json
import sys
from pathlib import Path

project_root = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(project_root))
import ingestion_layer_vision.orchestrator_contract as optimizer_contract
import ingestion_layer_file.orchestrator_contract as optimizer_file_contract

payload = {
    "version": sys.version.split()[0],
    "executable": str(Path(sys.executable).resolve()),
    "base_prefix": str(Path(sys.base_prefix).resolve()),
    "encodings": str(Path(encodings.__file__).resolve()),
    "yaml": "",
    "optimizer_contract": str(Path(optimizer_contract.__file__).resolve()),
    "optimizer_file_contract": str(Path(optimizer_file_contract.__file__).resolve()),
    "sys_path": [str(Path(entry).resolve()) if entry else "" for entry in sys.path],
}
import yaml
payload["yaml"] = str(Path(yaml.__file__).resolve())
print(json.dumps(payload))
'@

$probeScript = Join-ProjectPath $projectRoot ("runtime/python/.runtime-check-{0}.py" -f ([guid]::NewGuid().ToString("N")))
Set-Content -LiteralPath $probeScript -Value $probeCode -Encoding UTF8
try {
    $probeOutput = & $pythonPath $probeScript $projectRoot 2>&1
    $probeExitCode = $LASTEXITCODE
} finally {
    if (Test-Path -LiteralPath $probeScript) {
        Remove-Item -LiteralPath $probeScript -Force
    }
}

if ($probeExitCode -ne 0) {
    $payload.error = (($probeOutput | Out-String).Trim())
    if ([string]::IsNullOrWhiteSpace($payload.error)) {
        $payload.error = "Bundled Python konnte nicht gestartet werden."
    }
    $payload | ConvertTo-Json -Depth 8
    exit 1
}

$probe = ($probeOutput | Out-String).Trim() | ConvertFrom-Json
$runtimeRoot = (Join-ProjectPath $projectRoot "runtime/python")
$payload.python.version = [string]$probe.version
$payload.python.executable = [string]$probe.executable
$payload.python.base_prefix = [string]$probe.base_prefix
$payload.provenance.encodings = [string]$probe.encodings
$payload.provenance.yaml = [string]$probe.yaml
$payload.provenance["optimizer_contract"] = [string]$probe.optimizer_contract
$payload.provenance["optimizer_file_contract"] = [string]$probe.optimizer_file_contract
$payload.provenance.sys_path = @($probe.sys_path)

$violations = @()
foreach ($key in @("executable", "base_prefix")) {
    $value = [string]$payload.python[$key]
    if (-not $value.StartsWith($runtimeRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        $violations += "$key zeigt ausserhalb der gebuendelten Runtime: $value"
    }
}
foreach ($key in @("encodings", "yaml")) {
    $value = [string]$payload.provenance[$key]
    if (-not $value.StartsWith($runtimeRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        $violations += "$key wird ausserhalb der gebuendelten Runtime geladen: $value"
    }
}
foreach ($key in @("optimizer_contract", "optimizer_file_contract")) {
    $value = [string]$payload.provenance[$key]
    if (-not $value.StartsWith($projectRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        $violations += "$key wird ausserhalb des Modulordners geladen: $value"
    }
}
if (-not ([string]$payload.python.version).StartsWith([string]$manifest.python_version)) {
    $violations += "Unerwartete Python-Version: $($payload.python.version)"
}

$payload.violations = $violations
$payload.ok = ($violations.Count -eq 0)
if (-not $payload.ok -and [string]::IsNullOrWhiteSpace($payload.error)) {
    $payload.error = "Runtime-Provenance ist nicht portable."
}

$payload | ConvertTo-Json -Depth 8
if (-not $payload.ok) {
    exit 1
}
