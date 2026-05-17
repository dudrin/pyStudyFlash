param(
    [string]$AppVersion = "1.0.0",
    [string]$IsccPath = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

if (-not $IsccPath) {
    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            $IsccPath = $candidate
            break
        }
    }
}

if (-not $IsccPath) {
    throw "ISCC.exe не найден. Установите Inno Setup 6 или передайте -IsccPath."
}

& $IsccPath "/DMyAppVersion=$AppVersion" "installer\pystudyflash-source.iss"
if ($LASTEXITCODE -ne 0) {
    throw "Сборка установщика Inno Setup завершилась ошибкой."
}

Write-Host "Installer created in installer\output\pyStudyFlash-source-setup-$AppVersion.exe"
