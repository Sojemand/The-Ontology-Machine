from __future__ import annotations

UNINSTALL_POWERSHELL = """param(
  [Parameter(Mandatory = $true)]
  [string]$InstallRoot,
  [switch]$SkipInno,
  [switch]$AssumeYes,
  [switch]$KeepAppData,
  [switch]$NoPause
)

$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
  Write-Host "[Ontology Machine Uninstall] $Message"
}

function Normalize-Path([string]$PathValue) {
  $cleanPath = ([string]$PathValue).Trim().Trim([char[]]@('"', "'"))
  return ([System.IO.Path]::GetFullPath($cleanPath)).TrimEnd([char[]]@("\\", "/"))
}

function Assert-SafeInstallRoot([string]$Root) {
  $driveRoot = ([System.IO.Path]::GetPathRoot($Root)).TrimEnd([char[]]@("\\", "/"))
  $dangerousRoots = @(
    $driveRoot,
    $env:USERPROFILE,
    $env:LOCALAPPDATA,
    $env:APPDATA,
    $env:ProgramFiles,
    ${env:ProgramFiles(x86)}
  ) | Where-Object { $_ } | ForEach-Object { Normalize-Path $_ }

  $normalizedRoot = Normalize-Path $Root
  foreach ($dangerousRoot in $dangerousRoots) {
    if ($normalizedRoot.Equals($dangerousRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
      throw "Refusing to uninstall dangerous root path: $Root"
    }
  }

  if (-not (Test-Path -LiteralPath $Root)) {
    throw "Refusing to uninstall: install root does not exist: $Root"
  }

  $requiredMarkers = @(
    "release-manifest.json",
    "00 - Orchestrator",
    "Client Frontend",
    "07 - MCP Server",
    "08 - Semantic Control Kernel"
  )
  $missing = @()
  foreach ($marker in $requiredMarkers) {
    if (-not (Test-Path -LiteralPath (Join-Path $Root $marker))) {
      $missing += $marker
    }
  }
  if ($missing.Count -eq 0) {
    return
  }

  $knownResidualNames = @(
    "00 - Orchestrator",
    "01 - Optimizer",
    "02 - Interpreter",
    "03 - Validator",
    "04 - Normalizer",
    "05 - Corpus Builder",
    "06 - Edit Suite",
    "07 - MCP Server",
    "08 - Semantic Control Kernel",
    "Client Frontend",
    "Extractor_Tools",
    "SampleDB",
    "icons"
  )
  $knownResidualFiles = @(
    "Check All Runtimes.bat",
    "Configure Client Frontend.bat",
    "README.txt",
    "Start Article Archive Extractor.bat",
    "Start Audio Transcription Extractor.bat",
    "Start Client Frontend.bat",
    "Start Orchestrator.bat",
    "Start YouTube Transcript Extractor.bat",
    "Uninstall Ontology Machine.bat",
    "Uninstall Ontology Machine.ps1",
    "release-manifest.json"
  )
  $unknown = @()
  $knownCount = 0
  Get-ChildItem -LiteralPath $Root -Force -ErrorAction Stop | ForEach-Object {
    if ($_.PSIsContainer) {
      if ($knownResidualNames -contains $_.Name) {
        $knownCount += 1
      } else {
        $unknown += $_.Name
      }
    } elseif (($knownResidualFiles -contains $_.Name) -or ($_.Name -like "unins*")) {
      $knownCount += 1
    } else {
      $unknown += $_.Name
    }
  }
  if ($unknown.Count -gt 0) {
    throw "Refusing to uninstall: install root marker(s) missing and unknown top-level item(s) exist under '$Root': $($unknown -join ', ')"
  }
  if ($knownCount -eq 0) {
    throw "Refusing to uninstall: install root marker(s) missing and no Ontology Machine residual items were found under '$Root'."
  }
  Write-Step "Full install markers are missing; treating '$Root' as post-uninstall residual cleanup."
}

function Confirm-Uninstall([string]$Root, [bool]$DeleteAppData) {
  if ($AssumeYes) {
    return
  }
  Write-Host ""
  Write-Host "This will stop Ontology Machine processes and delete:"
  Write-Host "  $Root"
  if ($DeleteAppData) {
    Write-Host "  $env:LOCALAPPDATA\\Enterprise Stack\\Client Frontend"
  }
  Write-Host ""
  $answer = Read-Host "Type DELETE to continue"
  if ($answer -ne "DELETE") {
    throw "Uninstall cancelled."
  }
}

function Stop-InstallProcesses([string]$Root) {
  $rootPrefix = (Normalize-Path $Root) + "\\"
  Write-Step "Stopping running processes from install root..."
  try {
    $processes = Get-CimInstance Win32_Process | Where-Object {
      $processId = [int]$_.ProcessId
      if ($processId -eq $PID) {
        return $false
      }
      $exe = [string]$_.ExecutablePath
      $cmd = [string]$_.CommandLine
      $exeMatches = $exe -and $exe.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)
      $cmdMatches = $cmd -and ($cmd.IndexOf($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase) -ge 0)
      return $exeMatches -or $cmdMatches
    }
  } catch {
    Write-Warning "Could not enumerate processes: $($_.Exception.Message)"
    return
  }

  foreach ($process in $processes) {
    try {
      Write-Step "Stopping PID $($process.ProcessId): $($process.Name)"
      Stop-Process -Id $process.ProcessId -Force -ErrorAction Stop
    } catch {
      Write-Warning "Could not stop PID $($process.ProcessId): $($_.Exception.Message)"
    }
  }
}

function Invoke-InnoUninstaller([string]$Root) {
  if ($SkipInno) {
    return
  }
  $uninstaller = Get-ChildItem -LiteralPath $Root -Filter "unins*.exe" -File -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
  if (-not $uninstaller) {
    Write-Step "No Inno uninstaller found; continuing with direct cleanup."
    return
  }

  Write-Step "Running registered uninstaller: $($uninstaller.Name)"
  try {
    $process = Start-Process -FilePath $uninstaller.FullName -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART" -WorkingDirectory $Root -Wait -PassThru
    Write-Step "Registered uninstaller exited with code $($process.ExitCode)."
  } catch {
    Write-Warning "Registered uninstaller failed: $($_.Exception.Message)"
  }
}

function Remove-TreeWithRetry([string]$PathValue) {
  if (-not (Test-Path -LiteralPath $PathValue)) {
    return
  }

  $lastError = ""
  for ($attempt = 1; $attempt -le 8; $attempt++) {
    try {
      Remove-Item -LiteralPath $PathValue -Recurse -Force -ErrorAction Stop
      if (-not (Test-Path -LiteralPath $PathValue)) {
        Write-Step "Deleted: $PathValue"
        return
      }
    } catch {
      $lastError = $_.Exception.Message
      Start-Sleep -Milliseconds (250 * $attempt)
    }
  }
  Write-Warning "Could not delete '$PathValue': $lastError"
}

function Remove-Shortcuts {
  $startMenuDir = Join-Path $env:APPDATA "Microsoft\\Windows\\Start Menu\\Programs\\Ontology Machine"
  Remove-TreeWithRetry $startMenuDir
  Remove-TreeWithRetry (Join-Path $env:USERPROFILE "Desktop\\Ontology Machine")
  if ($env:PUBLIC) {
    Remove-TreeWithRetry (Join-Path $env:PUBLIC "Desktop\\Ontology Machine")
  }

  $desktopFiles = @(
    (Join-Path $env:USERPROFILE "Desktop\\Ontology Machine Orchestrator.lnk"),
    (Join-Path $env:USERPROFILE "Desktop\\Ontology Machine Client Frontend.lnk"),
    (Join-Path $env:USERPROFILE "Desktop\\Ontology Machine Config.lnk")
  )
  if ($env:PUBLIC) {
    $desktopFiles += @(
      (Join-Path $env:PUBLIC "Desktop\\Ontology Machine Orchestrator.lnk"),
      (Join-Path $env:PUBLIC "Desktop\\Ontology Machine Client Frontend.lnk"),
      (Join-Path $env:PUBLIC "Desktop\\Ontology Machine Config.lnk")
    )
  }
  foreach ($file in $desktopFiles) {
    if (Test-Path -LiteralPath $file) {
      Remove-Item -LiteralPath $file -Force -ErrorAction SilentlyContinue
    }
  }
}

function Remove-UninstallRegistryEntries([string]$Root) {
  $registryRoots = @(
    "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall",
    "HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall"
  )
  foreach ($registryRoot in $registryRoots) {
    if (-not (Test-Path $registryRoot)) {
      continue
    }
    try {
      Get-ChildItem $registryRoot -ErrorAction Stop | ForEach-Object {
        try {
          $props = Get-ItemProperty -LiteralPath $_.PSPath -ErrorAction Stop
          $displayName = [string]$props.DisplayName
          $installLocation = [string]$props.InstallLocation
          $uninstallString = [string]$props.UninstallString
          $matchesName = $displayName -eq "Ontology Machine"
          $matchesRoot = ($installLocation -and (Normalize-Path $installLocation).Equals((Normalize-Path $Root), [System.StringComparison]::OrdinalIgnoreCase)) -or
            ($uninstallString -and ($uninstallString.IndexOf($Root, [System.StringComparison]::OrdinalIgnoreCase) -ge 0))
          if ($matchesName -or $matchesRoot) {
            Remove-Item -LiteralPath $_.PSPath -Recurse -Force -ErrorAction Stop
          }
        } catch {}
      }
    } catch {}
  }
}

try {
  $root = Normalize-Path $InstallRoot
  Assert-SafeInstallRoot $root
  $deleteAppData = -not $KeepAppData
  Confirm-Uninstall $root $deleteAppData

  Stop-InstallProcesses $root
  Invoke-InnoUninstaller $root
  Stop-InstallProcesses $root
  Remove-Shortcuts

  if ($deleteAppData -and $env:LOCALAPPDATA) {
    Remove-TreeWithRetry (Join-Path $env:LOCALAPPDATA "Enterprise Stack\\Client Frontend")
    $enterpriseRoot = Join-Path $env:LOCALAPPDATA "Enterprise Stack"
    if ((Test-Path -LiteralPath $enterpriseRoot) -and -not (Get-ChildItem -LiteralPath $enterpriseRoot -Force -ErrorAction SilentlyContinue)) {
      Remove-Item -LiteralPath $enterpriseRoot -Force -ErrorAction SilentlyContinue
    }
  }

  Remove-UninstallRegistryEntries $root
  Remove-TreeWithRetry $root
  Write-Step "Done."
} catch {
  Write-Host ""
  Write-Host "Uninstall failed: $($_.Exception.Message)" -ForegroundColor Red
  exit 1
} finally {
  if (-not $NoPause) {
    Write-Host ""
    Read-Host "Press Enter to close"
  }
}
"""
