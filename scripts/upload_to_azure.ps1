# Upload large data files to Azure Blob Storage
# Run this to sync data files to Azure

$azureBase = "\\tradingsystem12345.file.core.windows.net\csv-exchange"
$localBase = "C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System"

Write-Host "=== AI Trading System - Azure Data Upload ===" -ForegroundColor Cyan
Write-Host "This script uploads large data files to Azure Blob Storage"
Write-Host ""

# Create folder structure in Azure
$azureFolders = @(
    "training",
    "logs",
    "logs\predictions",
    "logs\by_date",
    "logs\by_version"
)

Write-Host "Creating Azure folder structure..." -ForegroundColor Yellow
foreach ($folder in $azureFolders) {
    $path = Join-Path $azureBase $folder
    if (-not (Test-Path $path)) {
        New-Item -Path $path -ItemType Directory -Force | Out-Null
        Write-Host "  Created: $folder"
    }
}

# Upload training data
Write-Host "`n=== Uploading Training Data ===" -ForegroundColor Cyan
$trainingFiles = @(
    "train_data.csv",
    "val_data.csv",
    "test_data.csv"
)

foreach ($file in $trainingFiles) {
    $src = Join-Path $localBase $file
    $dst = Join-Path $azureBase "training\$file"
    if (Test-Path $src) {
        $size = [math]::Round((Get-Item $src).Length / 1MB, 0)
        Write-Host "  Uploading: $file ($size MB)..." -NoNewline
        Copy-Item $src $dst -Force
        Write-Host " Done" -ForegroundColor Green
    }
}

# Upload log files
Write-Host "`n=== Uploading Execution Logs ===" -ForegroundColor Cyan
$logFiles = @(
    "logs\predictions_v6_demo.csv",
    "logs\trades_v3_B1_demo.csv",
    "logs\expanded_features_v6_demo.csv",
    "logs\system_v6_demo.log"
)

foreach ($file in $logFiles) {
    $src = Join-Path $localBase $file
    $dst = Join-Path $azureBase $file
    if (Test-Path $src) {
        $size = [math]::Round((Get-Item $src).Length / 1MB, 0)
        Write-Host "  Uploading: $file ($size MB)..." -NoNewline
        Copy-Item $src $dst -Force
        Write-Host " Done" -ForegroundColor Green
    }
}

Write-Host "`n=== Upload Complete! ===" -ForegroundColor Green
