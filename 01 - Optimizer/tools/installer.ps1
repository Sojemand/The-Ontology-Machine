[CmdletBinding()]
param(
    [string]$SourceRoot = "",
    [string]$InstallRoot = "",
    [switch]$CheckOnly
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
function Resolve-InstallRoot {
    param(
        [string]$Value,
        [bool]$SkipDefault
    )
    if (-not [string]::IsNullOrWhiteSpace($Value)) {
        return [System.IO.Path]::GetFullPath($Value)
    }
    if ($SkipDefault) {
        return ""
    }
    if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        throw "LOCALAPPDATA ist nicht gesetzt."
    }
    return (Join-Path $env:LOCALAPPDATA "Enterprise Stack\Optimizer\app")
}
function Invoke-RuntimeCheck {
    param([string]$RootDir)
    $checkerPath = Join-Path $RootDir "tools\check-runtime.ps1"
    $raw = & $checkerPath -RootDir $RootDir 2>&1
    return [PSCustomObject]@{
        ExitCode = $LASTEXITCODE
        Raw = ($raw | Out-String).Trim()
        Status = if ($raw) { (($raw | Out-String).Trim() | ConvertFrom-Json) } else { $null }
    }
}
function Reset-InstallDirectory {
    param([string]$TargetDir)
    $resolvedTarget = [System.IO.Path]::GetFullPath($TargetDir)
    if ((Split-Path -Leaf $resolvedTarget) -ne "app") {
        throw "InstallRoot muss auf ein app-Verzeichnis zeigen: $resolvedTarget"
    }
    $parentDir = Split-Path -Parent $resolvedTarget
    if (Test-Path -LiteralPath $resolvedTarget) {
        $trashDir = Join-Path $parentDir (".app-delete-{0}" -f ([guid]::NewGuid().ToString("N")))
        Move-Item -LiteralPath $resolvedTarget -Destination $trashDir -Force
        try {
            Remove-Item -LiteralPath $trashDir -Recurse -Force -ErrorAction Stop
        } catch {
            # A stale cache must not block a fresh portable install.
        }
    }
    New-Item -ItemType Directory -Path $resolvedTarget -Force | Out-Null
}
function Copy-ProjectItem {
    param(
        [string]$SourceDir,
        [string]$TargetDir,
        [string]$RelativePath
    )
    $sourcePath = Join-Path $SourceDir $RelativePath
    if (-not (Test-Path -LiteralPath $sourcePath)) {
        return
    }
    $targetPath = Join-Path $TargetDir $RelativePath
    $targetParent = Split-Path -Parent $targetPath
    if (-not (Test-Path -LiteralPath $targetParent)) {
        New-Item -ItemType Directory -Path $targetParent -Force | Out-Null
    }
    if (Test-Path -LiteralPath $sourcePath -PathType Container) {
        if (-not (Test-Path -LiteralPath $targetPath)) {
            New-Item -ItemType Directory -Path $targetPath -Force | Out-Null
        }
        $excludedDirs = @("__pycache__")
        if ($RelativePath -eq "plugins") {
            $excludedDirs += @("runtime", "venv", ".venv")
        }
        & robocopy $sourcePath $targetPath /E /MT:8 /R:1 /W:1 /NFL /NDL /NJH /NJS /NC /NS /NP /XD $excludedDirs /XF *.pyc *.pyo | Out-Null
        if ($LASTEXITCODE -gt 7) {
            throw "Robocopy fehlgeschlagen fuer $RelativePath (ExitCode=$LASTEXITCODE)."
        }
        return
    }
    Copy-Item -LiteralPath $sourcePath -Destination $targetPath -Force
}
function Ensure-AppHomeLayout {
    param(
        [string]$InstallDir,
        [string]$AppHomeDir
    )
    foreach ($relativePath in @("config", "state", "output", "logs")) {
        $target = Join-Path $AppHomeDir $relativePath
        if (-not (Test-Path -LiteralPath $target)) {
            New-Item -ItemType Directory -Path $target -Force | Out-Null
        }
    }
    $bundledConfig = Join-Path $InstallDir "config"
    if (-not (Test-Path -LiteralPath $bundledConfig)) {
        return
    }
    Get-ChildItem -LiteralPath $bundledConfig -Recurse -Force | ForEach-Object {
        $relative = $_.FullName.Substring($bundledConfig.Length).TrimStart("\")
        if ([string]::IsNullOrWhiteSpace($relative)) {
            return
        }
        $target = Join-Path (Join-Path $AppHomeDir "config") $relative
        if ($_.PSIsContainer) {
            if (-not (Test-Path -LiteralPath $target)) {
                New-Item -ItemType Directory -Path $target -Force | Out-Null
            }
            return
        }
        if (-not (Test-Path -LiteralPath $target)) {
            $parent = Split-Path -Parent $target
            if (-not (Test-Path -LiteralPath $parent)) {
                New-Item -ItemType Directory -Path $parent -Force | Out-Null
            }
            Copy-Item -LiteralPath $_.FullName -Destination $target -Force
        }
    }
}
$projectRoot = Resolve-RootDir $SourceRoot
$installRoot = Resolve-InstallRoot -Value $InstallRoot -SkipDefault:$CheckOnly
$sourceCheck = Invoke-RuntimeCheck -RootDir $projectRoot
if ($sourceCheck.Raw -and $sourceCheck.ExitCode -ne 0) {
    Write-Host $sourceCheck.Raw
}
if ($sourceCheck.ExitCode -ne 0) {
    exit $sourceCheck.ExitCode
}
if ($CheckOnly) {
    [PSCustomObject]@{
        ok = $true
        source_root = $projectRoot
        runtime = $sourceCheck.Status
    } | ConvertTo-Json -Depth 6
    exit 0
}
$appHome = Split-Path -Parent $installRoot
Reset-InstallDirectory -TargetDir $installRoot
foreach ($relativePath in @(
    "optimizer_ocr",
    "ingestion_layer_vision",
    "ingestion_layer_file",
    "plugins",
    "runtime",
    "config",
    "tools",
    "module-manifest.json",
    "requirements.txt",
    "README.md",
    "check-runtime.bat",
    "installer.bat",
    "build-installer.bat"
)) {
    Copy-ProjectItem -SourceDir $projectRoot -TargetDir $installRoot -RelativePath $relativePath
}
Ensure-AppHomeLayout -InstallDir $installRoot -AppHomeDir $appHome
$installedCheck = Invoke-RuntimeCheck -RootDir $installRoot
if ($installedCheck.Raw -and $installedCheck.ExitCode -ne 0) {
    Write-Host $installedCheck.Raw
}
if ($installedCheck.ExitCode -ne 0) {
    exit $installedCheck.ExitCode
}
[PSCustomObject]@{
    ok = $true
    source_root = $projectRoot
    install_root = $installRoot
    app_home = $appHome
    runtime = $installedCheck.Status
} | ConvertTo-Json -Depth 6
