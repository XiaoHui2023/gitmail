@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    call "%~dp0update.bat"
)
call ".venv\Scripts\activate.bat"
pytest
