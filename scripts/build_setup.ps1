param(
    [string]$AppVersion = "1.0.0",
    [string]$IsccPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

$distExe = Join-Path $repoRoot "dist\\pyStudyFlash\\pyStudyFlash.exe"
if (-not (Test-Path $distExe)) {
    throw "Distribution is missing. Run scripts\\build_dist.ps1 first."
}

if (-not $IsccPath) {
    $candidates = @(
        "${env:ProgramFiles(x86)}\\Inno Setup 6\\ISCC.exe",
        "$env:ProgramFiles\\Inno Setup 6\\ISCC.exe"
    )
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            $IsccPath = $candidate
            break
        }
    }
}

if (-not $IsccPath) {
    throw "ISCC.exe not found. Install Inno Setup 6 or pass -IsccPath."
}

& $IsccPath "/DMyAppVersion=$AppVersion" "installer\\pystudyflash.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup build failed" }

Write-Host "Installer created in installer\\output\\"
