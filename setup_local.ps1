# Setup Local Environment for Smart Research Backend
# Run this in PowerShell

Write-Host "Checking for existing virtual environment..." -ForegroundColor Cyan
if (Test-Path "venv") {
    Write-Host "Removing old venv to fix corruption..." -ForegroundColor Yellow
    Remove-Item -Path "venv" -Recurse -Force
}

Write-Host "Creating Python Virtual Environment..." -ForegroundColor Cyan
python -m venv venv

if ($?) {
    Write-Host "Activating Virtual Environment..." -ForegroundColor Cyan
    & ./venv/Scripts/Activate.ps1

    Write-Host "Upgrading pip..." -ForegroundColor Cyan
    python -m pip install --upgrade pip

    Write-Host "Installing Dependencies (this may take a few minutes)..." -ForegroundColor Cyan
    pip install -r requirements.txt

    Write-Host ""
    Write-Host "Setup Complete!" -ForegroundColor Green
    Write-Host "--------------------------------------------------"
    Write-Host "IMPORTANT REMINDERS:" -ForegroundColor Yellow
    Write-Host "Copy the 'additionals' folder (containing Tesseract-OCR and poppler)" -ForegroundColor Cyan
    Write-Host "from the flashdrive directly into this folder (lumia_retrieval_bert/)." -ForegroundColor Cyan
    Write-Host "The system is configured to auto-detect them locally here." -ForegroundColor Cyan
    Write-Host "--------------------------------------------------"
    Write-Host "To start the server, run:" -ForegroundColor Cyan
    Write-Host "uvicorn app.main:app --reload"
} else {
    Write-Host "Failed to create virtual environment. Do you have Python installed and in your PATH?" -ForegroundColor Red
}
