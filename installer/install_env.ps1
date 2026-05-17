param(
    [string]$AppDir
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not $AppDir) {
    $AppDir = Split-Path -Parent $MyInvocation.MyCommand.Path
}
$AppDir = (Resolve-Path $AppDir).Path
$VenvDir = Join-Path $AppDir ".venv"
$Requirements = Join-Path $AppDir "requirements.txt"
$Wheelhouse = Join-Path $AppDir "wheelhouse"
$LogFile = Join-Path $AppDir "install-env.log"

foreach ($certEnvName in @("PIP_CERT", "REQUESTS_CA_BUNDLE", "SSL_CERT_FILE", "CURL_CA_BUNDLE")) {
    Remove-Item "Env:$certEnvName" -ErrorAction SilentlyContinue
}
$env:PIP_DISABLE_PIP_VERSION_CHECK = "1"

function Write-InstallLog {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp $Message" | Tee-Object -FilePath $LogFile -Append
}

function Get-PythonExe {
    $commands = @(
        @{ File = "py"; Args = @("-3") },
        @{ File = "python"; Args = @() }
    )

    foreach ($command in $commands) {
        $cmd = Get-Command $command.File -ErrorAction SilentlyContinue
        if (-not $cmd) {
            continue
        }

        try {
            $probe = @"
import sys
if sys.version_info < (3, 8):
    raise SystemExit(2)
print(sys.executable)
"@
            $output = & $command.File @($command.Args) -c $probe 2>$null
            if ($LASTEXITCODE -eq 0 -and $output) {
                return ($output | Select-Object -First 1).Trim()
            }
        } catch {
            continue
        }
    }

    throw "Python 3.8+ не найден. Установите Python с https://www.python.org/downloads/ и повторите установку."
}

Write-InstallLog "Starting environment installation in $AppDir"

if (-not (Test-Path $Requirements)) {
    throw "Файл requirements.txt не найден: $Requirements"
}

$PythonExe = Get-PythonExe
Write-InstallLog "Using Python: $PythonExe"

if (-not (Test-Path $VenvDir)) {
    Write-InstallLog "Creating virtual environment: $VenvDir"
    & $PythonExe -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) {
        throw "Не удалось создать виртуальное окружение."
    }
}

$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    throw "Python виртуального окружения не найден: $VenvPython"
}

Write-InstallLog "Ensuring pip tooling is available"
& $VenvPython -m ensurepip --upgrade
if ($LASTEXITCODE -ne 0) {
    throw "Не удалось подготовить pip."
}

if (Test-Path $Wheelhouse) {
    Write-InstallLog "Installing dependencies from bundled wheelhouse"
    & $VenvPython -m pip install --no-index --find-links $Wheelhouse -r $Requirements
} else {
    Write-InstallLog "Installing dependencies from PyPI"
    & $VenvPython -m pip install -r $Requirements
}
if ($LASTEXITCODE -ne 0) {
    throw "Не удалось установить зависимости из requirements.txt."
}

Write-InstallLog "Compiling Python files"
& $VenvPython -m compileall -q $AppDir

Write-InstallLog "Environment installation completed"
