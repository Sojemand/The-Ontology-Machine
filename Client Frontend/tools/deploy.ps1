[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$TargetDir,
    [switch]$IncludeStateSnapshot,
    [string]$StateHome,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceRoot = Split-Path -Parent $scriptDir
$resolvedTarget = [System.IO.Path]::GetFullPath($TargetDir)
$immutableDirs = @("app", "assistant", "client_frontend", "node", "runtime", "server", "shared")
$immutableFiles = @("package.json", "start.bat", "config.bat", "installer.bat", "build-runtime.bat", "README.md", "README.txt", "requirements.txt", "tools/check-runtimes.mjs", "tools/clear-stale-server-port.mjs", "tools/deploy.ps1", "tools/installer.ps1")
$chatDbFiles = @("chats.db", "chats.db-shm", "chats.db-wal")

function Write-DeployLog([string]$Message) {
    Write-Host ("[deploy] {0}" -f $Message)
}

function Ensure-Dir([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Copy-Entry([string]$SourcePath, [string]$TargetPath, [switch]$Directory) {
    if ($DryRun) {
        Write-DeployLog ("DRYRUN copy {0} -> {1}" -f $SourcePath, $TargetPath)
        return
    }
    Ensure-Dir (Split-Path -Parent $TargetPath)
    if ($Directory -and (Test-Path -LiteralPath $TargetPath)) {
        Remove-Item -LiteralPath $TargetPath -Recurse -Force
    }
    Copy-Item -LiteralPath $SourcePath -Destination $TargetPath -Recurse:$Directory -Force
}

function Resolve-StateRoot {
    if (-not [string]::IsNullOrWhiteSpace($StateHome)) {
        return [System.IO.Path]::GetFullPath($StateHome)
    }
    if (-not [string]::IsNullOrWhiteSpace($env:VISION_PIPELINE_CLIENT_FRONTEND_HOME)) {
        return [System.IO.Path]::GetFullPath($env:VISION_PIPELINE_CLIENT_FRONTEND_HOME)
    }
    if (-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        return [System.IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA "Enterprise Stack\Client Frontend"))
    }
    throw "State-Snapshot angefordert, aber weder StateHome noch VISION_PIPELINE_CLIENT_FRONTEND_HOME noch LOCALAPPDATA sind gesetzt."
}

function Export-StateSnapshot {
    $snapshotRoot = Join-Path $resolvedTarget "state-snapshot"
    $configTarget = Join-Path $snapshotRoot "config"
    $stateTarget = Join-Path $snapshotRoot "state"
    $stateRoot = Resolve-StateRoot
    $configSource = Join-Path $stateRoot "config"
    $stateSource = Join-Path $stateRoot "state"
    $legacyConfig = Join-Path $sourceRoot "config.json"
    $legacySalt = Join-Path $sourceRoot ".salt"
    $legacyLogs = Join-Path $sourceRoot "logs"

    if (-not $DryRun -and (Test-Path -LiteralPath $snapshotRoot)) {
        Remove-Item -LiteralPath $snapshotRoot -Recurse -Force
    }
    if ((Test-Path -LiteralPath $configSource) -and (Get-ChildItem -LiteralPath $configSource -Force | Select-Object -First 1)) {
        Copy-Entry $configSource $configTarget -Directory
    } else {
        foreach ($legacyFile in @($legacyConfig, $legacySalt)) {
            if (Test-Path -LiteralPath $legacyFile) {
                Copy-Entry $legacyFile (Join-Path $configTarget (Split-Path -Leaf $legacyFile))
            }
        }
    }
    if ((Test-Path -LiteralPath $stateSource) -and (Get-ChildItem -LiteralPath $stateSource -Force | Select-Object -First 1)) {
        Copy-Entry $stateSource $stateTarget -Directory
    } else {
        foreach ($dbFile in $chatDbFiles) {
            $legacyPath = Join-Path $sourceRoot $dbFile
            if (Test-Path -LiteralPath $legacyPath) {
                Copy-Entry $legacyPath (Join-Path $stateTarget $dbFile)
            }
        }
    }
    if (Test-Path -LiteralPath $legacyLogs) {
        Write-DeployLog "Legacy-logs werden nicht in den State-Snapshot uebernommen."
    }
}

if (-not $DryRun) { Ensure-Dir $resolvedTarget }
Write-DeployLog ("source = {0}" -f $sourceRoot)
Write-DeployLog ("target = {0}" -f $resolvedTarget)
Write-DeployLog ("includeStateSnapshot = {0}; dryRun = {1}" -f $IncludeStateSnapshot, $DryRun)

foreach ($entry in $immutableDirs) {
    Copy-Entry (Join-Path $sourceRoot $entry) (Join-Path $resolvedTarget $entry) -Directory
}
foreach ($entry in $immutableFiles) {
    Copy-Entry (Join-Path $sourceRoot $entry) (Join-Path $resolvedTarget $entry)
}
if ($IncludeStateSnapshot) {
    Export-StateSnapshot
}
Write-DeployLog "deploy complete"
