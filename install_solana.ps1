# Install Solana CLI on Windows
Write-Host "Installing Solana CLI for Windows..." -ForegroundColor Green

# Check if winget is available
$wingetAvailable = Get-Command winget -ErrorAction SilentlyContinue
if ($wingetAvailable) {
    Write-Host "Installing Solana CLI via winget..." -ForegroundColor Yellow
    winget install --id Solana.SolanaCLI --accept-source-agreements --accept-package-agreements
} else {
    Write-Host "winget not available. Please install Solana CLI manually:" -ForegroundColor Red
    Write-Host "Download from: https://github.com/solana-labs/solana/releases/latest" -ForegroundColor Cyan
    Write-Host "Select the Windows installer (.msi)" -ForegroundColor Cyan
    exit 1
}

# Add to PATH for current session
Write-Host "Adding Solana to PATH..." -ForegroundColor Yellow
$solanaPath = "$env:USERPROFILE\.local\share\solana\install\active_release\bin"
if (Test-Path $solanaPath) {
    $env:Path += ";$solanaPath"
    Write-Host "Solana CLI installed successfully!" -ForegroundColor Green
    Write-Host "Please restart your terminal and run the wallet setup again:" -ForegroundColor Cyan
    Write-Host "   python setup_beta_wallet.py" -ForegroundColor White
} else {
    Write-Host "Solana installed but path not found. You may need to restart your terminal." -ForegroundColor Yellow
}

Write-Host "After installation, verify with: solana --version" -ForegroundColor Cyan
