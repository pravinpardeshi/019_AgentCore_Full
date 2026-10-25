# build_agentcore_package.ps1
# Builds dist/agentcore_deployment.zip for AgentCore Runtime "S3" source
# Mimics the logic from build_deploy_package.sh for Windows environments

$ErrorActionPreference = "Stop"

# --- Configuration ---
$PyVer = "3.12"
$BuildDir = "build"
$StageDir = "build/stage"
$WheelsDir = "build/wheels"
$OutDir = "dist"
$OutFile = "dist/agentcore_deployment.zip"

# Cleanup and setup
if (Test-Path $BuildDir) { Remove-Item -Recurse -Force $BuildDir }
if (Test-Path $OutDir) { Remove-Item -Recurse -Force $OutDir }
New-Item -ItemType Directory -Path $WheelsDir -Force | Out-Null
New-Item -ItemType Directory -Path $StageDir -Force | Out-Null
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null

Write-Host "==> Downloading linux/arm64 wheels for Python $PyVer..." -ForegroundColor Cyan
# Use pip download to fetch wheels for the target platform (Linux ARM64)
pip download --quiet --only-binary=:all: `
    --python-version $PyVer --implementation cp `
    --platform manylinux2014_aarch64 --platform manylinux_2_17_aarch64 `
    --platform manylinux_2_28_aarch64 --platform linux_aarch64 `
    --platform any `
    -r requirements.txt -d $WheelsDir

$wheelCount = (Get-ChildItem $WheelsDir).Count
Write-Host "    $wheelCount wheels downloaded."

Write-Host "==> Unpacking wheels into staging root..." -ForegroundColor Cyan
$wheels = Get-ChildItem "$WheelsDir/*.whl"
foreach ($wheel in $wheels) {
    # Use python's zipfile module to extract wheels as it's cross-platform
    python -m zipfile -e $wheel.FullName $StageDir
}

Write-Host "==> Bundling application code..." -ForegroundColor Cyan
# Create the main.py entry point
$mainContent = @"
import uvicorn

if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8080, log_level="info")
"@
$mainContent | Out-File -FilePath "$StageDir/main.py" -Encoding utf8

# Copy project folders
foreach ($folder in @("src", "config", "templates", "static")) {
    if (Test-Path $folder) {
        Copy-Item -Path $folder -Destination $StageDir -Recurse -Force
    }
}
Copy-Item -Path "requirements.txt" -Destination $StageDir -Force

# Remove caches and pyc files
Get-ChildItem -Path $StageDir -Include "__pycache__" -Recurse | Remove-Item -Recurse -Force
Get-ChildItem -Path $StageDir -Include "*.pyc" -Recurse | Remove-Item -Force

Write-Host "==> Creating $OutFile..." -ForegroundColor Cyan
# Using Compress-Archive for the zip file
# Note: We enter the directory to ensure the zip root is the content, not the folder
Push-Location $StageDir
Compress-Archive -Path * -DestinationPath "..\..\$OutFile" -Force
Pop-Location

$fileSize = (Get-Item $OutFile).Length / 1KB
Write-Host "==> Done: $OutFile ($([Math]::Round($fileSize, 2)) KB)" -ForegroundColor Green
Write-Host "==> Entry point: python main.py (HTTP, port 8080)"
