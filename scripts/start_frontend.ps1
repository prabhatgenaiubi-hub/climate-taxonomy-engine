# Start React frontend dev server (port 5173)
# Run from project root: D:\Prabhat\climate-taxonomy-engine
#
#   PowerShell: .\scripts\start_frontend.ps1
#   Or manually: cd frontend && npm run dev

$PROJECT_ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
$REACT_DIR = Join-Path $PROJECT_ROOT "frontend"

Set-Location $REACT_DIR
Write-Host "Starting React dev server on http://localhost:5173 ..." -ForegroundColor Cyan
npm run dev
