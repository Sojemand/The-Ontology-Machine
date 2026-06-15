[CmdletBinding()]
param(
    [string]$SourceRoot = "",
    [string]$InstallRoot = "",
    [switch]$CheckOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:ProjectRoot = if ([string]::IsNullOrWhiteSpace($SourceRoot)) {
    Split-Path -Parent $PSScriptRoot
} else {
    [System.IO.Path]::GetFullPath($SourceRoot)
}

if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
    if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        throw "LOCALAPPDATA ist nicht gesetzt."
    }
    $InstallRoot = Join-Path $env:LOCALAPPDATA "Enterprise Stack\Validator Vision\app"
}

$script:InstallRoot = [System.IO.Path]::GetFullPath($InstallRoot)
$script:AppHome = Split-Path -Parent $script:InstallRoot
$script:LogDir = Join-Path $script:AppHome "logs"
$script:LogFile = Join-Path $script:LogDir "installer.log"
$script:CheckerPath = Join-Path $script:ProjectRoot "tools\check-runtime.ps1"
$script:InstallStage = Join-Path $script:AppHome (".app-stage-{0}" -f ([guid]::NewGuid().ToString("N")))
$script:InstallBackup = Join-Path $script:AppHome (".app-backup-{0}" -f ([guid]::NewGuid().ToString("N")))

function Ensure-LogDirectory {
    if (-not (Test-Path -LiteralPath $script:LogDir)) {
        New-Item -ItemType Directory -Path $script:LogDir -Force | Out-Null
    }
}

function Reset-Log {
    Ensure-LogDirectory
    Set-Content -LiteralPath $script:LogFile -Value ("[{0}] [INFO] Validator installer started." -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss")) -Encoding UTF8
}
function Write-Log {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message,
        [ValidateSet("INFO", "WARN", "ERROR")]
        [string]$Level = "INFO"
    )
    Ensure-LogDirectory
    $line = "[{0}] [{1}] {2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Level, $Message
    Add-Content -LiteralPath $script:LogFile -Value $line -Encoding UTF8
    Write-Host $line
}

function Invoke-RuntimeCheck {
    param([string]$RootDir)
    $raw = & $script:CheckerPath -RootDir $RootDir 2>&1
    $exitCode = $LASTEXITCODE
    $text = ($raw | Out-String).Trim()
    $status = if ([string]::IsNullOrWhiteSpace($text)) { $null } else { $text | ConvertFrom-Json }
    return [PSCustomObject]@{
        ExitCode = $exitCode
        Raw = $text
        Status = $status
    }
}

function Ensure-AppHomeLayout {
    $directories = @(
        (Join-Path $script:AppHome "config"),
        (Join-Path $script:AppHome "logs"),
        (Join-Path $script:AppHome "output"),
        (Join-Path $script:AppHome "state")
    )
    foreach ($directory in $directories) {
        if (-not (Test-Path -LiteralPath $directory)) {
            New-Item -ItemType Directory -Path $directory -Force | Out-Null
        }
    }
    $bundledConfig = Join-Path $script:ProjectRoot "config\config.json"
    $userConfig = Join-Path $script:AppHome "config\config.json"
    if ((Test-Path -LiteralPath $bundledConfig) -and -not (Test-Path -LiteralPath $userConfig)) {
        Copy-FileAtomic -SourcePath $bundledConfig -TargetPath $userConfig
        Write-Log ("Konfiguration initial nach {0} kopiert." -f $userConfig)
    }
}

function Copy-FileAtomic {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SourcePath,
        [Parameter(Mandatory = $true)]
        [string]$TargetPath
    )

    $targetParent = Split-Path -Parent $TargetPath
    if (-not (Test-Path -LiteralPath $targetParent)) {
        New-Item -ItemType Directory -Path $targetParent -Force | Out-Null
    }
    $tempPath = Join-Path $targetParent (".{0}.tmp" -f ([guid]::NewGuid().ToString("N")))
    try {
        Copy-Item -LiteralPath $SourcePath -Destination $tempPath -Force
        Move-Item -LiteralPath $tempPath -Destination $TargetPath -Force
    } finally {
        if (Test-Path -LiteralPath $tempPath) {
            Remove-Item -LiteralPath $tempPath -Force
        }
    }
}

function Remove-TreeIfPresent {
    param([string]$TargetPath)

    if (Test-Path -LiteralPath $TargetPath) {
        Remove-Item -LiteralPath $TargetPath -Recurse -Force
    }
}
function New-InstallStage {
    Remove-TreeIfPresent -TargetPath $script:InstallStage
    New-Item -ItemType Directory -Path $script:InstallStage -Force | Out-Null
}
function Publish-StagedInstall {
    $targetMoved = $false
    try {
        if (Test-Path -LiteralPath $script:InstallRoot) {
            Move-Item -LiteralPath $script:InstallRoot -Destination $script:InstallBackup -Force
            $targetMoved = $true
        }
        Move-Item -LiteralPath $script:InstallStage -Destination $script:InstallRoot -Force

        $installedCheck = Invoke-RuntimeCheck -RootDir $script:InstallRoot
        if ($installedCheck.ExitCode -ne 0) {
            if ($installedCheck.Raw) {
                Write-Host $installedCheck.Raw
            }
            throw "Installierte Runtime ist unvollstaendig."
        }
        return $installedCheck
    } catch {
        if (Test-Path -LiteralPath $script:InstallRoot) {
            Remove-Item -LiteralPath $script:InstallRoot -Recurse -Force
        }
        if ($targetMoved -and (Test-Path -LiteralPath $script:InstallBackup)) {
            Move-Item -LiteralPath $script:InstallBackup -Destination $script:InstallRoot -Force
        }
        throw
    } finally {
        Remove-TreeIfPresent -TargetPath $script:InstallStage
        Remove-TreeIfPresent -TargetPath $script:InstallBackup
    }
}
function Copy-ProjectItem {
    param([string]$RelativePath)

    $sourcePath = Join-Path $script:ProjectRoot $RelativePath
    $targetPath = Join-Path $script:InstallStage $RelativePath
    $targetParent = Split-Path -Parent $targetPath
    if (-not (Test-Path -LiteralPath $targetParent)) {
        New-Item -ItemType Directory -Path $targetParent -Force | Out-Null
    }
    if (Test-Path -LiteralPath $sourcePath -PathType Container) {
        Copy-ProjectTree -SourcePath $sourcePath -TargetPath $targetPath
    } else {
        Copy-Item -LiteralPath $sourcePath -Destination $targetPath -Force
    }
}

function Copy-ProjectTree {
    param(
        [Parameter(Mandatory = $true)]
        [string]$SourcePath,
        [Parameter(Mandatory = $true)]
        [string]$TargetPath
    )

    if (Get-Command robocopy -ErrorAction SilentlyContinue) {
        $robocopyArgs = @(
            $SourcePath,
            $TargetPath,
            "/E",
            "/NFL",
            "/NDL",
            "/NJH",
            "/NJS",
            "/NP",
            "/R:1",
            "/W:1",
            "/XD",
            "__pycache__",
            "/XF",
            "*.pyc",
            "*.pyo"
        )
        & robocopy @robocopyArgs | Out-Null
        if ($LASTEXITCODE -ge 8) {
            throw "Kopieren fehlgeschlagen: $SourcePath -> $TargetPath (robocopy exit $LASTEXITCODE)"
        }
        return
    }

    if (-not (Test-Path -LiteralPath $TargetPath)) {
        New-Item -ItemType Directory -Path $TargetPath -Force | Out-Null
    }
    foreach ($entry in Get-ChildItem -LiteralPath $SourcePath -Force) {
        if ($entry.Name -eq "__pycache__") {
            continue
        }

        $destination = Join-Path $TargetPath $entry.Name
        if ($entry.PSIsContainer) {
            Copy-ProjectTree -SourcePath $entry.FullName -TargetPath $destination
            continue
        }

        if ($entry.Extension -in @(".pyc", ".pyo")) {
            continue
        }

        Copy-Item -LiteralPath $entry.FullName -Destination $destination -Force
    }
}

try {
    Reset-Log
    Write-Log ("Source root: {0}" -f $script:ProjectRoot)
    Write-Log ("Install root: {0}" -f $script:InstallRoot)

    $sourceCheck = Invoke-RuntimeCheck -RootDir $script:ProjectRoot
    if ($sourceCheck.ExitCode -ne 0) {
        Write-Log "Quellmodul ist nicht portable oder unvollstaendig." "ERROR"
        if ($sourceCheck.Raw) {
            Write-Host $sourceCheck.Raw
        }
        exit $sourceCheck.ExitCode
    }
    Write-Log "Quellmodul-Runtime erfolgreich validiert."

    if ($CheckOnly) {
        if ($sourceCheck.Raw) {
            Write-Host $sourceCheck.Raw
        }
        exit 0
    }

    Ensure-AppHomeLayout
    New-InstallStage

    foreach ($relativePath in @(
        "validator_vision",
        "runtime",
        "config",
        "tools",
        "module-manifest.json",
        "README.md",
        "installer.bat",
        "check-runtime.bat",
        "build-runtime.bat"
    )) {
        Copy-ProjectItem -RelativePath $relativePath
    }

    $installedCheck = Publish-StagedInstall

    Write-Log "Installation erfolgreich abgeschlossen."
    [PSCustomObject]@{
        ok = $true
        source_root = $script:ProjectRoot
        install_root = $script:InstallRoot
        app_home = $script:AppHome
        log_file = $script:LogFile
        runtime = $installedCheck.Status
    } | ConvertTo-Json -Depth 8
} catch {
    Write-Log $_.Exception.Message "ERROR"
    throw
}
