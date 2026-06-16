param(
  [string]$BundlePath = "",
  [switch]$Force
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

function Write-Step([string]$Message) {
  Write-Host "[hydrate] $Message"
}

function Resolve-RepoRoot {
  $scriptRoot = Split-Path -Parent $PSCommandPath
  return (Resolve-Path -LiteralPath (Join-Path $scriptRoot "..")).Path
}

function Resolve-BundlePath([string]$RepoRoot, [string]$ExplicitPath) {
  if ($ExplicitPath.Trim()) {
    $candidate = Resolve-Path -LiteralPath $ExplicitPath -ErrorAction Stop
    return $candidate.Path
  }

  $assetDir = Join-Path $RepoRoot "release-assets"
  if (-not (Test-Path -LiteralPath $assetDir -PathType Container)) {
    New-Item -ItemType Directory -Force -Path $assetDir | Out-Null
  }

  $candidates = Get-ChildItem -LiteralPath $assetDir -Filter "OntologyMachine-RuntimeBundle*.zip" -File |
    Sort-Object LastWriteTimeUtc -Descending

  if (-not $candidates) {
    throw "No runtime bundle found in $assetDir. Put the runtime bundle release asset there or pass -BundlePath <zip>."
  }

  return $candidates[0].FullName
}

function Test-ZipHasEntry([string]$ZipPath, [string]$EntryName) {
  $archive = [System.IO.Compression.ZipFile]::OpenRead($ZipPath)
  try {
    $normalized = $EntryName.Replace("\", "/")
    foreach ($entry in $archive.Entries) {
      if ($entry.FullName -eq $normalized) {
        return $true
      }
    }
    return $false
  } finally {
    $archive.Dispose()
  }
}

function Assert-InsideRepo([string]$RepoRoot, [string]$Path) {
  $root = [System.IO.Path]::GetFullPath($RepoRoot).TrimEnd('\') + '\'
  $target = [System.IO.Path]::GetFullPath($Path)
  if (-not $target.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to write outside repository root: $target"
  }
}

function Assert-RequiredPaths([string]$RepoRoot) {
  $required = @(
    "00 - Orchestrator\runtime\python\python.exe",
    "01 - Optimizer\runtime\python\python.exe",
    "02 - Interpreter\runtime\python\python.exe",
    "03 - Validator\runtime\python\python.exe",
    "04 - Normalizer\runtime\python\python.exe",
    "05 - Corpus Builder\runtime\python\python.exe",
    "06 - Edit Suite\runtime\python\python.exe",
    "07 - MCP Server\runtime\python\python.exe",
    "08 - Semantic Control Kernel\runtime\python\python.exe",
    "Client Frontend\node\node.exe",
    "Client Frontend\app\index.html",
    "Client Frontend\runtime\python\python.exe",
    "Client Frontend\runtime\powershell\powershell.exe"
  )

  $missing = @()
  foreach ($relative in $required) {
    $path = Join-Path $RepoRoot $relative
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
      $missing += $relative
    }
  }

  if ($missing.Count -gt 0) {
    throw "Hydration incomplete. Missing required runtime files:`n - $($missing -join "`n - ")"
  }
}

$repoRoot = Resolve-RepoRoot
$bundle = Resolve-BundlePath $repoRoot $BundlePath
$bundleFull = [System.IO.Path]::GetFullPath($bundle)

Write-Step "Repository root: $repoRoot"
Write-Step "Runtime bundle: $bundleFull"

$requiredZipEntries = @(
  "00 - Orchestrator/runtime/python/python.exe",
  "01 - Optimizer/runtime/python/python.exe",
  "02 - Interpreter/runtime/python/python.exe",
  "03 - Validator/runtime/python/python.exe",
  "04 - Normalizer/runtime/python/python.exe",
  "05 - Corpus Builder/runtime/python/python.exe",
  "06 - Edit Suite/runtime/python/python.exe",
  "07 - MCP Server/runtime/python/python.exe",
  "08 - Semantic Control Kernel/runtime/python/python.exe",
  "Client Frontend/node/node.exe",
  "Client Frontend/app/index.html",
  "Client Frontend/runtime/python/python.exe",
  "Client Frontend/runtime/powershell/powershell.exe"
)

foreach ($entry in $requiredZipEntries) {
  if (-not (Test-ZipHasEntry $bundleFull $entry)) {
    throw "Runtime bundle is missing required entry: $entry"
  }
}

Assert-InsideRepo $repoRoot (Join-Path $repoRoot "Client Frontend")

if (-not $Force) {
  Write-Step "Extracting runtime payloads. Existing generated runtime files may be overwritten. Use -Force to suppress this message in automation."
}

Expand-Archive -LiteralPath $bundleFull -DestinationPath $repoRoot -Force
Assert-RequiredPaths $repoRoot

Write-Step "Hydration complete."
Write-Step "You can now run: .\build-all-in-one-installer.bat --skip-runtime-build --compile"
