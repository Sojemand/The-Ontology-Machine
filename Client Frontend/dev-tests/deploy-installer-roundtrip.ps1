[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$workspaceRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("vp-deploy-installer-" + [System.Guid]::NewGuid().ToString("N"))
$sourceRoot = Join-Path $workspaceRoot "source"
$deployRoot = Join-Path $workspaceRoot "deploy"
$sourceStateHome = Join-Path $workspaceRoot "source-home"
$targetStateHome = Join-Path $workspaceRoot "target-home"

function Assert-True([bool]$Condition, [string]$Message) {
    if (-not $Condition) {
        throw $Message
    }
}

function Ensure-Dir([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path -Force | Out-Null
    }
}

function Write-Utf8([string]$Path, [string]$Content) {
    Ensure-Dir (Split-Path -Parent $Path)
    [System.IO.File]::WriteAllText($Path, $Content, [System.Text.UTF8Encoding]::new($false))
}

function Copy-ProjectFile([string]$RelativePath, [string]$TargetRoot) {
    $sourcePath = Join-Path $projectRoot $RelativePath
    $targetPath = Join-Path $TargetRoot $RelativePath
    Ensure-Dir (Split-Path -Parent $targetPath)
    Copy-Item -LiteralPath $sourcePath -Destination $targetPath -Force
}

function Copy-ProjectTree([string]$RelativeDir, [string[]]$FileNames, [string]$TargetRoot) {
    foreach ($fileName in $FileNames) {
        Copy-ProjectFile (Join-Path $RelativeDir $fileName) $TargetRoot
    }
}

function Link-OrCopyFile([string]$SourcePath, [string]$TargetPath) {
    Ensure-Dir (Split-Path -Parent $TargetPath)
    try {
        New-Item -ItemType HardLink -Path $TargetPath -Target $SourcePath | Out-Null
    } catch {
        Copy-Item -LiteralPath $SourcePath -Destination $TargetPath -Force
    }
}

function New-MinimalFrontendPayload([string]$Root) {
    foreach ($dir in @("app", "assistant", "client_frontend\runtime_paths", "data", "shared", "node", "runtime\python", "runtime\powershell", "tools", "server")) {
        Ensure-Dir (Join-Path $Root $dir)
    }
    Write-Utf8 (Join-Path $Root "package.json") '{"name":"frontend-fixture","private":true,"type":"module"}'
    Write-Utf8 (Join-Path $Root "README.md") "# fixture"
    Write-Utf8 (Join-Path $Root "README.txt") "fixture"
    Write-Utf8 (Join-Path $Root "requirements.txt") "# fixture"
    foreach ($bat in @("start.bat", "config.bat", "installer.bat", "build-runtime.bat")) {
        Write-Utf8 (Join-Path $Root $bat) "@echo off`r`necho fixture"
    }
    Write-Utf8 (Join-Path $Root "app\index.html") "<html><body>fixture</body></html>"
    Write-Utf8 (Join-Path $Root "app\config.html") "<html><body>fixture</body></html>"
    Write-Utf8 (Join-Path $Root "assistant\soul.txt") "Name: Fixture`nStil: Test"
    Write-Utf8 (Join-Path $Root "data\corpus.db") "must-not-deploy"
    $manifest = @{
        node = @("node/node.exe")
        python = @("runtime/python/python.exe")
        powershell = @("runtime/powershell/pwsh.exe")
    } | ConvertTo-Json -Depth 4
    Write-Utf8 (Join-Path $Root "runtime\runtime-manifest.json") $manifest
    Write-Utf8 (Join-Path $Root "runtime\python\python.exe") ""
    Write-Utf8 (Join-Path $Root "runtime\powershell\pwsh.exe") ""
    Link-OrCopyFile (Join-Path $projectRoot "node\node.exe") (Join-Path $Root "node\node.exe")
    Copy-ProjectFile "tools\check-runtimes.mjs" $Root
    Copy-ProjectFile "tools\clear-stale-server-port.mjs" $Root
    Copy-ProjectFile "tools\deploy.ps1" $Root
    Copy-ProjectFile "tools\installer.ps1" $Root
    Copy-ProjectFile "server\runtime_paths.js" $Root
    Copy-ProjectFile "client_frontend\runtime_paths.js" $Root
    Copy-ProjectTree "client_frontend\runtime_paths" @("adapter.js", "surface.js", "types.js", "validation.js", "workflow.js") $Root
}

try {
    Ensure-Dir $sourceRoot
    Ensure-Dir (Join-Path $sourceStateHome "config")
    Ensure-Dir (Join-Path $sourceStateHome "state")
    New-MinimalFrontendPayload $sourceRoot
    Write-Utf8 (Join-Path $sourceStateHome "config\config.json") '{"customer_name":"Snapshot Customer"}'
    Write-Utf8 (Join-Path $sourceStateHome "config\.salt") "snapshot-salt"
    Write-Utf8 (Join-Path $sourceStateHome "state\chats.db") "chat-db"

    & (Join-Path $sourceRoot "tools\deploy.ps1") -TargetDir $deployRoot -IncludeStateSnapshot -StateHome $sourceStateHome
    Assert-True (Test-Path -LiteralPath (Join-Path $deployRoot "state-snapshot\config\config.json")) "Deploy snapshot config missing."
    Assert-True (Test-Path -LiteralPath (Join-Path $deployRoot "state-snapshot\config\.salt")) "Deploy snapshot salt missing."
    Assert-True (Test-Path -LiteralPath (Join-Path $deployRoot "state-snapshot\state\chats.db")) "Deploy snapshot chats missing."
    Assert-True (Test-Path -LiteralPath (Join-Path $deployRoot "tools\clear-stale-server-port.mjs")) "Deploy port cleaner missing."
    Assert-True (-not (Test-Path -LiteralPath (Join-Path $deployRoot "data"))) "Deploy copied module-root data."

    $oldHome = $env:VISION_PIPELINE_CLIENT_FRONTEND_HOME
    $env:VISION_PIPELINE_CLIENT_FRONTEND_HOME = $targetStateHome
    try {
        & (Join-Path $deployRoot "tools\installer.ps1")
    } finally {
        $env:VISION_PIPELINE_CLIENT_FRONTEND_HOME = $oldHome
    }

    Assert-True (Test-Path -LiteralPath (Join-Path $targetStateHome "app\app\index.html")) "Installed app payload missing."
    Assert-True (Test-Path -LiteralPath (Join-Path $targetStateHome "app\tools\clear-stale-server-port.mjs")) "Installed port cleaner missing."
    Assert-True (-not (Test-Path -LiteralPath (Join-Path $targetStateHome "app\data"))) "Installer copied module-root data."
    Assert-True (Test-Path -LiteralPath (Join-Path $targetStateHome "config\config.json")) "Installed config missing."
    Assert-True (Test-Path -LiteralPath (Join-Path $targetStateHome "config\.salt")) "Installed salt missing."
    Assert-True (Test-Path -LiteralPath (Join-Path $targetStateHome "state\chats.db")) "Installed chats missing."
    $config = Get-Content -LiteralPath (Join-Path $targetStateHome "config\config.json") -Raw | ConvertFrom-Json
    Assert-True ($config.customer_name -eq "Snapshot Customer") "Installed config value mismatch."
    Assert-True ((Get-Content -LiteralPath (Join-Path $targetStateHome "config\.salt") -Raw).Trim() -eq "snapshot-salt") "Installed salt mismatch."
    Assert-True ((Get-Content -LiteralPath (Join-Path $targetStateHome "state\chats.db") -Raw).Trim() -eq "chat-db") "Installed chat DB mismatch."
    Write-Host "[deploy-installer-roundtrip] ok"
} finally {
    if (Test-Path -LiteralPath $workspaceRoot) {
        Remove-Item -LiteralPath $workspaceRoot -Recurse -Force
    }
}
