[CmdletBinding()]
param(
    [string]$InstallRoot
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceRoot = Split-Path -Parent $scriptDir
$immutableDirs = @("app", "assistant", "client_frontend", "node", "runtime", "server", "shared")
$immutableFiles = @("package.json", "start.bat", "config.bat", "installer.bat", "build-runtime.bat", "README.md", "README.txt", "requirements.txt", "tools/check-runtimes.mjs", "tools/clear-stale-server-port.mjs", "tools/deploy.ps1", "tools/installer.ps1")
$chatDbFiles = @("chats.db", "chats.db-shm", "chats.db-wal")

function Resolve-AppHome {
    if (-not [string]::IsNullOrWhiteSpace($env:VISION_PIPELINE_CLIENT_FRONTEND_HOME)) {
        return [System.IO.Path]::GetFullPath($env:VISION_PIPELINE_CLIENT_FRONTEND_HOME)
    }
    if (-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        return [System.IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA "Enterprise Stack\Client Frontend"))
    }
    throw "VISION_PIPELINE_CLIENT_FRONTEND_HOME ist nicht gesetzt und LOCALAPPDATA fehlt."
}

function New-Layout {
    $appHome = Resolve-AppHome
    return [PSCustomObject]@{
        AppHome = $appHome
        AppDir = if ($InstallRoot) { [System.IO.Path]::GetFullPath($InstallRoot) } else { Join-Path $appHome "app" }
        ConfigDir = Join-Path $appHome "config"
        StateDir = Join-Path $appHome "state"
        LogDir = Join-Path $appHome "logs"
        SnapshotDir = Join-Path $sourceRoot "state-snapshot"
    }
}

$layout = New-Layout
$logFile = Join-Path $layout.LogDir "installer.log"

function Ensure-Dir([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Write-Log([string]$Message) {
    Ensure-Dir $layout.LogDir
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -LiteralPath $logFile -Value $line -Encoding UTF8
    Write-Host $line
}

function Invoke-RuntimeCheck([string]$RootPath) {
    $nodePath = Join-Path $RootPath "node\node.exe"
    $checkerPath = Join-Path $RootPath "tools\check-runtimes.mjs"
    if (-not (Test-Path -LiteralPath $nodePath)) {
        throw "Bundled Node runtime fehlt: $nodePath"
    }
    & $nodePath "--disable-warning=ExperimentalWarning" $checkerPath
    if ($LASTEXITCODE -ne 0) {
        throw "Runtime-Check fehlgeschlagen fuer $RootPath"
    }
}

function Test-DirHasContent([string]$Path) {
    return (Test-Path -LiteralPath $Path) -and (Get-ChildItem -LiteralPath $Path -Force | Select-Object -First 1)
}

function Test-LogDirHasUserContent([string]$Path) {
    return (Test-Path -LiteralPath $Path) -and (Get-ChildItem -LiteralPath $Path -Force | Where-Object { $_.Name -ne "installer.log" } | Select-Object -First 1)
}

function Copy-ImmutablePayload {
    $sourceResolved = [System.IO.Path]::GetFullPath($sourceRoot)
    $targetResolved = [System.IO.Path]::GetFullPath($layout.AppDir)
    if ($sourceResolved -ieq $targetResolved) {
        Write-Log "Installer-Quelle und AppDir sind identisch; Payload-Copy wird uebersprungen."
        return
    }
    if (Test-Path -LiteralPath $layout.AppDir) {
        Remove-Item -LiteralPath $layout.AppDir -Recurse -Force
    }
    Ensure-Dir $layout.AppDir
    foreach ($entry in $immutableDirs) {
        Copy-Item -LiteralPath (Join-Path $sourceRoot $entry) -Destination (Join-Path $layout.AppDir $entry) -Recurse -Force
    }
    foreach ($entry in $immutableFiles) {
        $targetPath = Join-Path $layout.AppDir $entry
        Ensure-Dir (Split-Path -Parent $targetPath)
        Copy-Item -LiteralPath (Join-Path $sourceRoot $entry) -Destination $targetPath -Force
    }
}

function Move-LegacyState {
    $legacyEntries = @(
        @{ Source = Join-Path $sourceRoot "config.json"; Target = Join-Path $layout.ConfigDir "config.json"; Label = "config.json" },
        @{ Source = Join-Path $sourceRoot ".salt"; Target = Join-Path $layout.ConfigDir ".salt"; Label = ".salt" },
        @{ Source = Join-Path $sourceRoot "logs"; Target = $layout.LogDir; Label = "logs"; Directory = $true }
    ) + ($chatDbFiles | ForEach-Object {
            @{ Source = Join-Path $sourceRoot $_; Target = Join-Path $layout.StateDir $_; Label = $_ }
        })
    $isDirectoryEntry = {
        param($Entry)
        return $Entry.ContainsKey("Directory") -and [bool]$Entry["Directory"]
    }
    $present = @($legacyEntries | Where-Object {
            if (& $isDirectoryEntry $_) { Test-DirHasContent $_.Source } else { Test-Path -LiteralPath $_.Source }
        })
    if (-not $present.Count) { return }
    $conflicts = @($legacyEntries | Where-Object {
            if ($_.Label -eq "logs") { return Test-LogDirHasUserContent $_.Target }
            if (& $isDirectoryEntry $_) { return Test-DirHasContent $_.Target }
            return Test-Path -LiteralPath $_.Target
        })
    if ($conflicts.Count) {
        throw "Legacy-Root-State und externer App-Home-State koennen nicht gemischt werden: $($conflicts.Label -join ', ')"
    }
    foreach ($entry in $present) {
        if (& $isDirectoryEntry $entry) {
            Copy-Item -LiteralPath $entry.Source -Destination $entry.Target -Recurse -Force
            Remove-Item -LiteralPath $entry.Source -Recurse -Force
            continue
        }
        Ensure-Dir (Split-Path -Parent $entry.Target)
        Copy-Item -LiteralPath $entry.Source -Destination $entry.Target -Force
        Remove-Item -LiteralPath $entry.Source -Force
    }
    Write-Log ("Legacy-State migriert: {0}" -f ($present.Label -join ", "))
}

function Import-StateSnapshot {
    $configSnapshot = Join-Path $layout.SnapshotDir "config"
    $stateSnapshot = Join-Path $layout.SnapshotDir "state"
    if (-not (Test-DirHasContent $configSnapshot) -and -not (Test-DirHasContent $stateSnapshot)) {
        return
    }
    if (Test-DirHasContent $layout.ConfigDir -or Test-DirHasContent $layout.StateDir) {
        throw "State-Snapshot kann nicht importiert werden, weil config/state bereits belegt sind."
    }
    if (Test-DirHasContent $configSnapshot) {
        Get-ChildItem -LiteralPath $configSnapshot -Force | ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $layout.ConfigDir $_.Name) -Recurse -Force
        }
    }
    if (Test-DirHasContent $stateSnapshot) {
        Get-ChildItem -LiteralPath $stateSnapshot -Force | ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $layout.StateDir $_.Name) -Recurse -Force
        }
    }
    Write-Log "State-Snapshot importiert."
}

Ensure-Dir $layout.ConfigDir
Ensure-Dir $layout.StateDir
Ensure-Dir $layout.LogDir
Set-Content -LiteralPath $logFile -Value ("[{0}] Installer gestartet." -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss")) -Encoding UTF8

Write-Log ("Quelle = {0}" -f $sourceRoot)
Write-Log ("AppHome = {0}" -f $layout.AppHome)
Write-Log ("AppDir = {0}" -f $layout.AppDir)
Invoke-RuntimeCheck $sourceRoot
Copy-ImmutablePayload
Move-LegacyState
Import-StateSnapshot
Invoke-RuntimeCheck $layout.AppDir
Write-Log "Per-User-Installation abgeschlossen."
