[CmdletBinding()]
param(
    [string]$BasePython = "",
    [switch]$Offline,
    [switch]$RefreshWheelhouse,
    [switch]$ArchiveWheelhouse
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$pluginDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$bootstrap = Join-Path $pluginDir "bootstrap.py"
$runtimeDir = Join-Path $pluginDir "runtime\python"

$pythonExe = if ([string]::IsNullOrWhiteSpace($BasePython)) { "python" } else { $BasePython }
$args = @(
    $bootstrap,
    "bootstrap",
    "--plugin-dir", $pluginDir,
    "--runtime-dir", $runtimeDir
)

if (-not [string]::IsNullOrWhiteSpace($BasePython)) {
    $args += @("--base-python", $BasePython)
}
if ($Offline) {
    $args += "--offline"
}
if ($RefreshWheelhouse) {
    $args += "--refresh-wheelhouse"
}
if ($ArchiveWheelhouse) {
    $args += "--archive-wheelhouse"
}

& $pythonExe @args
