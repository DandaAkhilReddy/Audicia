@echo off
echo ========================================
echo   AUDICIA VOICE-TO-SOAP BACKEND
echo   Production FastAPI Server
echo ========================================

echo.
echo Setting up environment...

REM Set Azure Key Vault name (replace with your actual vault name)
set AZURE_KEY_VAULT_NAME=hha-vault-prod

echo Azure Key Vault: %AZURE_KEY_VAULT_NAME%

echo.
echo Testing Azure services connection...

REM Test Azure Key Vault access
echo Testing Key Vault access...
python backend\secret_manager.py
if %ERRORLEVEL% neq 0 (
    echo ❌ Key Vault test failed. Check Azure authentication.
    pause
    exit /b 1
)

echo.
echo Testing database connection...
python backend\db.py
if %ERRORLEVEL% neq 0 (
    echo ❌ Database test failed. Check PostgreSQL configuration.
    pause
    exit /b 1
)

echo.
echo Testing Azure Speech Service...
python backend\transcriber.py
if %ERRORLEVEL% neq 0 (
    echo ❌ Speech service test failed. Check Azure Speech configuration.
    pause
    exit /b 1
)

echo.
echo Testing OpenAI service...
python backend\soap_generator.py
if %ERRORLEVEL% neq 0 (
    echo ❌ OpenAI test failed. Check OpenAI API key.
    pause
    exit /b 1
)

echo.
echo ✅ All services tested successfully!
echo.
echo Starting FastAPI server...
echo.
echo 🌐 Server will be available at:
echo    - API: http://localhost:8000
echo    - Docs: http://localhost:8000/api/docs
echo    - Health: http://localhost:8000/health
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start the FastAPI server with auto-reload for development
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

echo.
echo Server stopped.
pause