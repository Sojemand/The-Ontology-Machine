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
    return (Join-Path $env:LOCALAPPDATA "Enterprise Stack\Interpreter\app")
}

function Assert-SafeInstallRoot {
    param([string]$TargetDir)

    if ([string]::IsNullOrWhiteSpace($TargetDir)) {
        throw "InstallRoot fehlt."
    }
    $trimChars = [char[]]@([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar)
    $normalized = ([System.IO.Path]::GetFullPath($TargetDir)).TrimEnd($trimChars)
    $root = ([System.IO.Path]::GetPathRoot($normalized)).TrimEnd($trimChars)
    if ($normalized.Equals($root, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "InstallRoot darf kein Laufwerks- oder Dateisystem-Root sein: $normalized"
    }
    if (-not ((Split-Path -Leaf $normalized).Equals("app", [System.StringComparison]::OrdinalIgnoreCase))) {
        throw "InstallRoot muss auf einen app-Ordner zeigen: $normalized"
    }
    $parent = (Split-Path -Parent $normalized).TrimEnd($trimChars)
    if ([string]::IsNullOrWhiteSpace($parent) -or $parent.Equals($root, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "InstallRoot muss unter einem App-Home liegen: $normalized"
    }
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

    $envExample = Join-Path $InstallDir ".env.example"
    $userEnv = Join-Path (Join-Path $AppHomeDir "config") ".env"
    if ((Test-Path -LiteralPath $envExample) -and -not (Test-Path -LiteralPath $userEnv)) {
        Copy-Item -LiteralPath $envExample -Destination $userEnv -Force
    }
}

function Invoke-ConfigBootstrap {
    param(
        [string]$InstallDir,
        [string]$AppHomeDir
    )

    $pythonExe = Join-Path $InstallDir "runtime\python\python.exe"
    if (-not (Test-Path -LiteralPath $pythonExe)) {
        throw "Runtime-Python fuer Config-Bootstrap fehlt: $pythonExe"
    }
    Push-Location $InstallDir
    try {
        $raw = & $pythonExe -m llm_interpreter.config_bootstrap --app-home $AppHomeDir 2>&1
    } finally {
        Pop-Location
    }
    if ($LASTEXITCODE -ne 0) {
        throw (($raw | Out-String).Trim())
    }
}

function Reset-InstallDirectory {
    param([string]$TargetDir)

    Assert-SafeInstallRoot -TargetDir $TargetDir
    if (Test-Path -LiteralPath $TargetDir) {
        Remove-Item -LiteralPath $TargetDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
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
        & robocopy $sourcePath $targetPath /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NC /NS /NP /XD __pycache__ /XF *.pyc *.pyo | Out-Null
        if ($LASTEXITCODE -gt 7) {
            throw "Robocopy fehlgeschlagen fuer $RelativePath (ExitCode=$LASTEXITCODE)."
        }
        return
    }
    Copy-Item -LiteralPath $sourcePath -Destination $targetPath -Force
}

$projectRoot = Resolve-RootDir $SourceRoot
$installRoot = Resolve-InstallRoot -Value $InstallRoot -SkipDefault:$CheckOnly
if (-not $CheckOnly) {
    Assert-SafeInstallRoot -TargetDir $installRoot
}

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
    "llm_interpreter",
    "runtime",
    "tools",
    ".env.example",
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
Invoke-ConfigBootstrap -InstallDir $installRoot -AppHomeDir $appHome

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
