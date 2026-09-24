@echo off
setlocal
cd /d "%~dp0"
call "%~dp0VEC1_PYTHON.cmd" -B vec1\vecctl.py doctor --verbose
exit /b %ERRORLEVEL%
