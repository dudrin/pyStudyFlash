param(
    [string]$PythonExe = "python",
    [switch]$NoClean
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

# Some Windows environments set invalid certificate bundle paths for pip.
foreach ($certEnvName in @("PIP_CERT", "REQUESTS_CA_BUNDLE", "SSL_CERT_FILE", "CURL_CA_BUNDLE")) {
    Remove-Item "Env:$certEnvName" -ErrorAction SilentlyContinue
}
$env:PIP_DISABLE_PIP_VERSION_CHECK = "1"

if (-not $NoClean) {
    if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
    if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
}

& $PythonExe -m pip install -r requirements.txt -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw "Failed to install build dependencies" }

& $PythonExe -m PyInstaller --noconfirm --clean pyinstaller.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed" }

Write-Host "Build completed: dist\\pyStudyFlash\\pyStudyFlash.exe"
