@echo off
setlocal
cd /d "%~dp0"
call "%~dp0VEC1_PYTHON.cmd" -B vec1\vecctl.py dashboard
if errorlevel 1 exit /b %ERRORLEVEL%
start "" "%~dp0ui\index.html"
