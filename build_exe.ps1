$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonExe = Join-Path $projectDir "venv\Scripts\python.exe"
$specFile = Join-Path $projectDir "cache_clear.spec"
$releaseDir = Join-Path $projectDir "release"
$workDir = Join-Path $projectDir "build-release"
$releaseExe = Join-Path $releaseDir "cache_clear.exe"
$distDir = Join-Path $projectDir "dist"
$distExe = Join-Path $distDir "cache_clear.exe"

if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw "Virtual environment was not found: $pythonExe"
}

Write-Host "Building Cache Cleaner..." -ForegroundColor Cyan
& $pythonExe -m PyInstaller --clean --noconfirm --distpath $releaseDir --workpath $workDir $specFile
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

if (Get-Process -Name "cache_clear" -ErrorAction SilentlyContinue) {
    Write-Host ""
    Write-Host "Close the running Cache Cleaner. The EXE will update automatically." -ForegroundColor Yellow
    while (Get-Process -Name "cache_clear" -ErrorAction SilentlyContinue) {
        Start-Sleep -Seconds 1
    }
}

New-Item -ItemType Directory -Path $distDir -Force | Out-Null
Copy-Item -LiteralPath $releaseExe -Destination $distExe -Force

Write-Host ""
Write-Host "Done: $distExe" -ForegroundColor Green
