# Network Connectivity Checker for MiniDOS

param(
    [string]$RemoteHost = "",
    [int]$Port = 9000
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MiniDOS Network Connectivity Check" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get local network information
Write-Host "Local Network Information:" -ForegroundColor Yellow
Write-Host ""

$adapters = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike "*Loopback*" }

foreach ($adapter in $adapters) {
    Write-Host "  Interface: $($adapter.InterfaceAlias)" -ForegroundColor Cyan
    Write-Host "  IP Address: $($adapter.IPAddress)" -ForegroundColor White
    Write-Host "  Prefix Length: $($adapter.PrefixLength)" -ForegroundColor White
    Write-Host ""
}

# Check if ports are open locally
Write-Host "Checking local ports..." -ForegroundColor Yellow

$tcpPort = 9000
$udpPort = 9050

# Check TCP port
$tcpListener = Get-NetTCPConnection -LocalPort $tcpPort -ErrorAction SilentlyContinue
if ($tcpListener) {
    Write-Host "[OK] TCP port $tcpPort is in use (daemon may be running)" -ForegroundColor Green
} else {
    Write-Host "[INFO] TCP port $tcpPort is available" -ForegroundColor Yellow
}

# Check UDP port
$udpListener = Get-NetUDPEndpoint -LocalPort $udpPort -ErrorAction SilentlyContinue
if ($udpListener) {
    Write-Host "[OK] UDP port $udpPort is in use (discovery may be running)" -ForegroundColor Green
} else {
    Write-Host "[INFO] UDP port $udpPort is available" -ForegroundColor Yellow
}

Write-Host ""

# Check firewall rules
Write-Host "Checking firewall rules..." -ForegroundColor Yellow

$tcpRule = Get-NetFirewallRule -DisplayName "MiniDOS TCP" -ErrorAction SilentlyContinue
$udpRule = Get-NetFirewallRule -DisplayName "MiniDOS UDP" -ErrorAction SilentlyContinue

if ($tcpRule) {
    $enabled = $tcpRule.Enabled
    Write-Host "[OK] MiniDOS TCP rule exists (Enabled: $enabled)" -ForegroundColor Green
} else {
    Write-Host "[WARNING] MiniDOS TCP firewall rule not found" -ForegroundColor Yellow
    Write-Host "  Run install_dependencies.ps1 to create it" -ForegroundColor White
}

if ($udpRule) {
    $enabled = $udpRule.Enabled
    Write-Host "[OK] MiniDOS UDP rule exists (Enabled: $enabled)" -ForegroundColor Green
} else {
    Write-Host "[WARNING] MiniDOS UDP firewall rule not found" -ForegroundColor Yellow
    Write-Host "  Run install_dependencies.ps1 to create it" -ForegroundColor White
}

Write-Host ""

# Test remote connection if specified
if ($RemoteHost -ne "") {
    Write-Host "Testing connection to remote host..." -ForegroundColor Yellow
    Write-Host "  Host: $RemoteHost" -ForegroundColor White
    Write-Host "  Port: $Port" -ForegroundColor White
    Write-Host ""
    
    # Ping test
    Write-Host "Ping test..." -ForegroundColor Cyan
    $pingResult = Test-Connection -ComputerName $RemoteHost -Count 2 -Quiet
    
    if ($pingResult) {
        Write-Host "[OK] Host is reachable via ping" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Host is not reachable via ping" -ForegroundColor Red
    }
    
    # TCP port test
    Write-Host "TCP port test..." -ForegroundColor Cyan
    $tcpTest = Test-NetConnection -ComputerName $RemoteHost -Port $Port -WarningAction SilentlyContinue
    
    if ($tcpTest.TcpTestSucceeded) {
        Write-Host "[OK] TCP port $Port is open and accessible" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] TCP port $Port is not accessible" -ForegroundColor Red
        Write-Host "  Possible causes:" -ForegroundColor Yellow
        Write-Host "    - Remote daemon not running" -ForegroundColor White
        Write-Host "    - Firewall blocking connection" -ForegroundColor White
        Write-Host "    - Incorrect IP address or port" -ForegroundColor White
    }
} else {
    Write-Host "To test remote connection, use:" -ForegroundColor Yellow
    Write-Host "  .\net_check.ps1 -RemoteHost <IP> -Port 9000" -ForegroundColor White
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

