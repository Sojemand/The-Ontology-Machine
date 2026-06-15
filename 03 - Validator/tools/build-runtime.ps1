[CmdletBinding()]
param(
    [string]$SourceRuntime = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$runtimeRoot = Join-Path $projectRoot "runtime"
$targetRuntime = Join-Path $projectRoot "runtime\python"
$checkerPath = Join-Path $projectRoot "tools\check-runtime.ps1"

function Resolve-SourceRuntime {
    param([string]$Value)

    $candidates = @()
    if (-not [string]::IsNullOrWhiteSpace($Value)) {
        $candidates += [System.IO.Path]::GetFullPath($Value)
    } else {
        $candidates += (Join-Path $PSScriptRoot "python-runtime-source")
    }

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }
    return ""
}

function Copy-RuntimeTree {
    param(
        [string]$SourceDir,
        [string]$TargetDir
    )

    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
    Get-ChildItem -LiteralPath $SourceDir -Force | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $TargetDir $_.Name) -Recurse -Force
    }
}

function Assert-SourceRuntime {
    param([string]$SourceDir)

    foreach ($relativePath in @(
        "python.exe",
        "python311.dll",
        "Lib\encodings\__init__.py"
    )) {
        $candidate = Join-Path $SourceDir $relativePath
        if (-not (Test-Path -LiteralPath $candidate)) {
            throw "Portable Python-Quelle ist unvollstaendig: $relativePath fehlt."
        }
    }

    $pythonPath = Join-Path $SourceDir "python.exe"
    $probeOutput = & $pythonPath -c "import encodings, sys; print(sys.version.split()[0])" 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw ("Portable Python-Quelle konnte nicht gestartet werden: {0}" -f (($probeOutput | Out-String).Trim()))
    }
}

function Remove-PathIfPresent {
    param([string]$TargetPath)

    if (Test-Path -LiteralPath $TargetPath) {
        Remove-Item -LiteralPath $TargetPath -Recurse -Force
    }
}

function Move-StagedRuntimeIntoPlace {
    param(
        [string]$StageDir,
        [string]$TargetDir,
        [string]$BackupDir
    )

    $targetMoved = $false
    try {
        if (Test-Path -LiteralPath $TargetDir) {
            Move-Item -LiteralPath $TargetDir -Destination $BackupDir -Force
            $targetMoved = $true
        }
        Move-Item -LiteralPath $StageDir -Destination $TargetDir -Force

        $checkOutput = & $checkerPath -RootDir $projectRoot 2>&1
        $checkExitCode = $LASTEXITCODE
        if ($checkOutput) {
            Write-Host (($checkOutput | Out-String).Trim())
        }
        if ($checkExitCode -ne 0) {
            throw "Runtime-Check nach Staging-Swap fehlgeschlagen (exit $checkExitCode)."
        }
    } catch {
        if (Test-Path -LiteralPath $TargetDir) {
            Remove-Item -LiteralPath $TargetDir -Recurse -Force
        }
        if ($targetMoved -and (Test-Path -LiteralPath $BackupDir)) {
            Move-Item -LiteralPath $BackupDir -Destination $TargetDir -Force
        }
        throw
    } finally {
        Remove-PathIfPresent -TargetPath $StageDir
        Remove-PathIfPresent -TargetPath $BackupDir
    }
}

$sourceRuntime = Resolve-SourceRuntime -Value $SourceRuntime
if ([string]::IsNullOrWhiteSpace($sourceRuntime)) {
    throw "Keine portable Python-Quelle gefunden. Erwartet als -SourceRuntime oder unter tools\python-runtime-source."
}

Assert-SourceRuntime -SourceDir $sourceRuntime
Write-Host ("[BUILD] Portable Python source: {0}" -f $sourceRuntime)
$stageRuntime = Join-Path $runtimeRoot (".python-stage-{0}" -f ([guid]::NewGuid().ToString("N")))
$backupRuntime = Join-Path $runtimeRoot (".python-backup-{0}" -f ([guid]::NewGuid().ToString("N")))
Copy-RuntimeTree -SourceDir $sourceRuntime -TargetDir $stageRuntime

foreach ($relativePath in @(
    "Doc",
    "include",
    "libs",
    "Scripts",
    "Lib\site-packages",
    "Lib\test",
    "Lib\ensurepip",
    "Lib\idlelib",
    "Lib\turtledemo",
    "Lib\venv"
)) {
    Remove-PathIfPresent -TargetPath (Join-Path $stageRuntime $relativePath)
}

Get-ChildItem -LiteralPath $stageRuntime -Recurse -Directory -Force | Where-Object { $_.Name -eq "__pycache__" } | Remove-Item -Recurse -Force

Move-StagedRuntimeIntoPlace -StageDir $stageRuntime -TargetDir $targetRuntime -BackupDir $backupRuntime
