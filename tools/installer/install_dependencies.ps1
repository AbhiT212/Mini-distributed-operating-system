# MiniDOS Dependency Installer
# Requires Administrator Privileges

param(
    [switch]$SkipPython = $false,
    [switch]$SkipFirewall = $false
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MiniDOS Installation Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "ERROR: This script requires Administrator privileges!" -ForegroundColor Red
    Write-Host "Please right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] Running with Administrator privileges" -ForegroundColor Green

# Check Python installation
Write-Host ""
Write-Host "Checking Python installation..." -ForegroundColor Yellow

$pythonInstalled = $false
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python (\d+)\.(\d+)") {
        $major = [int]$matches[1]
        $minor = [int]$matches[2]
        
        if ($major -ge 3 -and $minor -ge 10) {
            Write-Host "[OK] Python $major.$minor is installed" -ForegroundColor Green
            $pythonInstalled = $true
        } else {
            Write-Host "[WARNING] Python $major.$minor found, but 3.10+ is required" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "[INFO] Python not found in PATH" -ForegroundColor Yellow
}

if (-not $pythonInstalled -and -not $SkipPython) {
    Write-Host ""
    Write-Host "Python 3.10+ is required but not found." -ForegroundColor Red
    Write-Host "Please install Python from: https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "Make sure to check 'Add Python to PATH' during installation" -ForegroundColor Yellow
    Write-Host ""
    $install = Read-Host "Do you want to open the Python download page? (Y/N)"
    if ($install -eq "Y" -or $install -eq "y") {
        Start-Process "https://www.python.org/downloads/"
    }
    exit 1
}

# Install Python dependencies
Write-Host ""
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow

$packages = @("pyyaml", "psutil", "colorama")

foreach ($package in $packages) {
    Write-Host "  Installing $package..." -ForegroundColor Cyan
    try {
        python -m pip install $package --quiet --disable-pip-version-check
        Write-Host "  [OK] $package installed" -ForegroundColor Green
    } catch {
        Write-Host "  [ERROR] Failed to install $package" -ForegroundColor Red
    }
}

# Create MiniDOS filesystem directory
Write-Host ""
Write-Host "Setting up MiniDOS filesystem..." -ForegroundColor Yellow

$miniDOSPath = "C:\MiniDOS_FS"

if (-not (Test-Path $miniDOSPath)) {
    New-Item -Path $miniDOSPath -ItemType Directory -Force | Out-Null
    Write-Host "[OK] Created directory: $miniDOSPath" -ForegroundColor Green
} else {
    Write-Host "[OK] Directory already exists: $miniDOSPath" -ForegroundColor Green
}

# Set permissions on MiniDOS directory
Write-Host "Setting permissions..." -ForegroundColor Yellow
try {
    icacls $miniDOSPath /grant "Everyone:(OI)(CI)F" /T | Out-Null
    Write-Host "[OK] Permissions set on $miniDOSPath" -ForegroundColor Green
} catch {
    Write-Host "[WARNING] Failed to set permissions: $_" -ForegroundColor Yellow
}

# Create logs directory
$logsPath = Join-Path $PSScriptRoot "..\..\logs"
if (-not (Test-Path $logsPath)) {
    New-Item -Path $logsPath -ItemType Directory -Force | Out-Null
    Write-Host "[OK] Created logs directory" -ForegroundColor Green
}

# Configure firewall rules
if (-not $SkipFirewall) {
    Write-Host ""
    Write-Host "Configuring Windows Firewall..." -ForegroundColor Yellow
    
    # Check if rules already exist
    $tcpRuleExists = Get-NetFirewallRule -DisplayName "MiniDOS TCP" -ErrorAction SilentlyContinue
    $udpRuleExists = Get-NetFirewallRule -DisplayName "MiniDOS UDP" -ErrorAction SilentlyContinue
    
    # TCP Rule
    if (-not $tcpRuleExists) {
        try {
            New-NetFirewallRule -DisplayName "MiniDOS TCP" `
                -Direction Inbound `
                -Protocol TCP `
                -LocalPort 9000-9010 `
                -Action Allow `
                -Profile Any `
                -ErrorAction Stop | Out-Null
            Write-Host "[OK] Created TCP firewall rule (ports 9000-9010)" -ForegroundColor Green
        } catch {
            Write-Host "[ERROR] Failed to create TCP firewall rule: $_" -ForegroundColor Red
        }
    } else {
        Write-Host "[OK] TCP firewall rule already exists" -ForegroundColor Green
    }
    
    # UDP Rule
    if (-not $udpRuleExists) {
        try {
            New-NetFirewallRule -DisplayName "MiniDOS UDP" `
                -Direction Inbound `
                -Protocol UDP `
                -LocalPort 9050 `
                -Action Allow `
                -Profile Any `
                -ErrorAction Stop | Out-Null
            Write-Host "[OK] Created UDP firewall rule (port 9050)" -ForegroundColor Green
        } catch {
            Write-Host "[ERROR] Failed to create UDP firewall rule: $_" -ForegroundColor Red
        }
    } else {
        Write-Host "[OK] UDP firewall rule already exists" -ForegroundColor Green
    }
}

# Verify installation
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Verifying Installation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$allGood = $true

# Check Python
try {
    python --version | Out-Null
    Write-Host "[OK] Python is accessible" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python is not accessible" -ForegroundColor Red
    $allGood = $false
}

# Check packages
foreach ($package in $packages) {
    try {
        python -c "import $($package.Replace('-', '_'))" 2>$null
        Write-Host "[OK] Package $package is available" -ForegroundColor Green
    } catch {
        Write-Host "[ERROR] Package $package is not available" -ForegroundColor Red
        $allGood = $false
    }
}

# Check filesystem
if (Test-Path $miniDOSPath) {
    Write-Host "[OK] Filesystem directory exists" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Filesystem directory not found" -ForegroundColor Red
    $allGood = $false
}

# Check firewall
if (-not $SkipFirewall) {
    if (Get-NetFirewallRule -DisplayName "MiniDOS TCP" -ErrorAction SilentlyContinue) {
        Write-Host "[OK] Firewall rules configured" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] Firewall rules not found" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan

if ($allGood) {
    Write-Host "  Installation Complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Edit configs\default.yaml to set your node name" -ForegroundColor White
    Write-Host "  2. Run: .\scripts\start_node.bat" -ForegroundColor White
    Write-Host "  3. Launch CLI: .\scripts\debug_shell.bat" -ForegroundColor White
} else {
    Write-Host "  Installation completed with errors" -ForegroundColor Yellow
    Write-Host "  Please review the errors above" -ForegroundColor Yellow
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

