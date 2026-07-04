# Jarvis Workbench Stop Script for Windows
param(
    [int]$Port = 8080
)

$ErrorActionPreference = "Continue"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$LogDir = Join-Path $RootDir "logs"
$PidFile = Join-Path $LogDir "workbench.pid"

if (Test-Path $PidFile) {
    $pidFromFile = Get-Content $PidFile -ErrorAction SilentlyContinue
    if ($pidFromFile) {
        $process = Get-Process -Id $pidFromFile -ErrorAction SilentlyContinue
        if ($process) {
            Write-Host "Stopping Jarvis workbench (PID: $pidFromFile)..."
            Stop-Process -Id $pidFromFile -Force
            Start-Sleep -Milliseconds 500
        }
        Remove-Item $PidFile -ErrorAction SilentlyContinue
        Write-Host "Jarvis workbench stopped."
        exit 0
    }
}

$connections = netstat -ano | Select-String ":$Port\s+LISTENING"
if ($connections) {
    $pid = ($connections -split '\s+')[-1]
    Write-Host "Process listening on port $Port: $pid"
    Write-Host "Stopping it now."
    Stop-Process -Id $pid -Force
    Write-Host "Jarvis workbench stopped."
} else {
    Write-Host "No Jarvis workbench process found on port $Port."
}
