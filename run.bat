@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    py -3 -m venv .venv
)

call ".venv\Scripts\activate.bat"

set "MOVIES_MEDIA_DIRS=E:\Win_Vault\Movies;E:\Win_Vault\Anime"

python -m pip install --upgrade pip >nul 2>&1
python -m pip install flask requests python-dotenv >nul 2>&1

start "" http://localhost:5000
python backend\run_portal.py

endlocal
