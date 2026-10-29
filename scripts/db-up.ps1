# scripts/db-up.ps1
# Helper script to reliably start local PostgreSQL (WSL pgvector) for Festiva

Write-Host "==> Checking Festiva PostgreSQL status on 127.0.0.1:5432..." -ForegroundColor Cyan

$portActive = $false
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $iar = $tcp.BeginConnect("127.0.0.1", 5432, $null, $null)
    $success = $iar.AsyncWaitHandle.WaitOne(1000, $false)
    if ($success -and $tcp.Connected) {
        $portActive = $true
        $tcp.EndConnect($iar)
    }
    $tcp.Close()
} catch {
    $portActive = $false
}

if ($portActive) {
    Write-Host "[OK] PostgreSQL is already running and listening on 127.0.0.1:5432." -ForegroundColor Green
    exit 0
}

Write-Host "PostgreSQL is not responding on 127.0.0.1:5432. Launching PostgreSQL via WSL..." -ForegroundColor Yellow

# Start postgres in WSL background service
wsl -u root /etc/init.d/postgresql start

# Poll for up to 10 seconds
$maxRetries = 10
$retryCount = 0
while ($retryCount -lt $maxRetries) {
    Start-Sleep -Seconds 1
    $retryCount++
    try {
        $tcp = New-Object System.Net.Sockets.TcpClient
        $iar = $tcp.BeginConnect("127.0.0.1", 5432, $null, $null)
        $ready = $iar.AsyncWaitHandle.WaitOne(1000, $false)
        if ($ready -and $tcp.Connected) {
            $tcp.EndConnect($iar)
            $tcp.Close()
            Write-Host "[OK] PostgreSQL successfully started and listening on 127.0.0.1:5432." -ForegroundColor Green
            exit 0
        }
        $tcp.Close()
    } catch {
        # continue waiting
    }
    Write-Host "Waiting for database to become ready ($retryCount/$maxRetries)..."
}

Write-Error "PostgreSQL failed to respond on 127.0.0.1:5432 after $maxRetries seconds. Please check WSL postgres installation."
exit 1
