# ==============================================================================
# JuriVision - Inicializador Automatizado do Ambiente Local (PowerShell)
# Disciplina: Gerência de Projetos (UFAL) | Equipe Epsilon
# ==============================================================================

Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "  JuriVision - Plataforma de Jurimetria Preditiva e Analise Processual" -ForegroundColor Yellow
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Verificar ambiente virtual Python
if (-not (Test-Path ".venv\Scripts\Activate.ps1")) {
    Write-Host "[1/3] Criando ambiente virtual Python (.venv)..." -ForegroundColor Yellow
    python -m venv .venv
    & .venv\Scripts\pip install -r backend\requirements.txt
}

# 2. Iniciar Backend em nova janela
Write-Host "[2/3] Iniciando Servidor Backend FastAPI (Porta 8000)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$env:PYTHONPATH='backend'; .venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload --port 8000"

# 3. Iniciar Frontend em nova janela
Write-Host "[3/3] Iniciando Interface Web Vite (Porta 5173)..." -ForegroundColor Green
if (-not (Test-Path "frontend\node_modules")) {
    Write-Host "[Frontend] Instalando dependencias Node..." -ForegroundColor Yellow
    Push-Location frontend
    npm install
    Pop-Location
}
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"

Write-Host ""
Write-Host "==============================================================================" -ForegroundColor Cyan
Write-Host "  Ambiente Local Inicializado com Sucesso!" -ForegroundColor Green
Write-Host "  - Interface Web:  http://localhost:5173" -ForegroundColor White
Write-Host "  - Swagger API:    http://localhost:8000/docs" -ForegroundColor White
Write-Host "==============================================================================" -ForegroundColor Cyan
