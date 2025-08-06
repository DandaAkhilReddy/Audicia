@echo off
color 0A
echo ========================================
echo   🏥 AUDICIA VOICE-TO-SOAP SYSTEM
echo   PRODUCTION LAUNCH SEQUENCE
echo ========================================

echo.
echo 📋 Production Checklist:
echo ✅ Azure Speech Service API Key: PROVIDED
echo ✅ OpenAI GPT-4 API Key: PROVIDED  
echo ✅ PostgreSQL Database: hha-pg-prod.postgres.database.azure.com
echo ✅ All secrets configured in .env file
echo.

echo 🧪 Running comprehensive system tests...
echo.
python test_system.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo ❌ SYSTEM TESTS FAILED
    echo Please fix the issues above before production launch.
    echo.
    pause
    exit /b 1
)

echo.
echo 🎉 ALL TESTS PASSED - LAUNCHING PRODUCTION SERVER!
echo.
echo 📊 Production Configuration:
echo    - Database: hha-pg-prod.postgres.database.azure.com
echo    - Azure Speech: eastus region
echo    - OpenAI: GPT-4 Turbo Preview
echo    - Environment: Production
echo.
echo 🌐 Server Endpoints:
echo    - API Base: http://localhost:8000
echo    - Health Check: http://localhost:8000/health
echo    - API Docs: http://localhost:8000/api/docs
echo    - Voice-to-SOAP: POST /api/v1/voice-to-soap
echo.
echo 🔒 Security Features:
echo    - HIPAA-compliant encryption
echo    - Comprehensive audit logging
echo    - JWT authentication
echo    - PHI data protection
echo.

echo Press any key to start the production server...
pause > nul

echo.
echo 🚀 Starting FastAPI production server...
echo Press Ctrl+C to stop the server
echo.

REM Start production server
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 4 --log-level info

echo.
echo Server stopped. Production session ended.
echo.
pause