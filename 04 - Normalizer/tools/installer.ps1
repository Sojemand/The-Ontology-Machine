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

function Resolve-DefaultInstallRoot {
    param([string]$ManifestPath)

    $manifest = Get-Content -Raw -LiteralPath $ManifestPath | ConvertFrom-Json
    $defaultPath = [string]$manifest.default_install_dir
    if ([string]::IsNullOrWhiteSpace($defaultPath)) {
        throw "default_install_dir fehlt im Installer-Manifest."
    }
    return [Environment]::ExpandEnvironmentVariables($defaultPath)
}

function Join-ProjectPath {
    param(
        [string]$BaseDir,
        [string]$RelativePath
    )

    $normalized = $RelativePath.Replace("/", "\")
    return Join-Path $BaseDir $normalized
}

function Invoke-RuntimeCheck {
    param(
        [string]$CheckerPath,
        [string]$RootDir
    )

    $raw = & $CheckerPath -RootDir $RootDir 2>&1
    $exitCode = $LASTEXITCODE
    $text = ($raw | Out-String).Trim()
    $status = if ([string]::IsNullOrWhiteSpace($text)) { $null } else { $text | ConvertFrom-Json }
    return [PSCustomObject]@{
        ExitCode = $exitCode
        Raw = $text
        Status = $status
    }
}

function Get-SafeChildItems {
    param([string]$Path)

    try {
        return @(Get-ChildItem -LiteralPath $Path -Force -ErrorAction Stop)
    } catch [System.UnauthorizedAccessException] {
        throw "Zugriff verweigert beim Lesen von Installationsdaten: $Path"
    }
}

function Test-ExcludedEntry {
    param(
        [string]$Name,
        [string[]]$ExcludedRootNames
    )

    if ($ExcludedRootNames -contains $Name) {
        return $true
    }
    return $Name -like "pytest-cache-files-*"
}

function Save-InstallState {
    param(
        [string]$InstallDir,
        [string]$StashDir,
        [string[]]$MutableDirs,
        [string[]]$MutableFiles,
        [string[]]$MutableGlobs
    )

    if (-not (Test-Path -LiteralPath $InstallDir)) {
        return
    }

    foreach ($relativePath in @($MutableFiles) + @($MutableDirs)) {
        $sourcePath = Join-ProjectPath $InstallDir $relativePath
        if (-not (Test-Path -LiteralPath $sourcePath)) {
            continue
        }
        $targetPath = Join-ProjectPath $StashDir $relativePath
        $targetParent = Split-Path -Parent $targetPath
        if (-not (Test-Path -LiteralPath $targetParent)) {
            New-Item -ItemType Directory -Path $targetParent -Force | Out-Null
        }
        if (Test-Path -LiteralPath $sourcePath -PathType Container) {
            Copy-ProjectTree -SourcePath $sourcePath -TargetPath $targetPath -ExcludedRelativePaths @()
        } else {
            Copy-Item -LiteralPath $sourcePath -Destination $targetPath -Force
        }
    }

    foreach ($relativePattern in $MutableGlobs) {
        foreach ($match in Get-MutableGlobMatches -BaseDir $InstallDir -RelativePattern $relativePattern) {
            $targetPath = Join-ProjectPath $StashDir $match.RelativePath
            $targetParent = Split-Path -Parent $targetPath
            if (-not (Test-Path -LiteralPath $targetParent)) {
                New-Item -ItemType Directory -Path $targetParent -Force | Out-Null
            }
            Copy-Item -LiteralPath $match.Path -Destination $targetPath -Force
        }
    }

}

function Restore-InstallState {
    param(
        [string]$InstallDir,
        [string]$StashDir,
        [string]$SourceDir,
        [string[]]$MutableDirs,
        [string[]]$MutableFiles,
        [string[]]$MutableGlobs
    )

    foreach ($directory in $MutableDirs) {
        $target = Join-ProjectPath $InstallDir $directory
        if (-not (Test-Path -LiteralPath $target)) {
            New-Item -ItemType Directory -Path $target -Force | Out-Null
        }
        $stashed = Join-ProjectPath $StashDir $directory
        if (Test-Path -LiteralPath $stashed) {
            Copy-ProjectTree -SourcePath $stashed -TargetPath $target -ExcludedRelativePaths @()
        }
    }

    foreach ($relativePath in $MutableFiles) {
        $target = Join-ProjectPath $InstallDir $relativePath
        $stashed = Join-ProjectPath $StashDir $relativePath
        $source = Join-ProjectPath $SourceDir $relativePath
        $targetParent = Split-Path -Parent $target
        if (-not (Test-Path -LiteralPath $targetParent)) {
            New-Item -ItemType Directory -Path $targetParent -Force | Out-Null
        }
        if (Test-Path -LiteralPath $stashed) {
            Copy-Item -LiteralPath $stashed -Destination $target -Force
        } elseif (-not (Test-Path -LiteralPath $target) -and (Test-Path -LiteralPath $source)) {
            Copy-Item -LiteralPath $source -Destination $target -Force
        }
    }

    foreach ($relativePattern in $MutableGlobs) {
        $stashedMatches = @(Get-MutableGlobMatches -BaseDir $StashDir -RelativePattern $relativePattern)
        if ($stashedMatches.Count -eq 0) {
            continue
        }
        foreach ($match in Get-MutableGlobMatches -BaseDir $InstallDir -RelativePattern $relativePattern) {
            Remove-Item -LiteralPath $match.Path -Force
        }
        foreach ($match in $stashedMatches) {
            $target = Join-ProjectPath $InstallDir $match.RelativePath
            $targetParent = Split-Path -Parent $target
            if (-not (Test-Path -LiteralPath $targetParent)) {
                New-Item -ItemType Directory -Path $targetParent -Force | Out-Null
            }
            Copy-Item -LiteralPath $match.Path -Destination $target -Force
        }
    }
}

function Get-MutableGlobMatches {
    param(
        [string]$BaseDir,
        [string]$RelativePattern
    )

    $parentRelative = Split-Path -Parent $RelativePattern
    $leafPattern = Split-Path -Leaf $RelativePattern
    $searchRoot = if ([string]::IsNullOrWhiteSpace($parentRelative)) { $BaseDir } else { Join-ProjectPath $BaseDir $parentRelative }
    if (-not (Test-Path -LiteralPath $searchRoot)) {
        return @()
    }

    $items = @(Get-ChildItem -LiteralPath $searchRoot -Filter $leafPattern -File -Force -ErrorAction SilentlyContinue)
    return @(
        foreach ($item in $items) {
            [PSCustomObject]@{
                Path = $item.FullName
                RelativePath = if ([string]::IsNullOrWhiteSpace($parentRelative)) { $item.Name } else { Join-Path $parentRelative $item.Name }
            }
        }
    )
}

function Copy-ProjectTree {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SourcePath,
        [Parameter(Mandatory = $true)]
        [string]$TargetPath,
        [string[]]$ExcludedRelativePaths = @()
    )

    if (-not (Test-Path -LiteralPath $TargetPath)) {
        New-Item -ItemType Directory -Path $TargetPath -Force | Out-Null
    }

    foreach ($entry in Get-SafeChildItems $SourcePath) {
        if ($entry.Name -eq "__pycache__") {
            continue
        }
        if ($entry.Name -like "pytest-cache-files-*") {
            continue
        }
        if ($entry.Extension -in @(".pyc", ".pyo")) {
            continue
        }

        if ($ExcludedRelativePaths -contains $entry.Name) {
            continue
        }

        $destination = Join-Path $TargetPath $entry.Name
        if ($entry.PSIsContainer) {
            Copy-ProjectTree -SourcePath $entry.FullName -TargetPath $destination -ExcludedRelativePaths @()
            continue
        }

        Copy-Item -LiteralPath $entry.FullName -Destination $destination -Force
    }
}

function Copy-InstallPayload {
    param(
        [string]$SourceDir,
        [string]$InstallDir,
        [string[]]$ExcludedRootNames,
        [string[]]$ExcludedRelativePaths
    )

    if (-not (Test-Path -LiteralPath $InstallDir)) {
        New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    }

    foreach ($entry in Get-SafeChildItems $SourceDir) {
        if (Test-ExcludedEntry -Name $entry.Name -ExcludedRootNames $ExcludedRootNames) {
            continue
        }

        $relativePath = $entry.Name
        if ($ExcludedRelativePaths -contains $relativePath) {
            continue
        }

        $destination = Join-Path $InstallDir $entry.Name
        if ($entry.PSIsContainer) {
            Copy-ProjectTree -SourcePath $entry.FullName -TargetPath $destination -ExcludedRelativePaths @()
            continue
        }
        Copy-Item -LiteralPath $entry.FullName -Destination $destination -Force
    }

    foreach ($relativePath in $ExcludedRelativePaths) {
        $targetPath = Join-ProjectPath $InstallDir $relativePath
        if (Test-Path -LiteralPath $targetPath) {
            Remove-Item -LiteralPath $targetPath -Recurse -Force
        }
    }
}

$projectRoot = Resolve-RootDir $SourceRoot
$installerManifestPath = Join-ProjectPath $projectRoot "installer/installer-manifest.json"
$checkerPath = Join-ProjectPath $projectRoot "tools/check-runtime.ps1"

if (-not (Test-Path -LiteralPath $installerManifestPath)) {
    throw "Installer-Manifest fehlt: $installerManifestPath"
}
if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
    $InstallRoot = Resolve-DefaultInstallRoot $installerManifestPath
}

$installRoot = [System.IO.Path]::GetFullPath($InstallRoot)
$installerManifest = Get-Content -Raw -LiteralPath $installerManifestPath | ConvertFrom-Json
$mutableDirs = @($installerManifest.mutable_dirs) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
$mutableFiles = @($installerManifest.mutable_files) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
$mutableGlobs = @($installerManifest.mutable_globs) | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
$excludedRootNames = @(".git", ".pytest_cache", ".pytest-tmp", ".tmp", ".venv", "dev-tests", "vendor") + $mutableDirs
$excludedRelativePaths = @($installerManifest.excluded_runtime_paths)
$sourceCheck = Invoke-RuntimeCheck -CheckerPath $checkerPath -RootDir $projectRoot

if ($sourceCheck.ExitCode -ne 0) {
    if ($sourceCheck.Raw) {
        Write-Host $sourceCheck.Raw
    }
    exit $sourceCheck.ExitCode
}

if ($CheckOnly) {
    [PSCustomObject]@{
        ok = $true
        source_root = $projectRoot
        install_root = $installRoot
        runtime = $sourceCheck.Status
    } | ConvertTo-Json -Depth 8
    exit 0
}

$installParent = Split-Path -Parent $installRoot
if (-not (Test-Path -LiteralPath $installParent)) {
    New-Item -ItemType Directory -Path $installParent -Force | Out-Null
}

# Keep the temporary stash path short so long taxonomy filenames do not exceed MAX_PATH on reinstall.
$stashRoot = Join-Path $installParent (".nstash-{0}" -f ([guid]::NewGuid().ToString("N").Substring(0, 12)))
try {
    Save-InstallState -InstallDir $installRoot -StashDir $stashRoot -MutableDirs $mutableDirs -MutableFiles $mutableFiles -MutableGlobs $mutableGlobs
    if (Test-Path -LiteralPath $installRoot) {
        Remove-Item -LiteralPath $installRoot -Recurse -Force
    }
    Copy-InstallPayload -SourceDir $projectRoot -InstallDir $installRoot -ExcludedRootNames $excludedRootNames -ExcludedRelativePaths $excludedRelativePaths
    Restore-InstallState -InstallDir $installRoot -StashDir $stashRoot -SourceDir $projectRoot -MutableDirs $mutableDirs -MutableFiles $mutableFiles -MutableGlobs $mutableGlobs

    $installedCheck = Invoke-RuntimeCheck -CheckerPath (Join-ProjectPath $installRoot "tools/check-runtime.ps1") -RootDir $installRoot
    if ($installedCheck.ExitCode -ne 0) {
        if ($installedCheck.Raw) {
            Write-Host $installedCheck.Raw
        }
        exit $installedCheck.ExitCode
    }

    [PSCustomObject]@{
        ok = $true
        source_root = $projectRoot
        install_root = $installRoot
        runtime = $installedCheck.Status
    } | ConvertTo-Json -Depth 8
} finally {
    if (Test-Path -LiteralPath $stashRoot) {
        Remove-Item -LiteralPath $stashRoot -Recurse -Force
    }
}
