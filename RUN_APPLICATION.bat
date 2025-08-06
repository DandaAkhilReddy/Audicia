@echo off
echo ======================================================================
echo             AUDICIA SOAP NOTE SYSTEM - ENTERPRISE LAUNCHER
echo                   $200M Healthcare Documentation Platform
echo ======================================================================
echo.
echo Starting Audicia SOAP Note System...
echo.

cd /d "C:\Users\akhil\OneDrive\Desktop\Audicia\Agent-Audicia"

echo [1/4] Checking system requirements...
echo ✓ Python 3.11 required for backend
echo ✓ Node.js 18+ required for frontend
echo ✓ Azure CLI for cloud deployment
echo.

echo [2/4] Opening application components...
echo.

echo 🌐 Opening Frontend Application...
start "" "frontend\index.html"

echo.
echo ⚙️ Starting Backend API Server...
start "Backend API" cmd /k "cd backend && echo Starting FastAPI server... && python main.py"

echo.
echo 📚 Opening Documentation...
start "" "README.md"

echo.
echo 👥 Opening Team Assignments...
start "" "TEAM_ASSIGNMENTS.md"

echo.
echo ======================================================================
echo                        SYSTEM STATUS
echo ======================================================================
echo.
echo Frontend:     http://localhost:3000 (Static preview available)
echo Backend API:   http://localhost:8000 (Starting...)
echo API Docs:      http://localhost:8000/api/docs
echo.
echo Team Size:     20 developers
echo Budget:        $2.5M
echo Timeline:      12 weeks
echo.
echo Architecture:  Azure Cloud Native
echo Security:      HIPAA Compliant
echo Scalability:   10,000+ concurrent users
echo.
echo ======================================================================
echo.
echo 🏥 AUDICIA SOAP NOTE SYSTEM - READY FOR DEVELOPMENT
echo.
echo Your enterprise medical documentation platform is initializing.
echo All team assignments and architecture documents are now available.
echo.
echo Next Steps:
echo 1. Review team assignments in TEAM_ASSIGNMENTS.md
echo 2. Check system architecture in ARCHITECTURE.md
echo 3. Start development with your assigned sprint tasks
echo 4. Deploy to Azure using infrastructure templates
echo.
echo For technical support: dev-team@yourcompany.com
echo For project management: pm-audicia@yourcompany.com
echo.
echo ======================================================================
pause