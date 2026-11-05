@echo off
TITLE JuriVision - Inicializador do Ambiente Local
echo ==============================================================================
echo [JuriVision] Iniciando Plataforma de Jurimetria Preditiva (UFAL)
echo ==============================================================================
echo.

:: 1. Verificar se o ambiente virtual Python existe
if not exist ".venv\Scripts\activate.bat" (
    echo [AVISO] Ambiente virtual .venv nao encontrado. Criando...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r backend\requirements.txt
)

:: 2. Iniciar o servidor Backend (FastAPI + SQLite Fallback)
echo [1/2] Iniciando API Backend FastAPI em http://localhost:8000 ...
start "JuriVision Backend API" cmd /k "set PYTHONPATH=backend&& .venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload --port 8000"

:: 3. Iniciar o servidor Frontend (Vite)
echo [2/2] Iniciando Interface Web (Vite) em http://localhost:5173 ...
cd frontend
if not exist "node_modules\" (
    echo [AVISO] Instalando dependencias do Node...
    call npm install
)
start "JuriVision Frontend" cmd /k "npm run dev"
cd ..

echo.
echo ==============================================================================
echo [SUCESSO] Sistema inicializado com sucesso!
echo.
echo - Interface do Advogado (Frontend): http://localhost:5173
echo - Documentacao da API (Swagger):   http://localhost:8000/docs
echo - Health Check do Backend:         http://localhost:8000/health
echo ==============================================================================
pause
