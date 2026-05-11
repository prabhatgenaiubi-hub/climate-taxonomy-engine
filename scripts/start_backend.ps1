# Start FastAPI backend (port 8000)
# Run from project root: D:\Prabhat\climate-taxonomy-engine
#
#   PowerShell:  .\scripts\start_backend.ps1
#   Or manually: uvicorn backend.api.main:app --reload --port 8000

$PYTHON = "C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe"
$PROJECT_ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent

Set-Location $PROJECT_ROOT
Write-Host "Starting FastAPI backend on http://localhost:8000 ..." -ForegroundColor Cyan
& $PYTHON -m uvicorn backend.api.main:app --reload --port 8000
