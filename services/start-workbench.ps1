# Jarvis Workbench Start Script for Windows
param(
    [int]$Port = 8080
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$BackendEntry = Join-Path $RootDir "backend\main.py"
$LogDir = Join-Path $RootDir "logs"
$PidFile = Join-Path $LogDir "workbench.pid"
$EnvFile = Join-Path $RootDir ".env"

if (-not (Test-Path $BackendEntry)) {
    Write-Error "Backend entry not found: $BackendEntry"
    exit 1
}

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}

$env:JARVIS_ROOT = $RootDir

$connections = netstat -ano | Select-String ":$Port\s+LISTENING"
if ($connections) {
    $existingPid = ($connections -split '\s+')[-1]
    Write-Host "Port $Port is already in use by PID: $existingPid"
    Write-Host "If this is Jarvis, run: .\stop-workbench.ps1"
    exit 1
}

Write-Host "Starting Jarvis workbench at http://127.0.0.1:$Port/"

$stdoutLog = Join-Path $LogDir "workbench.out.log"
$stderrLog = Join-Path $LogDir "workbench.err.log"

$process = Start-Process -FilePath "python" -ArgumentList $BackendEntry `
    -WorkingDirectory $RootDir `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog `
    -PassThru -NoNewWindow

$process.Id | Out-File -FilePath $PidFile -Encoding ascii
Write-Host "Jarvis workbench started with PID: $($process.Id)"

$ready = $false
for ($i = 0; $i -lt 10; $i++) {
    Start-Sleep -Seconds 1
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/" -UseBasicParsing -TimeoutSec 2
        if ($response.StatusCode -eq 200) {
            $ready = $true
            break
        }
    } catch {
    }
}

if ($ready) {
    Write-Host "Jarvis workbench is ready: http://127.0.0.1:$Port/"
} else {
    Write-Host "Jarvis workbench did not become ready in time."
    Write-Host "See logs:"
    Write-Host "  $stdoutLog"
    Write-Host "  $stderrLog"
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    Remove-Item $PidFile -ErrorAction SilentlyContinue
    exit 1
}
