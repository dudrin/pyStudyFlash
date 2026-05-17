param(
    [string]$PythonExe = "python",
    [string]$AppVersion = "1.0.0",
    [string]$IsccPath = "",
    [switch]$NoClean
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptRoot = $PSScriptRoot

& (Join-Path $scriptRoot "build_dist.ps1") -PythonExe $PythonExe -NoClean:$NoClean
if ($LASTEXITCODE -ne 0) { throw "Distribution build failed" }

& (Join-Path $scriptRoot "build_setup.ps1") -AppVersion $AppVersion -IsccPath $IsccPath
if ($LASTEXITCODE -ne 0) { throw "Installer build failed" }
