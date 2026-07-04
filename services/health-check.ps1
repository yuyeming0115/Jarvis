# Jarvis Workbench Health Check Script for Windows
param(
    [int]$Port = 8080
)

$url = "http://127.0.0.1:$Port/"

try {
    $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Host "Jarvis workbench is online: $url"
        exit 0
    } else {
        Write-Error "Jarvis workbench returned status: $($response.StatusCode)"
        exit 1
    }
} catch {
    Write-Error "Jarvis workbench is not responding: $_"
    exit 1
}
