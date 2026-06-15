[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$BuildArgs = @()
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$pipelineRoot = Split-Path -Parent $projectRoot
$builderPath = Join-Path $pipelineRoot "tools\build-runtimes.bat"
$checkerPath = Join-Path $projectRoot "tools\check-runtime.ps1"

if (-not (Test-Path -LiteralPath $builderPath)) {
    throw "Zentraler Runtime-Builder wurde nicht gefunden: $builderPath"
}

$commandArgs = @("--module", "01 - Optimizer", "--archive-wheelhouse") + $BuildArgs
& $builderPath @commandArgs
$buildExitCode = $LASTEXITCODE
if ($buildExitCode -ne 0) {
    exit $buildExitCode
}

$checkOutput = & $checkerPath -RootDir $projectRoot 2>&1
$checkExitCode = $LASTEXITCODE
if ($checkOutput) {
    Write-Host (($checkOutput | Out-String).Trim())
}
if ($checkExitCode -ne 0) {
    exit $checkExitCode
}
